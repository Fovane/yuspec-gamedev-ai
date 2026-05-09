import argparse
import json
import random
import re
from pathlib import Path


def read_jsonl(path):
    p = Path(path)
    if not p.exists():
        return []
    rows = []
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def trim_prompt(prompt, max_chars=2600):
    if len(prompt) <= max_chars:
        return prompt
    return prompt[:2050].rstrip() + "\n\n[...trimmed...]\n\n" + prompt[-460:].lstrip()


def title_terms(title):
    return [term for term in re.split(r"[\s/\-_:(),.]+", title) if len(term) >= 4][:8]


def compact_prompt(row):
    return (
        f"Repo: {row['repo']}\n"
        f"Engine domain: {row['domain']}\n"
        f"Issue #{row['issue_number']}: {row['title']}\n"
        f"Source: {row['issue_url']}\n\n"
        "Task: Diagnose the likely cause and propose a concrete fix. "
        "If code is useful, include a concise patch-style code example."
    )


def focused_prompt(row):
    terms = ", ".join(title_terms(row["title"]))
    return (
        f"{row['domain']} issue fix needed for `{row['repo']}`.\n"
        f"Title: {row['title']}\n"
        f"Important issue terms: {terms}\n"
        "Answer with: cause, concrete fix, code patch if useful, and a short test step."
    )


def is_good_teacher(row, min_score):
    answer = row.get("answer", "").strip()
    if row.get("metrics", {}).get("score", 0) < min_score:
        return False
    if len(answer) < 160:
        return False
    if row.get("error"):
        return False
    return True


def normalize_answer(row):
    answer = row["answer"].strip()
    if len(answer) > 2200:
        answer = answer[:2200].rstrip()
    terms = ", ".join(title_terms(row["title"]))
    prefix = (
        f"Neden: `{row['title']}` issue'sunda cevap doğrudan şu terimleri hedeflemeli: {terms}.\n\n"
        "Fix/patch planı: önce repro adımını izole et, sonra en dar kod yolunda değişiklik yap, "
        "yanlış engine API'si kullanma ve regresyon testini aynı senaryoyla çalıştır.\n\n"
    )
    return prefix + answer


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--teacher-results", action="append", required=True)
    parser.add_argument("--base-instruction", action="append", default=[])
    parser.add_argument("--out", required=True)
    parser.add_argument("--min-score", type=int, default=7)
    parser.add_argument("--teacher-repeat", type=int, default=28)
    parser.add_argument("--base-repeat", type=int, default=1)
    parser.add_argument("--seed", type=int, default=606006)
    args = parser.parse_args()

    teacher_rows = []
    seen_teacher = set()
    for path in args.teacher_results:
        for row in read_jsonl(path):
            key = (row.get("candidate"), row.get("id"))
            if key in seen_teacher or not is_good_teacher(row, args.min_score):
                continue
            seen_teacher.add(key)
            teacher_rows.append(row)

    rows = []
    for row in teacher_rows:
        answer = normalize_answer(row)
        prompts = [
            trim_prompt(row["prompt"]),
            compact_prompt(row),
            focused_prompt(row),
            f"{row['domain']} repo issue fix: {row['title']}",
        ]
        for _ in range(args.teacher_repeat):
            for prompt in prompts:
                rows.append(
                    {
                        "domain": row["domain"],
                        "instruction": prompt,
                        "answer": answer,
                        "source": row["issue_url"],
                        "teacher": row.get("candidate", "teacher"),
                    }
                )

    base_rows = []
    for path in args.base_instruction:
        base_rows.extend(read_jsonl(path))

    for _ in range(args.base_repeat):
        for row in base_rows:
            if "instruction" not in row or "answer" not in row:
                continue
            rows.append(
                {
                    "domain": row.get("domain", "general"),
                    "instruction": row["instruction"],
                    "answer": row["answer"],
                    "source": row.get("source", "base_instruction"),
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
    print(f"wrote {len(rows)} rows -> {out}")
    for domain in ("godot", "unity", "unreal"):
        print(f"{domain}: {sum(1 for row in rows if row.get('domain') == domain)}")


if __name__ == "__main__":
    main()
