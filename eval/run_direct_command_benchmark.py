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
    "general": "",
}
SYSTEM_BY_DOMAIN = {
    "godot": "You are a senior Godot 4 and GDScript engineer. Write concise, runnable game code.",
    "unity": "You are a senior Unity and C# engineer. Write concise, runnable Unity game code.",
    "unreal": "You are a senior Unreal Engine 5 and C++ engineer. Write concise, runnable Unreal code.",
}


def read_jsonl(path):
    rows = []
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def build_yuspec_prompt(item):
    return (
        f"<|bos|>{DOMAIN_TAGS.get(item['domain'], '')}"
        "<|user|>\n"
        f"{item['prompt']}\n"
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
    ids = tokenizer.encode(build_yuspec_prompt(item)).ids[-900:]
    x = torch.tensor([ids], dtype=torch.long, device=DEVICE)
    eos_id = tokenizer.token_to_id("<|eos|>")
    started = time.time()
    out = model.generate(
        x,
        max_new_tokens=max_new_tokens,
        temperature=0.18,
        top_k=12,
        eos_id=eos_id,
        vocab_limit=tokenizer.get_vocab_size(),
    )
    decoded = tokenizer.decode(out[0].tolist())
    return extract_answer(decoded, item["prompt"]).replace("\ufffd", "").strip(), time.time() - started


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
        {"role": "system", "content": SYSTEM_BY_DOMAIN.get(item["domain"], "Write game-development code.")},
        {"role": "user", "content": item["prompt"]},
    ]
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=900).to(DEVICE)
    started = time.time()
    out = model.generate(
        **inputs,
        max_new_tokens=max_new_tokens,
        do_sample=True,
        temperature=0.18,
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
        f"{SYSTEM_BY_DOMAIN.get(item['domain'], 'Write game-development code.')}\n"
        "Return practical code first. Do not switch to another engine.\n\n"
        f"Task: {item['prompt']}"
    )
    started = time.time()
    data = post_json(
        "http://127.0.0.1:11434/api/generate",
        {
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.18, "top_k": 20, "num_predict": max_new_tokens},
        },
        timeout,
    )
    return data.get("response", "").strip(), time.time() - started


def has_mojibake(text):
    return any(token in text for token in ("Ã", "ï¿½", "\ufffd"))


def expected_hits(answer, expected):
    lower = answer.lower()
    return [term for term in expected if term.lower() in lower]


def score_answer(item, answer):
    hits = expected_hits(answer, item.get("expected", []))
    wrong = [term for term in item.get("wrong", []) if term.lower() in answer.lower()]
    checks = {
        "not_empty": len(answer.strip()) >= 120,
        "has_code_fence": "```" in answer or item["domain"] == "unreal",
        "no_mojibake": not has_mojibake(answer),
        "no_wrong_engine": not wrong,
        "has_expected_terms": len(hits) >= max(3, min(6, len(item.get("expected", [])) - 1)),
        "mentions_task_object": any(term.lower() in answer.lower() for term in item["prompt"].replace(",", " ").split() if len(term) >= 6),
    }
    score = sum(int(value) for value in checks.values())
    score += min(4, len(hits))
    return {
        "score": min(10, score),
        "max_score": 10,
        "checks": checks,
        "expected_hits": hits,
        "wrong_terms": wrong,
    }


def write_summary(rows, out_md):
    candidates = []
    for row in rows:
        if row["candidate"] not in candidates:
            candidates.append(row["candidate"])
    lines = ["# Direct Game Command Benchmark", ""]
    lines.append("| Candidate | Total | Average | Avg latency |")
    lines.append("|---|---:|---:|---:|")
    for candidate in candidates:
        subset = [row for row in rows if row["candidate"] == candidate]
        total = sum(row["metrics"]["score"] for row in subset)
        max_total = sum(row["metrics"]["max_score"] for row in subset)
        latencies = [row["latency_sec"] for row in subset if row["latency_sec"] is not None]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
        lines.append(f"| `{candidate}` | {total}/{max_total} | {total / max_total:.2%} | {avg_latency:.2f}s |")
    lines.append("")
    lines.append("## Per Command")
    lines.append("")
    lines.append("| Command | Domain | " + " | ".join(f"`{c}`" for c in candidates) + " |")
    lines.append("|---|---|" + "|".join(["---:"] * len(candidates)) + "|")
    for item_id in sorted({row["id"] for row in rows}):
        first = next(row for row in rows if row["id"] == item_id)
        scores = []
        for candidate in candidates:
            row = next(row for row in rows if row["id"] == item_id and row["candidate"] == candidate)
            scores.append(str(row["metrics"]["score"]))
        lines.append(f"| `{first['prompt']}` | {first['domain']} | " + " | ".join(scores) + " |")
    Path(out_md).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", default="eval/direct_command_benchmark.jsonl")
    parser.add_argument("--out-jsonl", default="eval/results_direct_command_benchmark.jsonl")
    parser.add_argument("--out-md", default="eval/results_direct_command_benchmark.md")
    parser.add_argument("--yuspec-checkpoint", default="checkpoints/compound_game_commands_60m_v5/best.pt")
    parser.add_argument("--qwen-base", default="Qwen/Qwen2.5-0.5B-Instruct")
    parser.add_argument("--qwen-adapter", default="checkpoints/qwen2_5_0_5b_gamedev_lora_godot_balanced")
    parser.add_argument("--qwen05", default="qwen2.5:0.5b")
    parser.add_argument("--qwen7b", default="qwen2.5:7b-instruct-q4_K_M")
    parser.add_argument("--max-new-tokens", type=int, default=700)
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--skip-yuspec", action="store_true")
    parser.add_argument("--skip-lora", action="store_true")
    parser.add_argument("--skip-qwen05", action="store_true")
    parser.add_argument("--skip-qwen7b", action="store_true")
    args = parser.parse_args()

    items = read_jsonl(args.benchmark)
    rows = []
    candidates = []

    if not args.skip_yuspec:
        yuspec = load_yuspec(args.yuspec_checkpoint)
        candidates.append(("yuspec_60m_compound_v5", lambda item: call_yuspec(*yuspec, item, args.max_new_tokens), "local_yuspec"))
    if not args.skip_lora:
        lora = load_lora(args.qwen_base, args.qwen_adapter)
        candidates.append(("qwen2.5_0.5b_lora", lambda item: call_lora(*lora, item, args.max_new_tokens), "hf_lora"))
    if not args.skip_qwen05:
        candidates.append(("qwen2.5_0.5b", lambda item: call_ollama(args.qwen05, item, args.max_new_tokens, args.timeout), "ollama"))
    if not args.skip_qwen7b:
        candidates.append(("qwen2.5_7b", lambda item: call_ollama(args.qwen7b, item, args.max_new_tokens, args.timeout), "ollama"))

    for name, call_fn, mode in candidates:
        for item in items:
            try:
                answer, latency = call_fn(item)
                metrics = score_answer(item, answer)
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
