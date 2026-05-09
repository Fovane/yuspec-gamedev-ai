import argparse
import json
import random
from pathlib import Path


def read_jsonl(path):
    rows = []
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def trim_prompt(prompt, max_chars=2400):
    if len(prompt) <= max_chars:
        return prompt
    return prompt[:1900].rstrip() + "\n\n[...trimmed...]\n\n" + prompt[-400:].lstrip()


def compact_prompt(row):
    return (
        f"Repo: {row['repo']}\n"
        f"Engine domain: {row['domain']}\n"
        f"Issue #{row['issue_number']}: {row['title']}\n"
        f"Source: {row['issue_url']}\n\n"
        "Task: Diagnose the likely cause and propose a concrete fix. "
        "If code is useful, include a concise patch-style code example."
    )


def is_good_teacher(row, min_score):
    answer = row.get("answer", "").strip()
    if row.get("candidate") != "qwen2.5_7b":
        return False
    if row.get("metrics", {}).get("score", 0) < min_score:
        return False
    if len(answer) < 120:
        return False
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", default="eval/results_github_issue_yuspec_qwen7b.jsonl")
    parser.add_argument("--base-instruction", action="append", default=[
        "data/instructions/benchmark_realign_v4.jsonl",
        "data/instructions/multiengine_v2.jsonl",
    ])
    parser.add_argument("--out", default="data/instructions/github_issue_distill_qwen7b_v1.jsonl")
    parser.add_argument("--teacher-repeat", type=int, default=24)
    parser.add_argument("--base-repeat", type=int, default=2)
    parser.add_argument("--min-score", type=int, default=7)
    parser.add_argument("--seed", type=int, default=20260509)
    args = parser.parse_args()

    result_rows = read_jsonl(args.results)
    teacher_rows = [row for row in result_rows if is_good_teacher(row, args.min_score)]

    rows = []
    for row in teacher_rows:
        answer = row["answer"].strip()
        prompts = [
            trim_prompt(row["prompt"]),
            compact_prompt(row),
            f"{row['domain']} projesindeki şu issue için çözüm öner: {row['title']}",
        ]
        for _ in range(args.teacher_repeat):
            for prompt in prompts:
                rows.append(
                    {
                        "domain": row["domain"],
                        "instruction": prompt,
                        "answer": answer,
                        "source": row["issue_url"],
                        "teacher": "qwen2.5_7b",
                    }
                )

    base_rows = []
    for path in args.base_instruction:
        p = Path(path)
        if p.exists():
            base_rows.extend(read_jsonl(p))
    for _ in range(args.base_repeat):
        for row in base_rows:
            if "instruction" in row and "answer" in row:
                rows.append(
                    {
                        "domain": row.get("domain", "godot"),
                        "instruction": row["instruction"],
                        "answer": row["answer"],
                        "source": row.get("source", "local_instruction"),
                    }
                )

    random.seed(args.seed)
    random.shuffle(rows)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"teacher rows: {len(teacher_rows)}")
    print(f"base rows: {len(base_rows)}")
    print(f"wrote {len(rows)} rows to {out}")


if __name__ == "__main__":
    main()
