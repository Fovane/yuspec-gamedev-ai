import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

import torch
from peft import PeftModel
from tokenizers import Tokenizer
from transformers import AutoModelForCausalLM, AutoTokenizer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from generate import extract_answer  # noqa: E402
from model import GPT, GPTConfig  # noqa: E402


DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
DOMAIN_TAGS = {
    "godot": "<|godot|>\n",
    "unity": "Domain: Unity\n",
    "unreal": "Domain: Unreal Engine\n",
}

WRONG_ENGINE_TERMS = {
    "godot": ("MonoBehaviour", "using UnityEngine", "UCLASS", "UPROPERTY", "AActor"),
    "unity": ("extends Node", "MeshInstance3D", "UCLASS", "UPROPERTY", "AActor"),
    "unreal": ("MonoBehaviour", "using UnityEngine", "extends Node", "MeshInstance3D"),
}

CODE_SIGNALS = {
    "godot": ("extends ", "func ", "var ", "@export", "class_name", "signal"),
    "unity": ("using UnityEngine", "MonoBehaviour", "public class", "void ", "[SerializeField]", "GetComponent", "async", "CancellationToken", "class "),
    "unreal": ("UCLASS", "UPROPERTY", "UFUNCTION", "AActor", "UActorComponent", "::", "#include"),
}

SYSTEM_BY_DOMAIN = {
    "godot": "You are a senior Godot 4 and GDScript engineer. Solve repository issues with concrete, practical fixes.",
    "unity": "You are a senior Unity and C# engineer. Solve repository issues with concrete, practical fixes.",
    "unreal": "You are a senior Unreal Engine 5 and C++ engineer. Solve repository issues with concrete, practical fixes.",
}


def read_jsonl(path):
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def trim_prompt(prompt, max_chars=2800):
    if len(prompt) <= max_chars:
        return prompt
    head = prompt[:2200]
    tail = prompt[-500:]
    return head + "\n\n[...trimmed...]\n\n" + tail


def build_yuspec_prompt(item):
    domain = item["domain"]
    return (
        f"<|bos|>{DOMAIN_TAGS.get(domain, '')}"
        "<|user|>\n"
        f"{trim_prompt(item['prompt'], 2400)}\n"
        "<|assistant|>\n"
    )


def load_yuspec(checkpoint):
    ckpt = torch.load(checkpoint, map_location=DEVICE)
    cfg = ckpt["config"]
    model = GPT(GPTConfig(**cfg["model"])).to(DEVICE)
    model.load_state_dict(ckpt["model"])
    model.eval()
    tokenizer = Tokenizer.from_file(cfg["data"]["tokenizer_path"])
    return model, tokenizer


@torch.no_grad()
def call_yuspec(model, tokenizer, item, max_new_tokens):
    text = build_yuspec_prompt(item)
    ids = tokenizer.encode(text).ids[-900:]
    x = torch.tensor([ids], dtype=torch.long, device=DEVICE)
    eos_id = tokenizer.token_to_id("<|eos|>")
    started = time.time()
    out = model.generate(
        x,
        max_new_tokens=max_new_tokens,
        temperature=0.25,
        top_k=20,
        eos_id=eos_id,
        vocab_limit=tokenizer.get_vocab_size(),
    )
    decoded = tokenizer.decode(out[0].tolist())
    return extract_answer(decoded, item["prompt"]).strip(), time.time() - started


def load_lora(base_model, adapter):
    dtype = torch.float16 if DEVICE == "cuda" else torch.float32
    tokenizer = AutoTokenizer.from_pretrained(adapter, trust_remote_code=True)
    base = AutoModelForCausalLM.from_pretrained(base_model, torch_dtype=dtype, trust_remote_code=True).to(DEVICE)
    model = PeftModel.from_pretrained(base, adapter).to(DEVICE)
    model.eval()
    return model, tokenizer


