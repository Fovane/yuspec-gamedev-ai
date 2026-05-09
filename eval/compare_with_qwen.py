import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path


DOMAIN_NAMES = {
    "godot": "Godot 4 / GDScript",
    "unity": "Unity / C#",
    "unreal": "Unreal Engine 5 / C++",
}

WRONG_ENGINE_TERMS = {
    "godot": ("MonoBehaviour", "using UnityEngine", "UCLASS", "UPROPERTY", "AActor"),
    "unity": ("extends Node", "MeshInstance3D", "UCLASS", "UPROPERTY", "AActor"),
    "unreal": ("MonoBehaviour", "using UnityEngine", "extends Node", "MeshInstance3D"),
}

CODE_SIGNALS = {
    "godot": ("extends ", "func ", "var ", "MeshInstance3D", "CharacterBody2D"),
    "unity": ("using UnityEngine", "MonoBehaviour", "public class", "void ", "[SerializeField]"),
    "unreal": ("UCLASS", "UPROPERTY", "UFUNCTION", "AActor", "ACharacter", "::", "#include"),
}


def read_jsonl(path):
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def post_json(url, payload, timeout):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def call_yuspec(base_url, item, use_retrieval, timeout):
    payload = {
        "domain": item["domain"],
        "prompt": item["prompt"],
        "max_new_tokens": 420,
        "temperature": 0.25,
        "top_k": 20,
        "use_retrieval": use_retrieval,
        "snippet_limit": 3,
    }
    started = time.time()
    data = post_json(f"{base_url.rstrip('/')}/generate", payload, timeout)
    return {
        "answer": data.get("answer", ""),
        "latency_sec": time.time() - started,
        "mode": data.get("mode", "unknown"),
        "extra": {
            "matched_instruction": data.get("matched_instruction"),
            "sources": data.get("sources"),
        },
    }


def qwen_prompt(item):
    domain = DOMAIN_NAMES.get(item["domain"], item["domain"])
    return (
        "Türkçe cevap ver. Gereksiz uzatma. Kod gerekiyorsa geçerli ve kısa kod bloğu yaz.\n"
        f"Alan: {domain}\n"
        f"Soru: {item['prompt']}"
    )


def call_ollama(base_url, model, item, timeout):
    payload = {
        "model": model,
        "prompt": qwen_prompt(item),
        "stream": False,
        "options": {
            "temperature": 0.25,
            "top_k": 20,
            "num_predict": 420,
        },
    }
    started = time.time()
    data = post_json(f"{base_url.rstrip('/')}/api/generate", payload, timeout)
    return {
        "answer": data.get("response", ""),
        "latency_sec": time.time() - started,
        "mode": "ollama",
        "extra": {
            "model": model,
            "eval_count": data.get("eval_count"),
        },
    }


def has_mojibake(text):
    return any(token in text for token in ("Ä", "Ã", "Å", "Â"))


def max_repeated_line_count(text):
    counts = {}
    for line in (line.strip() for line in text.splitlines()):
        if not line:
            continue
        if line in {"{", "}", "};", "```", "```cpp", "```csharp", "```gdscript"}:
            continue
        counts[line] = counts.get(line, 0) + 1
    return max(counts.values(), default=0)


def expected_hits(answer, expected):
    lower = answer.lower()
    return [term for term in expected if term.lower() in lower]


def score_answer(item, answer):
    expected = item.get("expected", [])
    hits = expected_hits(answer, expected)
    domain = item["domain"]
    wrong_terms = [term for term in WRONG_ENGINE_TERMS.get(domain, ()) if term.lower() in answer.lower()]

    checks = {
        "not_empty": len(answer.strip()) >= 80,
        "no_mojibake": not has_mojibake(answer),
        "not_repetitive": max_repeated_line_count(answer) <= 2,
        "has_code_signal": any(signal in answer for signal in CODE_SIGNALS.get(domain, ())),
        "no_wrong_engine": not wrong_terms,
        "expected_ratio_60": len(hits) >= max(1, int(len(expected) * 0.6)),
    }

    score = sum(int(value) for value in checks.values())
    if expected:
        score += min(4, round((len(hits) / len(expected)) * 4))
    return {
        "score": score,
        "max_score": 10,
        "checks": checks,
        "expected_hits": hits,
        "expected_total": len(expected),
        "wrong_terms": wrong_terms,
    }


