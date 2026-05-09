import argparse
import json
import sys
from pathlib import Path

import torch
from tokenizers import Tokenizer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from model import GPT, GPTConfig  # noqa: E402


DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

EXPECTATIONS = {
    "godot_move_2d": ("CharacterBody2D", "velocity", "move_and_slide", "Input.get_vector"),
    "godot_coin": ("Area2D", "body_entered", "queue_free"),
    "godot_signal": ("signal", "emit", "connect"),
    "godot_enemy_follow": ("global_position", "direction_to", "velocity", "move_and_slide"),
    "godot_camera": ("Camera2D", "current"),
    "godot_health": ("health", "take_damage", "signal"),
    "godot_error_nil": ("null", "node", "get_node"),
    "godot_scene_arch": ("player", "world", "ui"),
    "unity_move": ("MonoBehaviour", "CharacterController", "Update", "Time.deltaTime"),
    "unity_health": ("Health", "TakeDamage", "SerializeField"),
    "unity_coin": ("OnTriggerEnter", "Destroy", "GetComponent"),
    "unity_scriptable_object": ("ScriptableObject", "CreateAssetMenu"),
    "unreal_character": ("ACharacter", "AddMovementInput", "SetupPlayerInputComponent"),
    "unreal_actor": ("AActor", "Tick", "UPROPERTY"),
    "unreal_reflection": ("UPROPERTY", "UFUNCTION", "Blueprint"),
    "unreal_health": ("UActorComponent", "BlueprintCallable", "FMath"),
}


def read_jsonl(path):
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def domain_prefix(domain):
    return {
        "godot": "<|godot|>\n",
        "unity": "Domain: Unity\n",
        "unreal": "Domain: Unreal Engine\n",
        "general": "",
    }.get(domain, "<|godot|>\n")


def build_prompt(prompt, domain):
    return (
        f"<|bos|>{domain_prefix(domain)}"
        "<|user|>\n"
        f"{prompt}\n"
        "<|assistant|>\n"
    )


def load_model(checkpoint_path):
    ckpt = torch.load(checkpoint_path, map_location=DEVICE)
    cfg = ckpt["config"]

    model_cfg = GPTConfig(**cfg["model"])
    model = GPT(model_cfg).to(DEVICE)
    model.load_state_dict(ckpt["model"])
    model.eval()

    tokenizer = Tokenizer.from_file(cfg["data"]["tokenizer_path"])
    return model, tokenizer


def generate_answer(model, tokenizer, prompt, domain, max_new_tokens, temperature, top_k):
    prompt_text = build_prompt(prompt, domain)
    ids = tokenizer.encode(prompt_text).ids
    x = torch.tensor([ids], dtype=torch.long, device=DEVICE)
    eos_id = tokenizer.token_to_id("<|eos|>")

    out = model.generate(
        x,
        max_new_tokens=max_new_tokens,
        temperature=temperature,
        top_k=top_k,
        eos_id=eos_id,
        vocab_limit=tokenizer.get_vocab_size(),
    )

    decoded = tokenizer.decode(out[0].tolist())
    if prompt in decoded:
        return decoded.split(prompt, 1)[1].strip()
    return decoded.strip()


def score_answer(item, answer):
    text = answer.lower()
    score = 0
    checks = {}

    checks["not_empty"] = len(answer.strip()) >= 40
    checks["no_mojibake"] = not has_mojibake(answer)
    checks["no_markdown_leak"] = "```" not in answer or answer.count("```") % 2 == 0
    checks["not_repetitive"] = max_repeated_line_count(answer) <= 2

    if item.get("type") == "code":
        domain = item.get("domain", "godot")
        code_signals = {
            "godot": ("extends ", "func ", "var ", "@export", "move_and_slide"),
            "unity": ("using UnityEngine", "MonoBehaviour", "void ", "SerializeField", "GetComponent"),
            "unreal": ("UCLASS", "UPROPERTY", "UFUNCTION", "AActor", "ACharacter", "::"),
        }
        checks["has_code_signal"] = any(
            token in answer for token in code_signals.get(domain, code_signals["godot"])
        )
        checks["no_obvious_syntax_junk"] = not has_obvious_syntax_junk(answer)
    else:
        checks["has_explanation"] = len(answer.split()) >= 15
        checks["mostly_words"] = word_ratio(text) >= 0.65

    expected_tokens = EXPECTATIONS.get(item["id"], ())
    if expected_tokens:
        checks["has_expected_terms"] = expected_term_ratio(answer, expected_tokens) >= 0.5

    for passed in checks.values():
        score += int(passed)

    return {
        "score": score,
        "max_score": len(checks),
        "checks": checks,
    }


def max_repeated_line_count(text):
    counts = {}
    for line in (line.strip() for line in text.splitlines()):
        if not line:
            continue
        counts[line] = counts.get(line, 0) + 1
    return max(counts.values(), default=0)


def has_mojibake(text):
    return any(token in text for token in ("Ä", "Ã", "Å", "Â"))


def has_obvious_syntax_junk(text):
    junk_tokens = (
        ".0",
        "Input.0",
        "data.ZERO",
        "if level.global_position =",
        "func _physics_position",
    )
    return any(token in text for token in junk_tokens)


def word_ratio(text):
    if not text.strip():
        return 0.0
    word_chars = sum(ch.isalpha() or ch.isspace() for ch in text)
    return word_chars / len(text)


def expected_term_ratio(answer, expected_tokens):
    answer_lower = answer.lower()
    found = sum(token.lower() in answer_lower for token in expected_tokens)
    return found / len(expected_tokens)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--benchmark", default="eval/godot_v0_benchmark.jsonl")
    parser.add_argument("--out", default="eval/results.jsonl")
    parser.add_argument("--max-new-tokens", type=int, default=220)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--top-k", type=int, default=40)
    parser.add_argument("--seed", type=int, default=1234)
    args = parser.parse_args()

    torch.manual_seed(args.seed)
    model, tokenizer = load_model(args.checkpoint)
    rows = []

    for item in read_jsonl(args.benchmark):
        answer = generate_answer(
            model,
            tokenizer,
            item["prompt"],
            item.get("domain", "godot"),
            args.max_new_tokens,
            args.temperature,
            args.top_k,
        )
        result = {
            "id": item["id"],
            "prompt": item["prompt"],
            "type": item.get("type"),
            "answer": answer,
            "metrics": score_answer(item, answer),
        }
        rows.append(result)
        print(f"{result['id']}: {result['metrics']['score']}/{result['metrics']['max_score']}")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    total = sum(row["metrics"]["score"] for row in rows)
    max_total = sum(row["metrics"]["max_score"] for row in rows)
    print(f"total: {total}/{max_total}")
    print(f"wrote: {out_path}")


if __name__ == "__main__":
    main()
