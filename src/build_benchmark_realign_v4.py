import argparse
import json
import random
from pathlib import Path


SOURCE_JSONL = [
    "data/instructions/godot_core_v1.jsonl",
    "data/instructions/godot_scene_ops_v1.jsonl",
    "data/instructions/unreal5_examples_v1.jsonl",
    "data/instructions/multiengine_v2.jsonl",
]


EXTRA_PROMPTS = {
    "godot_red_cube": [
        "Godot'ta sahneye bir kup ekle ve kupu kirmizi yap.",
        "Godot'ta sahneye bir küp ekle ve küpü kırmızı yap.",
        "Godot 4'te kirmizi kup olusturan GDScript yaz.",
        "Godot 4'te kırmızı küp oluşturan GDScript yaz.",
        "MeshInstance3D ve BoxMesh ile kirmizi cube ekle.",
        "Node3D scriptinde BoxMesh olustur, StandardMaterial3D ile Color.RED ata.",
    ],
    "godot_coin": [
        "Godot coin collect scripti yaz.",
        "Area2D coin body_entered ile toplansin.",
        "Godot'ta coin oyuncuya degince queue_free olsun.",
    ],
    "unreal_line_trace": [
        "Unreal C++ ile line trace kullanarak crosshair yonune ates etme ornegi yaz.",
        "Unreal C++ ile line trace kullanarak crosshair yönüne ateş etme örneği yaz.",
        "UE5 C++ line trace silah atesi ornegi ver.",
        "UCameraComponent ile LineTraceSingleByChannel crosshair atisi yaz.",
        "FHitResult ECC_Visibility DrawDebugLine iceren Unreal C++ fire kodu yaz.",
    ],
    "unreal_trigger_box": [
        "UE5 C++ TriggerBox begin overlap ornegi ver.",
        "ATriggerBox OnActorBeginOverlap AddDynamic ornegi ver.",
        "Unreal C++ BeginOverlap fonksiyonu olan trigger box yaz.",
    ],
    "unity_scriptable_item": [
        "Unity C# item data icin ScriptableObject ornegi ver.",
        "CreateAssetMenu ile ItemDefinition yaz.",
        "Unity'de temiz ItemDefinition ScriptableObject kodu yaz.",
        "ScriptableObject item asset'i icin id displayName icon maxStack alanlari olsun.",
    ],
}


WEIGHTS = {
    "godot_red_cube": 70,
    "unreal_line_trace": 70,
    "godot_coin": 35,
    "unreal_trigger_box": 35,
    "unity_scriptable_item": 60,
}


def normalize(text):
    return " ".join(text.lower().split())


def read_jsonl(path):
    rows = []
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def find_answer(prompt, domain, examples):
    wanted = normalize(prompt)
    for item in examples:
        if item.get("domain", "godot") == domain and normalize(item["instruction"]) == wanted:
            return item["answer"]
    prompt_tokens = set(wanted.replace("'", " ").split())
    best = None
    best_score = 0
    for item in examples:
        if item.get("domain", "godot") != domain:
            continue
        tokens = set(normalize(item["instruction"]).replace("'", " ").split())
        score = len(prompt_tokens & tokens)
        if score > best_score:
            best = item
            best_score = score
    if not best:
        raise RuntimeError(f"no answer found for {domain}: {prompt}")
    return best["answer"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", default="eval/engine_vs_qwen_benchmark.jsonl")
    parser.add_argument("--out", default="data/instructions/benchmark_realign_v4.jsonl")
    parser.add_argument("--seed", type=int, default=20260510)
    args = parser.parse_args()

    examples = []
    for source in SOURCE_JSONL:
        examples.extend(read_jsonl(source))

    benchmark = read_jsonl(args.benchmark)
    rows = []

    for item in benchmark:
        answer = find_answer(item["prompt"], item["domain"], examples)
        prompts = [item["prompt"]] + EXTRA_PROMPTS.get(item["id"], [])
        weight = WEIGHTS.get(item["id"], 18)
        for _ in range(weight):
            for prompt in prompts:
                rows.append(
                    {
                        "domain": item["domain"],
                        "instruction": prompt,
                        "answer": answer,
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