def run_candidate(name, call_fn, items):
    rows = []
    for item in items:
        try:
            result = call_fn(item)
            answer = result["answer"]
            metrics = score_answer(item, answer)
            rows.append(
                {
                    "candidate": name,
                    "id": item["id"],
                    "domain": item["domain"],
                    "prompt": item["prompt"],
                    "answer": answer,
                    "metrics": metrics,
                    "latency_sec": result["latency_sec"],
                    "mode": result["mode"],
                    "extra": result["extra"],
                    "error": None,
                }
            )
            print(f"{name} | {item['id']}: {metrics['score']}/10 ({result['mode']})")
        except Exception as exc:
            rows.append(
                {
                    "candidate": name,
                    "id": item["id"],
                    "domain": item["domain"],
                    "prompt": item["prompt"],
                    "answer": "",
                    "metrics": {"score": 0, "max_score": 10},
                    "latency_sec": None,
                    "mode": "error",
                    "extra": {},
                    "error": str(exc),
                }
            )
            print(f"{name} | {item['id']}: ERROR {exc}")
    return rows


def write_summary(rows, out_md):
    candidates = sorted({row["candidate"] for row in rows})
    lines = ["# Engine Benchmark", ""]
    lines.append("| Candidate | Total | Average | Avg latency |")
    lines.append("|---|---:|---:|---:|")
    for candidate in candidates:
        subset = [row for row in rows if row["candidate"] == candidate]
        total = sum(row["metrics"]["score"] for row in subset)
        max_total = sum(row["metrics"].get("max_score", 10) for row in subset)
        latencies = [row["latency_sec"] for row in subset if row["latency_sec"] is not None]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
        lines.append(f"| {candidate} | {total}/{max_total} | {total / max_total:.2%} | {avg_latency:.2f}s |")

    lines.append("")
    lines.append("## Per Prompt")
    lines.append("")
    lines.append("| Prompt | " + " | ".join(candidates) + " |")
    lines.append("|---|" + "|".join(["---:"] * len(candidates)) + "|")
    for prompt_id in sorted({row["id"] for row in rows}):
        scores = []
        for candidate in candidates:
            row = next(row for row in rows if row["id"] == prompt_id and row["candidate"] == candidate)
            scores.append(str(row["metrics"]["score"]))
        lines.append(f"| {prompt_id} | " + " | ".join(scores) + " |")

    Path(out_md).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", default="eval/engine_vs_qwen_benchmark.jsonl")
    parser.add_argument("--out-jsonl", default="eval/results_engine_vs_qwen.jsonl")
    parser.add_argument("--out-md", default="eval/results_engine_vs_qwen.md")
    parser.add_argument("--yuspec-url", default="http://127.0.0.1:8008")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    parser.add_argument("--ollama-model", default="qwen2.5:0.5b")
    parser.add_argument("--skip-ollama", action="store_true")
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args()

    items = list(read_jsonl(args.benchmark))
    rows = []
    rows += run_candidate(
        "yuspec_hybrid",
        lambda item: call_yuspec(args.yuspec_url, item, True, args.timeout),
        items,
    )
    rows += run_candidate(
        "yuspec_model_only",
        lambda item: call_yuspec(args.yuspec_url, item, False, args.timeout),
        items,
    )

    if not args.skip_ollama:
        rows += run_candidate(
            args.ollama_model,
            lambda item: call_ollama(args.ollama_url, args.ollama_model, item, args.timeout),
            items,
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
