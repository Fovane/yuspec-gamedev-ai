import argparse
import sys

import torch
from tokenizers import Tokenizer

from model import GPT, GPTConfig


device = "cuda" if torch.cuda.is_available() else "cpu"


def extract_answer(decoded, prompt=None):
    marker = "<|assistant|>"
    if marker in decoded:
        decoded = decoded.split(marker, 1)[1]
    elif prompt and prompt in decoded:
        decoded = decoded.split(prompt, 1)[1]
    if "<|eos|>" in decoded:
        decoded = decoded.split("<|eos|>", 1)[0]
    return decoded.strip()


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", default="checkpoints/best.pt")
    parser.add_argument("--prompt")
    parser.add_argument("--max-new-tokens", type=int, default=256)
    parser.add_argument("--temperature", type=float, default=0.8)
    parser.add_argument("--top-k", type=int, default=50)
    parser.add_argument("--domain", choices=["godot", "unity", "unreal", "general"], default="godot")
    parser.add_argument("--answer-only", action="store_true")
    args = parser.parse_args()

    ckpt = torch.load(args.checkpoint, map_location=device)
    cfg = ckpt["config"]

    model_cfg = GPTConfig(**cfg["model"])
    model = GPT(model_cfg).to(device)
    model.load_state_dict(ckpt["model"])
    model.eval()

    tokenizer = Tokenizer.from_file(cfg["data"]["tokenizer_path"])
    prompt = args.prompt if args.prompt is not None else input("Prompt: ").strip()

    domain_tags = {
        "godot": "<|godot|>\n",
        "unity": "Domain: Unity\n",
        "unreal": "Domain: Unreal Engine\n",
        "general": "",
    }
    domain_tag = domain_tags[args.domain]
    text = (
        f"<|bos|>{domain_tag}"
        "<|user|>\n"
        f"{prompt}\n"
        "<|assistant|>\n"
    )

    ids = tokenizer.encode(text).ids
    x = torch.tensor([ids], dtype=torch.long, device=device)
    eos_id = tokenizer.token_to_id("<|eos|>")

    out = model.generate(
        x,
        max_new_tokens=args.max_new_tokens,
        temperature=args.temperature,
        top_k=args.top_k,
        eos_id=eos_id,
        vocab_limit=tokenizer.get_vocab_size(),
    )

    decoded = tokenizer.decode(out[0].tolist())
    print(extract_answer(decoded, prompt) if args.answer_only else decoded)


if __name__ == "__main__":
    main()
