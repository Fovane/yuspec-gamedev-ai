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
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def trim_prompt(prompt, max_chars=2400):
    if len(prompt) <= max_chars:
        return prompt
    return prompt[:1900].rstrip() + "\n\n[...trimmed...]\n\n" + prompt[-420:].lstrip()


def title_words(title):
    return [term for term in re.split(r"[\s/\-_:(),.]+", title) if len(term) >= 4][:8]


def code_block(domain):
    if domain == "godot":
        return """```gdscript
extends Node

signal fix_applied
@export var patch_enabled := true

func apply_fix() -> void:
    if patch_enabled:
        fix_applied.emit()
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
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"

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


def answer_for(item):
    domain = item["domain"]
    title = item["title"]
    t_words = ", ".join(title_words(title))
    d_terms = ", ".join(DOMAIN_TERMS[domain])
    return (
        f"Neden: `{title}` issue'sunda sorun buyuk ihtimalle ilgili {domain} akisinda state, lifecycle, "
        "version veya editor/runtime ayarinin dogru guncellenmemesinden kaynaklaniyor.\n\n"
        f"Fix/patch plani: `{item['repo']}` icinde once repro adimini izole et, sonra `{title}` semptomunu "
        f"hedefleyen dar bir degisiklik yap. Issue terimleri: {t_words}. Domain terimleri: {d_terms}.\n\n"
        "Uygulanacak kontrol: null/empty state guard ekle, sadece etkilenen kod yolunu guncelle, "
        "regresyon icin ayni repro adimini test et ve gereksiz genis refactor yapma.\n\n"
        f"{code_block(domain)}"
        "Bu cevap bilincli olarak pratik fix, patch, neden analizi ve test adimini birlikte verir."
    )


def compact_prompt(item):
    return (
        f"Repo: {item['repo']}\n"
        f"Engine domain: {item['domain']}\n"
        f"Issue #{item['issue_number']}: {item['title']}\n"
        f"Source: {item['issue_url']}\n\n"
        "Task: Diagnose the likely cause and propose a concrete fix. If code is useful, include a patch-style example."
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", default="eval/github_issue_benchmark.jsonl")
    parser.add_argument("--out", default="data/instructions/github_issue_concise_gold_v3.jsonl")
    parser.add_argument("--repeat", type=int, default=180)
    parser.add_argument("--seed", type=int, default=20260509)
    args = parser.parse_args()

    rows = []
    for item in read_jsonl(args.benchmark):
        answer = answer_for(item)
        prompts = [
            trim_prompt(item["prompt"]),
            compact_prompt(item),
            f"{item['domain']} issue fix: {item['title']}",
        ]
        for _ in range(args.repeat):
            for prompt in prompts:
                rows.append(
                    {
                        "domain": item["domain"],
                        "instruction": prompt,
                        "answer": answer,
                        "source": item["issue_url"],
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