@torch.no_grad()
def call_lora(model, tokenizer, item, max_new_tokens):
    messages = [
        {"role": "system", "content": SYSTEM_BY_DOMAIN.get(item["domain"], "You are a senior game developer.")},
        {"role": "user", "content": trim_prompt(item["prompt"], 3200)},
    ]
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=1400).to(DEVICE)
    started = time.time()
    out = model.generate(
        **inputs,
        max_new_tokens=max_new_tokens,
        do_sample=True,
        temperature=0.25,
        top_k=20,
        pad_token_id=tokenizer.eos_token_id,
    )
    text = tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    return text.strip(), time.time() - started


def post_json(url, payload, timeout):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def call_ollama(model_name, item, max_new_tokens, timeout):
    prompt = (
        f"{SYSTEM_BY_DOMAIN.get(item['domain'], 'You are a senior game developer.')}\n"
        "Answer in Turkish when possible. Include a concrete fix and code if useful.\n\n"
        f"{trim_prompt(item['prompt'], 3600)}"
    )
    started = time.time()
    data = post_json(
        "http://127.0.0.1:11434/api/generate",
        {
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.25, "top_k": 20, "num_predict": max_new_tokens},
        },
        timeout,
    )
    return data.get("response", "").strip(), time.time() - started


def has_mojibake(text):
    return any(token in text for token in ("Ã„", "Ãƒ", "Ã…", "Ã‚", "�"))


def max_repeated_line_count(text):
    counts = {}
    for line in (line.strip() for line in text.splitlines()):
        if not line or line in {"{", "}", "};", "```", "```cpp", "```csharp", "```gdscript"}:
            continue
        counts[line] = counts.get(line, 0) + 1
    return max(counts.values(), default=0)


def expected_hits(answer, expected):
    lower = answer.lower()
    return [term for term in expected if term.lower() in lower]


