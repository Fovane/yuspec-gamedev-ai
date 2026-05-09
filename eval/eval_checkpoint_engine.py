import argparse
import json
import sys
import time
from pathlib import Path

import torch
from tokenizers import Tokenizer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from generate import extract_answer  # noqa: E402
from model import GPT, GPTConfig  # noqa: E402
from compare_with_qwen import score_answer, write_summary  # noqa: E402


DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

DOMAIN_TAGS = {
    "godot": "<|godot|>\n",
    "unity": "Domain: Unity\n",
    "unreal": "Domain: Unreal Engine\n",
    "general": "",
}


def read_jsonl(path):
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def build_prompt(prompt, domain):
    return (
        f"<|bos|>{DOMAIN_TAGS.get(domain, '')}"
        "<|user|>\n"
        f"{prompt}\n"
        "<|assistant|>\n"
    )


def load_model(checkpoint):
    ckpt = torch.load(checkpoint, map_location=DEVICE)
    cfg = ckpt["config"]
    model = GPT(GPTConfig(**cfg["model"])).to(DEVICE)
    model.load_state_dict(ckpt["model"])
    model.eval()
    tokenizer = Tokenizer.from_file(cfg["data"]["tokenizer_path"])
    return model, tokenizer


@torch.no_grad()
def generate(model, tokenizer, item, max_new_tokens, temperature, top_k):
    text = build_prompt(item["prompt"], item["domain"])
    ids = tokenizer.encode(text).ids
    x = torch.tensor([ids], dtype=torch.long, device=DEVICE)
    eos_id = tokenizer.token_to_id("<|eos|>")
    out = model.generate(
        x,
        max_new_tokens=max_new_tokens,
        temperature=temperature,
        top_k=top_k,
        eos_id=eos_id,
        vocab_limit=tokenizer.get_vocab_size(),
    )
    decoded = tokenizer.decode(out[0].tolist())
    return extract_answer(decoded, item["prompt"])


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--name", default="checkpoint")
    parser.add_argument("--benchmark", default="eval/engine_vs_qwen_benchmark.jsonl")
    parser.add_argument("--out-jsonl", default="eval/results_checkpoint_engine.jsonl")
    parser.add_argument("--out-md", default="eval/results_checkpoint_engine.md")
    parser.add_argument("--max-new-tokens", type=int, default=420)
    parser.add_argument("--temperature", type=float, default=0.25)
    parser.add_argument("--top-k", type=int, default=20)
    parser.add_argument("--seed", type=int, default=1234)
    args = parser.parse_args()

    torch.manual_seed(args.seed)
    model, tokenizer = load_model(args.checkpoint)
    rows = []

    for item in read_jsonl(args.benchmark):
        started = time.time()
        answer = generate(model, tokenizer, item, args.max_new_tokens, args.temperature, args.top_k)
        latency = time.time() - started
        metrics = score_answer(item, answer)
        rows.append(
            {
                "candidate": args.name,
                "id": item["id"],
                "domain": item["domain"],
                "prompt": item["prompt"],
                "answer": answer,
                "metrics": metrics,
                "latency_sec": latency,
                "mode": "model",
                "extra": {},
                "error": None,
            }
        )
        print(f"{args.name} | {item['id']}: {metrics['score']}/10")

    out_jsonl = Path(args.out_jsonl)
    out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with out_jsonl.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    write_summary(rows, args.out_md)
    total = sum(row["metrics"]["score"] for row in rows)
    max_total = sum(row["metrics"]["max_score"] for row in rows)
    print(f"total: {total}/{max_total}")
    print(f"wrote {args.out_jsonl}")
    print(f"wrote {args.out_md}")


if __name__ == "__main__":
    main()
