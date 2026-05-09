import argparse
import json
from pathlib import Path


def read_jsonl(path):
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", action="append", required=True)
    parser.add_argument("--out-jsonl", default="eval/results_github_issue_all_models.jsonl")
    parser.add_argument("--out-md", default="eval/results_github_issue_all_models.md")
    args = parser.parse_args()

    rows = []
    for path in args.input:
        rows.extend(read_jsonl(path))

    candidates = []
    for row in rows:
        if row["candidate"] not in candidates:
            candidates.append(row["candidate"])

    out_jsonl = Path(args.out_jsonl)
    out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with out_jsonl.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    lines = ["# GitHub Issue Benchmark - All Models", ""]
    lines.append("| Candidate | Total | Average | Avg latency |")
    lines.append("|---|---:|---:|---:|")
    for candidate in candidates:
        subset = [row for row in rows if row["candidate"] == candidate]
        total = sum(row["metrics"]["score"] for row in subset)
        max_total = sum(row["metrics"].get("max_score", 10) for row in subset)
        latencies = [row["latency_sec"] for row in subset if row["latency_sec"] is not None]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
        lines.append(f"| `{candidate}` | {total}/{max_total} | {total / max_total:.2%} | {avg_latency:.2f}s |")

    lines.extend(["", "## By Domain", ""])
    lines.append("| Candidate | Godot | Unity | Unreal |")
    lines.append("|---|---:|---:|---:|")
    for candidate in candidates:
        values = []
        for domain in ["godot", "unity", "unreal"]:
            subset = [row for row in rows if row["candidate"] == candidate and row["domain"] == domain]
            total = sum(row["metrics"]["score"] for row in subset)
            max_total = sum(row["metrics"].get("max_score", 10) for row in subset)
            values.append(f"{total}/{max_total}")
        lines.append(f"| `{candidate}` | " + " | ".join(values) + " |")

    lines.extend(["", "## Per Issue", ""])
    lines.append("| Issue | Domain | Repo | " + " | ".join(f"`{c}`" for c in candidates) + " |")
    lines.append("|---|---|---|" + "|".join(["---:"] * len(candidates)) + "|")
    for item_id in sorted({row["id"] for row in rows}):
        first = next(row for row in rows if row["id"] == item_id)
        scores = []
        for candidate in candidates:
            row = next(row for row in rows if row["id"] == item_id and row["candidate"] == candidate)
            scores.append(str(row["metrics"]["score"]))
        title = first["title"].replace("|", "/")[:70]
        lines.append(
            f"| [#{first['issue_number']}]({first['issue_url']}) {title} "
            f"| {first['domain']} | `{first['repo']}` | " + " | ".join(scores) + " |"
        )

    Path(args.out_md).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {args.out_jsonl}")
    print(f"wrote {args.out_md}")


if __name__ == "__main__":
    main()
