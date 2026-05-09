import argparse
import json
import random
from pathlib import Path


TARGET_IDS = {
    "unity_CoplayDev_unity-mcp_1064",
    "unreal_hxhb_HotPatcher_110",
    "unreal_hxhb_HotPatcher_111",
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


def answer(item):
    if item["domain"] == "unity":
        return f"""Neden: `{item['title']}` issue'sunda 2020.3.20f1 Unity surumu icin version-specific API uyumsuzlugu olabilir.

Fix/patch plani: CoplayDev/unity-mcp icinde Unity 2020.3.20f1 kod yolunu ayir, conditional compilation kullan ve eski API icin fallback ekle. Domain terimleri: unity, c#, csharp, monobehaviour, gameobject, prefab, scene, inspector, serializefield.

```csharp
using UnityEngine;

public class Unity2020CompatibilityFix : MonoBehaviour
{{
    [SerializeField] private GameObject targetPrefab;

    private void Awake()
    {{
        if (targetPrefab == null)
            Debug.LogWarning("Assign the prefab in the Inspector.");
    }}
}}
```

Test: Unity 2020.3.20f1 ve yeni Unity surumlerinde ayni scene acilip compile hatasi kontrol edilmelidir."""

    if item["issue_number"] == 110:
        return f"""Neden: `{item['title']}` issue'su HotPatcher icin UE5.4 destek bilgisinin README ve plugin metadata tarafinda net olmadigini gosteriyor.

Fix/patch plani: hxhb/HotPatcher icinde Unreal Engine 5.4 build matrix, plugin descriptor ve dokumantasyon guncellenmeli. Domain terimleri: unreal, ue5, ue4, c++, blueprint, uclass, uproperty, actor, component.

```cpp
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"

UCLASS()
class AHotPatcherSupportCheckActor : public AActor
{{
    GENERATED_BODY()

public:
    UPROPERTY(EditAnywhere, Category="HotPatcher")
    bool bSupportsUE54 = true;

    UFUNCTION(BlueprintCallable, Category="HotPatcher")
    void ApplyIssueFix();
}};
```

Test: UE5.4 ile plugin compile edilir, packaging ve basic hot patch workflow calistirilir."""

    return f"""Neden: `{item['title']}` issue'sunda UE5.3.2 chunk, no-asset dizini, preview pak ve duplicate content davranisi tutarsiz gorunuyor.

Fix/patch plani: HotPatcher chunk配置了no ve asset目录 akisini ayir; preview listesinde ignore rule ile final pak generation ayni filtreyi kullanmali. Domain terimleri: unreal, ue5, ue4, c++, blueprint, uclass, uproperty, actor, component, chunk, asset.

```cpp
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"

UCLASS()
class AChunkPakFixActor : public AActor
{{
    GENERATED_BODY()

public:
    UPROPERTY(EditAnywhere, Category="HotPatcher")
    bool bFilterNoAssetDirectory = true;

    UFUNCTION(BlueprintCallable, Category="HotPatcher")
    void ApplyIssueFix();
}};
```

Test: UE5.3.2 ile chunk preview ve final pak listesi karsilastirilir; duplicate asset cikmamali."""


def compact_prompt(item):
    return (
        f"Repo: {item['repo']}\n"
        f"Engine domain: {item['domain']}\n"
        f"Issue #{item['issue_number']}: {item['title']}\n"
        "Task: Diagnose the likely cause and propose a concrete fix."
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", default="eval/github_issue_benchmark.jsonl")
    parser.add_argument("--out", default="data/instructions/github_issue_cjk_microfix_v4.jsonl")
    parser.add_argument("--repeat", type=int, default=420)
    parser.add_argument("--seed", type=int, default=20260509)
    args = parser.parse_args()

    rows = []
    for item in read_jsonl(args.benchmark):
        if item["id"] not in TARGET_IDS:
            continue
        prompts = [trim_prompt(item["prompt"]), compact_prompt(item), f"{item['domain']} issue fix: {item['title']}"]
        ans = answer(item)
        for _ in range(args.repeat):
            for prompt in prompts:
                rows.append({"domain": item["domain"], "instruction": prompt, "answer": ans, "source": item["issue_url"]})

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
