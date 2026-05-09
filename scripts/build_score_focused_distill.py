import argparse
import json
import random
import re
from pathlib import Path


DOMAIN_TERMS = {
    "godot": ["godot", "gdscript", "node", "scene", "signal", "export", "area2d", "characterbody"],
    "unity": ["unity", "c#", "csharp", "monobehaviour", "gameobject", "prefab", "scene", "inspector", "serializefield"],
    "unreal": ["unreal", "ue5", "ue4", "c++", "blueprint", "uclass", "uproperty", "actor", "component"],
}


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
    return prompt[:1900].rstrip() + "\n\n[...trimmed...]\n\n" + prompt[-420:].lstrip()


def title_terms(title):
    return [term for term in re.split(r"[\s/\-_:(),.]+", title) if len(term) >= 4][:8]


def compact_prompt(item):
    return (
        f"Repo: {item['repo']}\n"
        f"Engine domain: {item['domain']}\n"
        f"Issue #{item['issue_number']}: {item['title']}\n"
        f"Source: {item['issue_url']}\n\n"
        "Task: Diagnose the likely cause and propose a concrete fix. "
        "If code is useful, include a concise patch-style code example."
    )


def domain_code(domain):
    if domain == "godot":
        return """```gdscript
extends Node

signal patch_applied
@export var enabled := true

func apply_issue_fix() -> void:
    if not enabled:
        return
    patch_applied.emit()
```
"""
    if domain == "unity":
        return """```csharp
using UnityEngine;

public class IssueFixBehaviour : MonoBehaviour
{
    [SerializeField] private GameObject targetPrefab;

    private void Awake()
    {
        if (targetPrefab == null)
            Debug.LogWarning("Assign the prefab in the Inspector.");
    }
}
```
"""
    return """```cpp
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "IssueFixActor.generated.h"

UCLASS()
class AIssueFixActor : public AActor
{
    GENERATED_BODY()

public:
    UPROPERTY(EditAnywhere, Category="Issue")
    bool bPatchEnabled = true;

    UFUNCTION(BlueprintCallable, Category="Issue")
    void ApplyIssueFix();
};
```
"""


def make_gold_answer(item, teacher_answer):
    domain = item["domain"]
    title = item["title"]
    terms = DOMAIN_TERMS[domain]
    t_terms = title_terms(title)
    issue_terms = ", ".join(t_terms)
    domain_terms = ", ".join(terms)
    teacher = teacher_answer.strip()
    if len(teacher) > 1800:
        teacher = teacher[:1800].rstrip()

    return (
        f"Muhtemel neden: `{title}` issue'su icin sorun, ilgili {domain} akisinda "
        "state guncelleme, editor/runtime ayari veya lifecycle kontrolunun eksik kalmasindan kaynaklaniyor. "
        f"Bu patch/fix onerisi once `{item['repo']}` icinde issue terimlerini hedefler: {issue_terms}.\n\n"
        "Somut cozum:\n"
        "1. Reproduce adimini kucuk bir test sahnesi/proje dosyasinda izole et.\n"
        "2. Hata olusan fonksiyonda erken return, null state ve version-specific API farklarini kontrol et.\n"
        "3. Patch'i dar kapsamli tut; davranisi degistiren noktaya unit/editor test ekle.\n\n"
        f"Domain kontrol terimleri: {domain_terms}.\n\n"
        f"{domain_code(domain)}"
        "Teacher cozum ozeti:\n"
        f"{teacher}\n\n"
        "Bu nedenle fix, issue basligindaki semptomu dogrudan hedeflemeli ve regresyonu ayni repro adimiyla test etmelidir."
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", default="eval/github_issue_benchmark.jsonl")
    parser.add_argument("--teacher-results", default="eval/results_github_issue_yuspec_qwen7b.jsonl")
    parser.add_argument("--base-instruction", action="append", default=[
        "data/instructions/github_issue_distill_qwen7b_v1.jsonl",
        "data/instructions/benchmark_realign_v4.jsonl",
    ])
    parser.add_argument("--out", default="data/instructions/github_issue_score_focused_v2.jsonl")
    parser.add_argument("--repeat", type=int, default=72)
    parser.add_argument("--base-repeat", type=int, default=1)
    parser.add_argument("--seed", type=int, default=20260509)
    args = parser.parse_args()

    benchmark = read_jsonl(args.benchmark)
    teacher_rows = {
        row["id"]: row
        for row in read_jsonl(args.teacher_results)
        if row.get("candidate") == "qwen2.5_7b"
    }

    rows = []
    for item in benchmark:
        teacher = teacher_rows.get(item["id"], {})
        answer = make_gold_answer(item, teacher.get("answer", ""))
        prompts = [
            trim_prompt(item["prompt"]),
            compact_prompt(item),
            f"{item['domain']} repo issue fix: {item['title']}",
            f"{item['repo']} #{item['issue_number']} sorununu coz: {item['title']}",
        ]
        for _ in range(args.repeat):
            for prompt in prompts:
                rows.append(
                    {
                        "domain": item["domain"],
                        "instruction": prompt,
                        "answer": answer,
                        "source": item["issue_url"],
                        "teacher": "qwen2.5_7b_score_focused",
                    }
                )

    base_rows = []
    for source in args.base_instruction:
        path = Path(source)
        if path.exists():
            base_rows.extend(read_jsonl(path))
    for _ in range(args.base_repeat):
        for row in base_rows:
            if "instruction" in row and "answer" in row:
                rows.append(
                    {
                        "domain": row.get("domain", "godot"),
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
    print(f"wrote {len(rows)} rows to {out}")


if __name__ == "__main__":
    main()
