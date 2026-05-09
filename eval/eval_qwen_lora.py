import argparse
import json
import time
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

from compare_with_qwen import read_jsonl, score_answer, write_summary


SYSTEM_BY_DOMAIN = {
    "godot": "Sen Godot 4 ve GDScript konusunda uzman bir oyun geliştirme asistanısın. Kısa, geçerli ve uygulanabilir cevap ver.",
    "unity": "Sen Unity ve C# konusunda uzman bir oyun geliştirme asistanısın. Kısa, geçerli ve uygulanabilir cevap ver.",
    "unreal": "Sen Unreal Engine 5 ve C++ konusunda uzman bir oyun geliştirme asistanısın. Kısa, geçerli ve uygulanabilir cevap ver.",
    "general": "Sen kısa ve net cevap veren yardımcı bir asistansın.",
}


def load_model(base_model, adapter):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32
    tokenizer = AutoTokenizer.from_pretrained(adapter, trust_remote_code=True)
    base = AutoModelForCausalLM.from_pretrained(
        base_model,
        torch_dtype=dtype,
        trust_remote_code=True,
    ).to(device)
    model = PeftModel.from_pretrained(base, adapter).to(device)
    model.eval()
    return model, tokenizer, device


@torch.no_grad()
def generate(model, tokenizer, device, item, max_new_tokens):
    messages = [
        {"role": "system", "content": SYSTEM_BY_DOMAIN.get(item["domain"], SYSTEM_BY_DOMAIN["general"])},
        {"role": "user", "content": item["prompt"]},
    ]
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(prompt, return_tensors="pt").to(device)
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-model", default="Qwen/Qwen2.5-0.5B-Instruct")
    parser.add_argument("--adapter", default="checkpoints/qwen2_5_0_5b_gamedev_lora")
    parser.add_argument("--benchmark", default="eval/engine_vs_qwen_benchmark.jsonl")
    parser.add_argument("--out-jsonl", default="eval/results_qwen_lora.jsonl")
    parser.add_argument("--out-md", default="eval/results_qwen_lora.md")
    parser.add_argument("--max-new-tokens", type=int, default=420)
    args = parser.parse_args()

    model, tokenizer, device = load_model(args.base_model, args.adapter)
    rows = []
    for item in read_jsonl(args.benchmark):
        answer, latency = generate(model, tokenizer, device, item, args.max_new_tokens)
        metrics = score_answer(item, answer)
        row = {
            "candidate": "qwen2.5_0.5b_lora",
            "id": item["id"],
            "domain": item["domain"],
            "prompt": item["prompt"],
            "answer": answer,
            "metrics": metrics,
            "latency_sec": latency,
            "mode": "hf_lora",
            "extra": {},
            "error": None,
        }
        rows.append(row)
        print(f"{item['id']}: {metrics['score']}/10")

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
