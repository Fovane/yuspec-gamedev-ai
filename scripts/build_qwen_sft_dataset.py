import argparse
import json
import random
from pathlib import Path


SYSTEM_BY_DOMAIN = {
    "godot": "Sen Godot 4 ve GDScript konusunda uzman bir oyun geliştirme asistanısın. Kısa, geçerli ve uygulanabilir cevap ver.",
    "unity": "Sen Unity ve C# konusunda uzman bir oyun geliştirme asistanısın. Kısa, geçerli ve uygulanabilir cevap ver.",
    "unreal": "Sen Unreal Engine 5 ve C++ konusunda uzman bir oyun geliştirme asistanısın. Kısa, geçerli ve uygulanabilir cevap ver.",
    "general": "Sen kısa ve net cevap veren yardımcı bir asistansın.",
}


def read_jsonl(path):
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def normalize_row(item):
    domain = item.get("domain", "godot")
    return {
        "domain": domain,
        "messages": [
            {"role": "system", "content": SYSTEM_BY_DOMAIN.get(domain, SYSTEM_BY_DOMAIN["general"])},
            {"role": "user", "content": item["instruction"].strip()},
            {"role": "assistant", "content": item["answer"].strip()},
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="data/qwen_sft")
    parser.add_argument("--val-ratio", type=float, default=0.06)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--godot-repeat", type=int, default=1)
    parser.add_argument(
        "--input",
        action="append",
        default=[
            "data/instructions/godot_core_v1.jsonl",
            "data/instructions/godot_scene_ops_v1.jsonl",
            "data/instructions/multiengine_v2.jsonl",
            "data/instructions/unreal5_examples_v1.jsonl",
        ],
    )
    args = parser.parse_args()

    rows = []
    for path in args.input:
        p = Path(path)
        if not p.exists():
            continue
        for item in read_jsonl(p):
            row = normalize_row(item)
            repeat = args.godot_repeat if row["domain"] == "godot" else 1
            rows.extend(row for _ in range(repeat))

    if len(rows) < 2:
        raise SystemExit("Need at least two SFT rows")

    random.seed(args.seed)
    random.shuffle(rows)
    split = max(1, int(len(rows) * (1.0 - args.val_ratio)))
    split = min(split, len(rows) - 1)
    train_rows = rows[:split]
    val_rows = rows[split:]

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, split_rows in [("train", train_rows), ("val", val_rows)]:
        with (out_dir / f"{name}.jsonl").open("w", encoding="utf-8") as f:
            for row in split_rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"train rows: {len(train_rows)}")
    print(f"val rows: {len(val_rows)}")
    print(f"wrote {out_dir}")


if __name__ == "__main__":
    main()
