import argparse
import json
import random
from collections import defaultdict
from pathlib import Path


def read_jsonl(path):
    rows = []
    p = Path(path)
    if not p.exists():
        return rows
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path, rows):
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", action="append", required=True)
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument("--out", required=True)
    parser.add_argument("--seed", type=int, default=6060)
    parser.add_argument("--max-per-domain", type=int, default=18)
    args = parser.parse_args()

    excluded = set()
    for path in args.exclude:
        for row in read_jsonl(path):
            excluded.add(row.get("issue_url") or row.get("id"))
            excluded.add(row.get("id"))

    seen = set()
    by_domain = defaultdict(list)
    for path in args.candidate:
        for row in read_jsonl(path):
            key = row.get("issue_url") or row.get("id")
            if not key or key in seen or key in excluded or row.get("id") in excluded:
                continue
            seen.add(key)
            by_domain[row["domain"]].append(row)

    rng = random.Random(args.seed)
    selected = []
    for domain in ("godot", "unity", "unreal"):
        rows = by_domain[domain]
        rng.shuffle(rows)
        selected.extend(rows[: args.max_per_domain])

    selected.sort(key=lambda row: (row["domain"], row["repo"], row["issue_number"]))
    write_jsonl(args.out, selected)
    print(f"wrote {len(selected)} rows -> {args.out}")
    for domain in ("godot", "unity", "unreal"):
        print(f"{domain}: {sum(1 for row in selected if row['domain'] == domain)}")


if __name__ == "__main__":
    main()