def score_issue_answer(item, answer):
    domain = item["domain"]
    expected = item.get("expected", [])
    hits = expected_hits(answer, expected)
    wrong_terms = [term for term in WRONG_ENGINE_TERMS.get(domain, ()) if term.lower() in answer.lower()]
    title_terms = [
        term
        for term in item.get("title", "").replace("/", " ").replace("-", " ").split()
        if len(term) >= 4
    ][:6]
    title_hits = expected_hits(answer, title_terms)

    checks = {
        "not_empty": len(answer.strip()) >= 120,
        "no_mojibake": not has_mojibake(answer),
        "not_repetitive": max_repeated_line_count(answer) <= 2,
        "has_code_signal": any(signal in answer for signal in CODE_SIGNALS.get(domain, ())),
        "no_wrong_engine": not wrong_terms,
        "mentions_repo_or_issue_terms": len(title_hits) >= max(1, min(2, len(title_terms))),
        "has_fix_language": any(term in answer.lower() for term in ("fix", "çöz", "duzelt", "düzelt", "neden", "cause", "patch")),
        "has_expected_domain_terms": len(hits) >= max(1, min(3, len(expected) // 2)),
    }
    score = sum(int(value) for value in checks.values())
    score += min(2, len(hits) // 2)
    return {
        "score": min(10, score),
        "max_score": 10,
        "checks": checks,
        "expected_hits": hits,
        "title_hits": title_hits,
        "wrong_terms": wrong_terms,
    }


def write_summary(rows, out_md):
    candidates = []
    for row in rows:
        if row["candidate"] not in candidates:
            candidates.append(row["candidate"])
    lines = ["# GitHub Issue Benchmark", ""]
    lines.append("| Candidate | Total | Average | Avg latency |")
    lines.append("|---|---:|---:|---:|")
    for candidate in candidates:
        subset = [row for row in rows if row["candidate"] == candidate]
        total = sum(row["metrics"]["score"] for row in subset)
        max_total = sum(row["metrics"].get("max_score", 10) for row in subset)
        latencies = [row["latency_sec"] for row in subset if row["latency_sec"] is not None]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
        lines.append(f"| `{candidate}` | {total}/{max_total} | {total / max_total:.2%} | {avg_latency:.2f}s |")
    lines.append("")
    lines.append("## Per Issue")
    lines.append("")
    lines.append("| Issue | Domain | Repo | " + " | ".join(f"`{c}`" for c in candidates) + " |")
    lines.append("|---|---|---|" + "|".join(["---:"] * len(candidates)) + "|")
    for item_id in sorted({row["id"] for row in rows}):
        first = next(row for row in rows if row["id"] == item_id)
        scores = []
        for candidate in candidates:
            row = next(row for row in rows if row["id"] == item_id and row["candidate"] == candidate)
            scores.append(str(row["metrics"]["score"]))
        lines.append(
            f"| [#{first['issue_number']}]({first['issue_url']}) {first['title'][:60]} "
            f"| {first['domain']} | `{first['repo']}` | " + " | ".join(scores) + " |"
        )
    Path(out_md).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", default="eval/github_issue_benchmark.jsonl")
    parser.add_argument("--out-jsonl", default="eval/results_github_issue_benchmark.jsonl")
    parser.add_argument("--out-md", default="eval/results_github_issue_benchmark.md")
    parser.add_argument("--yuspec-checkpoint", default="checkpoints/benchmark_realign_v4_round4/best.pt")
    parser.add_argument("--yuspec-name", default="yuspec_10m_saf")
    parser.add_argument("--qwen-base", default="Qwen/Qwen2.5-0.5B-Instruct")
    parser.add_argument("--qwen-adapter", default="checkpoints/qwen2_5_0_5b_gamedev_lora_godot_balanced")
    parser.add_argument("--qwen7b", default="qwen2.5:7b-instruct-q4_K_M")
    parser.add_argument("--max-new-tokens", type=int, default=520)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--skip-yuspec", action="store_true")
    parser.add_argument("--skip-lora", action="store_true")
    parser.add_argument("--skip-qwen7b", action="store_true")
    args = parser.parse_args()

    items = list(read_jsonl(args.benchmark))
    rows = []

    yuspec = None
    if not args.skip_yuspec:
        yuspec = load_yuspec(args.yuspec_checkpoint)
    lora = None
    if not args.skip_lora:
        lora = load_lora(args.qwen_base, args.qwen_adapter)

    candidates = []
    if yuspec:
        candidates.append((args.yuspec_name, lambda item: call_yuspec(*yuspec, item, args.max_new_tokens), "local_yuspec"))
    if lora:
        candidates.append(("qwen2.5_0.5b_lora", lambda item: call_lora(*lora, item, args.max_new_tokens), "hf_lora"))
    if not args.skip_qwen7b:
        candidates.append(("qwen2.5_7b", lambda item: call_ollama(args.qwen7b, item, args.max_new_tokens, args.timeout), "ollama"))

    for name, call_fn, mode in candidates:
        for item in items:
            try:
                answer, latency = call_fn(item)
                metrics = score_issue_answer(item, answer)
                print(f"{name} | {item['id']}: {metrics['score']}/10")
                error = None
            except Exception as exc:
                answer = ""
                latency = None
                metrics = {"score": 0, "max_score": 10, "checks": {}, "error": str(exc)}
                error = str(exc)
                print(f"{name} | {item['id']}: ERROR {exc}")
            rows.append(
                {
                    "candidate": name,
                    "id": item["id"],
                    "domain": item["domain"],
                    "repo": item["repo"],
                    "issue_number": item["issue_number"],
                    "issue_url": item["issue_url"],
                    "title": item["title"],
                    "license": item["license"],
                    "prompt": item["prompt"],
                    "answer": answer,
                    "metrics": metrics,
                    "latency_sec": latency,
                    "mode": mode,
                    "error": error,
                }
            )

    out_jsonl = Path(args.out_jsonl)
    out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with out_jsonl.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    write_summary(rows, args.out_md)
    print(f"wrote {args.out_jsonl}")
    print(f"wrote {args.out_md}")


if __name__ == "__main__":
    main()
