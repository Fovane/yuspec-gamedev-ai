import argparse
import json
import random
from pathlib import Path

import numpy as np
from tokenizers import Tokenizer
from tqdm import tqdm


def split_clean_text(text, max_chars=20000):
    if "<|eos|>" in text:
        parts = text.split("<|eos|>")
    else:
        parts = []
        current = []
        current_len = 0
        for paragraph in text.split("\n\n"):
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            if current and current_len + len(paragraph) > max_chars:
                parts.append("\n\n".join(current))
                current = []
                current_len = 0
            current.append(paragraph)
            current_len += len(paragraph)
        if current:
            parts.append("\n\n".join(current))

    return [part.strip() for part in parts if len(part.strip()) >= 200]


def load_texts(include_clean=True, include_instructions=True, clean_globs=None, instruction_globs=None):
    texts = []

    if include_clean:
        clean_paths = []
        for pattern in clean_globs or ["data/clean/*.txt"]:
            clean_paths.extend(Path().glob(pattern))
        for path in sorted(set(clean_paths)):
            text = path.read_text(encoding="utf-8", errors="ignore").strip()
            for chunk in split_clean_text(text):
                texts.append(f"<|bos|><|godot|>\n{chunk}\n<|eos|>\n")

    if include_instructions:
        instruction_paths = []
        for pattern in instruction_globs or ["data/instructions/*.jsonl"]:
            instruction_paths.extend(Path().glob(pattern))
        for path in sorted(set(instruction_paths)):
            with path.open("r", encoding="utf-8") as f:
                for line_no, line in enumerate(f, start=1):
                    line = line.strip()
                    if not line:
                        continue
                    item = json.loads(line)
                    instruction = item["instruction"].strip()
                    answer = item["answer"].strip()
                    domain = item.get("domain", "godot").strip().lower()
                    domain_tags = {
                        "godot": "<|godot|>\n",
                        "unity": "Domain: Unity\n",
                        "unreal": "Domain: Unreal Engine\n",
                        "general": "",
                    }
                    domain_tag = domain_tags.get(domain, "")
                    text = (
                        f"<|bos|>{domain_tag}"
                        "<|user|>\n"
                        f"{instruction}\n"
                        "<|assistant|>\n"
                        f"{answer}\n"
                        "<|eos|>\n"
                    )
                    texts.append(text)

    random.shuffle(texts)
    return texts


def encode_all(texts, tokenizer):
    ids = []
    eos_id = tokenizer.token_to_id("<|eos|>")
    for text in tqdm(texts, desc="Encoding"):
        encoded = tokenizer.encode(text).ids
        ids.extend(encoded)
        if eos_id is not None and (not encoded or encoded[-1] != eos_id):
            ids.append(eos_id)
    return np.array(ids, dtype=np.uint16)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tokenizer", default="tokenizer/tokenizer.json")
    parser.add_argument("--out-dir", default="data/tokens")
    parser.add_argument("--val-ratio", type=float, default=0.02)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--include-clean", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--include-instructions", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--clean-glob", action="append")
    parser.add_argument("--instruction-glob", action="append")
    args = parser.parse_args()

    random.seed(args.seed)
    tokenizer = Tokenizer.from_file(args.tokenizer)
    texts = load_texts(
        include_clean=args.include_clean,
        include_instructions=args.include_instructions,
        clean_globs=args.clean_glob,
        instruction_globs=args.instruction_glob,
    )
    if len(texts) < 2:
        raise SystemExit("Need at least two texts to create train/val splits")

    split = max(1, int(len(texts) * (1.0 - args.val_ratio)))
    split = min(split, len(texts) - 1)
    train_texts = texts[:split]
    val_texts = texts[split:]

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    train_ids = encode_all(train_texts, tokenizer)
    val_ids = encode_all(val_texts, tokenizer)
    train_ids.tofile(out_dir / "train.bin")
    val_ids.tofile(out_dir / "val.bin")

    print("train tokens:", len(train_ids))
    print("val tokens:", len(val_ids))


if __name__ == "__main__":
    main()
