import argparse
import json
import random
from collections import defaultdict
from pathlib import Path


def read_jsonl(path):
    rows = []
    with Path(path).open("r", encoding="utf-8") as f:
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
    parser.add_argument("--candidates", default="eval/hidden_github_issue_candidates.jsonl")
    parser.add_argument("--exclude", default="eval/github_issue_benchmark.jsonl")
    parser.add_argument("--out", default="eval/github_issue_hidden_benchmark.jsonl")
    parser.add_argument("--seed", type=int, default=40560)
    parser.add_argument("--godot", type=int, default=6)
    parser.add_argument("--unity", type=int, default=6)
    parser.add_argument("--unreal", type=int, default=4)
    args = parser.parse_args()

    candidates = read_jsonl(args.candidates)
    excluded = read_jsonl(args.exclude)
    excluded_urls = {row.get("issue_url") for row in excluded}
    excluded_ids = {row.get("id") for row in excluded}

    by_domain = defaultdict(list)
    seen = set()
    for row in candidates:
        key = row.get("issue_url") or row.get("id")
        if not key or key in seen:
            continue
        if row.get("issue_url") in excluded_urls or row.get("id") in excluded_ids:
            continue
        seen.add(key)
        by_domain[row["domain"]].append(row)

    rng = random.Random(args.seed)
    targets = {"godot": args.godot, "unity": args.unity, "unreal": args.unreal}
    hidden = []
    for domain, count in targets.items():
        rows = by_domain[domain]
        rng.shuffle(rows)
        hidden.extend(rows[:count])

    hidden.sort(key=lambda row: (row["domain"], row["repo"], row["issue_number"]))
    write_jsonl(args.out, hidden)

    print(f"hidden issues: {len(hidden)} -> {args.out}")
    for domain in ("godot", "unity", "unreal"):
        print(f"{domain}: {sum(1 for row in hidden if row['domain'] == domain)}")


if __name__ == "__main__":
    main()
