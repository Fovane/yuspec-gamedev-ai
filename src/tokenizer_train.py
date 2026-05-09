import argparse
from pathlib import Path

from tokenizers import Tokenizer
from tokenizers.decoders import ByteLevel as ByteLevelDecoder
from tokenizers.models import BPE
from tokenizers.pre_tokenizers import ByteLevel
from tokenizers.trainers import BpeTrainer


SPECIAL_TOKENS = [
    "<|pad|>",
    "<|unk|>",
    "<|bos|>",
    "<|eos|>",
    "<|user|>",
    "<|assistant|>",
    "<|system|>",
    "<|godot|>",
    "<|gdscript|>",
    "<|code|>",
    "<|error|>",
    "<|patch|>",
]


def collect_files():
    files = [str(p) for p in Path("data/clean").glob("*.txt")]
    files += [str(p) for p in Path("data/instructions").glob("*.jsonl")]
    return files


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--vocab-size", type=int, default=16000)
    parser.add_argument("--out", default="tokenizer/tokenizer.json")
    args = parser.parse_args()

    files = collect_files()
    if not files:
        raise SystemExit("No training files found in data/clean or data/instructions")

    tokenizer = Tokenizer(BPE(unk_token="<|unk|>"))
    tokenizer.pre_tokenizer = ByteLevel(add_prefix_space=False)
    tokenizer.decoder = ByteLevelDecoder()

    trainer = BpeTrainer(
        vocab_size=args.vocab_size,
        min_frequency=2,
        special_tokens=SPECIAL_TOKENS,
    )

    tokenizer.train(files, trainer)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    tokenizer.save(args.out)
    print(f"Saved {args.out}")


if __name__ == "__main__":
    main()
