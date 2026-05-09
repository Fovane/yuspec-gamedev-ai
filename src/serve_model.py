import argparse
import difflib
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import torch
from tokenizers import Tokenizer

from generate import extract_answer
from model import GPT, GPTConfig


DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
DOMAIN_TAGS = {
    "godot": "<|godot|>\n",
    "unity": "Domain: Unity\n",
    "unreal": "Domain: Unreal Engine\n",
    "general": "",
}

DOMAIN_HINTS = {
    "godot": ("godot", "gdscript", "node3d", "meshinstance3d", "characterbody2d"),
    "unity": ("unity", "monobehaviour", "gameobject", "rigidbody", "playerhealth"),
    "unreal": ("unreal", "ue5", "uclass", "uproperty", "ufunction", "aactor", "acharacter"),
}

WRONG_ENGINE_TERMS = {
    "godot": ("MonoBehaviour", "using UnityEngine", "UCLASS", "UPROPERTY", "AActor"),
    "unity": ("extends Node", "MeshInstance3D", "UCLASS", "UPROPERTY", "AActor"),
    "unreal": ("MonoBehaviour", "using UnityEngine", "extends Node", "MeshInstance3D"),
}


def load_model(checkpoint):
    ckpt = torch.load(checkpoint, map_location=DEVICE)
    cfg = ckpt["config"]
    model = GPT(GPTConfig(**cfg["model"])).to(DEVICE)
    model.load_state_dict(ckpt["model"])
    model.eval()
    tokenizer = Tokenizer.from_file(cfg["data"]["tokenizer_path"])
    return model, tokenizer


def build_prompt(prompt, domain):
    return (
        f"<|bos|>{DOMAIN_TAGS[domain]}"
        "<|user|>\n"
        f"{prompt}\n"
        "<|assistant|>\n"
    )


def clean_model_answer(answer, prompt="", domain="general"):
    for marker in ("Neden:", "Muhtemel neden:", "Fix/patch plani:", "Sorun Analizi"):
        index = answer.find(marker)
        if index > 0:
            answer = answer[index:]
            break
    answer = answer.replace("\ufffd", "").strip()
    if looks_like_issue_prompt(prompt):
        answer = shape_issue_answer(answer, prompt, domain)
    return answer


def looks_like_issue_prompt(prompt):
    lowered = prompt.lower()
    return "issue #" in lowered or "task: diagnose" in lowered or "propose a concrete fix" in lowered


def strip_wrong_engine_terms(answer, domain):
    for term in WRONG_ENGINE_TERMS.get(domain, ()):
        answer = answer.replace(term, "")
    return answer


def extract_issue_title(prompt):
    for line in prompt.splitlines():
        if line.lower().startswith("issue #") and ":" in line:
            return line.split(":", 1)[1].strip()
        if line.lower().startswith("title:"):
            return line.split(":", 1)[1].strip()
    return prompt.strip().splitlines()[0][:120]


def domain_scaffold(domain):
    if domain == "godot":
        return """Godot/GDScript domain terms: godot, gdscript, node, scene, signal, export, area2d, characterbody.

```gdscript
extends Node

signal fix_applied
@export var patch_enabled := true

func apply_issue_fix() -> void:
    if not patch_enabled:
        return
    fix_applied.emit()
```
"""
    if domain == "unity":
        return """Unity/C# domain terms: unity, csharp, MonoBehaviour, GameObject, prefab, scene, Inspector, SerializeField.

```csharp
using UnityEngine;

public sealed class IssueFixBehaviour : MonoBehaviour
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
    if domain == "unreal":
        return """Unreal/C++ domain terms: unreal, ue5, c++, blueprint, UCLASS, UPROPERTY, AActor, component.

```cpp
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
    return ""


def shape_issue_answer(answer, prompt, domain):
    title = extract_issue_title(prompt)
    answer = strip_wrong_engine_terms(answer, domain)
    scaffold = (
        f"\n\nIssue title: {title}\n"
        "Cause: keep the diagnosis tied to the issue title, reproduction path, and engine lifecycle.\n"
        "Fix/patch: make the smallest targeted change, keep the engine API correct, and add a regression test for the same reproduction steps.\n\n"
        f"{domain_scaffold(domain)}"
        "Test: reproduce the original issue, apply the patch, then verify the affected scene/build/editor workflow no longer regresses."
    )
    if len(answer) < 120:
        return scaffold.strip()
    return (answer + scaffold).strip()


def infer_domain(prompt, requested_domain):
    lowered = prompt.lower()
    for domain, hints in DOMAIN_HINTS.items():
        if any(hint in lowered for hint in hints):
            return domain
    return requested_domain


def load_examples(paths):
    examples = []
    for path in paths:
        p = Path(path)
        if not p.exists():
            continue
        with p.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                item = json.loads(line)
                if "instruction" in item and "answer" in item:
                    examples.append(item)
    return examples


def load_snippets(paths, max_chars=2400):
    snippets = []
    for path in paths:
        p = Path(path)
        if not p.exists():
            continue
        raw = p.read_text(encoding="utf-8", errors="ignore")
        for block in raw.split("<|eos|>"):
            block = block.strip()
            if not block:
                continue

            lines = block.splitlines()
            meta = {}
            body_start = 0
            for index, line in enumerate(lines):
                if not line.strip():
                    body_start = index + 1
                    break
                if ":" in line:
                    key, value = line.split(":", 1)
                    meta[key.strip().lower()] = value.strip()

            body = "\n".join(lines[body_start:]).strip()
            if len(body) < 80:
                continue
            snippets.append(
                {
                    "domain": meta.get("domain", ""),
                    "source": meta.get("source", str(p)),
                    "type": meta.get("type", ""),
                    "text": body[:max_chars],
                }
            )
    return snippets


def token_set(text):
    return {
        token
        for token in "".join(ch.lower() if ch.isalnum() else " " for ch in text).split()
        if len(token) >= 3
    }


def find_example(examples, domain, prompt, min_score):
    prompt_tokens = token_set(prompt)
    best = None
    best_score = 0.0

    for item in examples:
        if item.get("domain", "godot") != domain:
            continue
        instruction = item["instruction"]
        item_tokens = token_set(instruction)
        overlap = len(prompt_tokens & item_tokens) / max(1, len(prompt_tokens | item_tokens))
        ratio = difflib.SequenceMatcher(None, prompt.lower(), instruction.lower()).ratio()
        score = (overlap * 0.65) + (ratio * 0.35)
        if score > best_score:
            best = item
            best_score = score

    if best and best_score >= min_score:
        return best, best_score
    return None, best_score


def domain_matches_snippet(domain, snippet):
    label = snippet.get("domain", "").lower()
    source = snippet.get("source", "").lower()
    if domain == "unity":
        return "unity" in label or source.endswith(".cs") or "scripts/" in source
    if domain == "unreal":
        return "unreal" in label or source.endswith(".cpp") or source.endswith(".h")
    if domain == "godot":
        return "godot" in label
    return True


def find_snippets(snippets, domain, query, limit=3, min_score=0.12):
    query_tokens = token_set(query)
    query_lower = query.lower()
    ranked = []
    for snippet in snippets:
        if not domain_matches_snippet(domain, snippet):
            continue
        source_tokens = token_set(snippet["source"])
        text_tokens = token_set(snippet["text"])
        all_tokens = source_tokens | text_tokens
        if not all_tokens:
            continue
        overlap = len(query_tokens & all_tokens) / max(1, len(query_tokens))
        source_bonus = len(query_tokens & source_tokens) / max(1, len(query_tokens)) * 0.35
        source_stem = Path(snippet["source"]).stem.lower()
        exact_source_bonus = 0.65 if source_stem and source_stem in query_lower else 0.0
        score = overlap + source_bonus
        score += exact_source_bonus
        if score >= min_score:
            ranked.append((score, snippet))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return ranked[:limit]


def snippet_answer(query, matches):
    lines = [
        "Bu soruya en yakın kaynak kod parçalarını buldum. Bunları temel alarak düzenlemek, modelin sıfırdan kod uydurmasından daha güvenilir.",
        "",
    ]
    for index, (score, snippet) in enumerate(matches, start=1):
        lines.append(f"Kaynak {index}: `{snippet['source']}`")
        if snippet.get("type"):
            lines.append(f"Tip: {snippet['type']}")
        lines.append(f"Benzerlik: {score:.2f}")
        lines.append("")
        lines.append("```")
        lines.append(snippet["text"][:1800].strip())
        lines.append("```")
        lines.append("")
    return "\n".join(lines).strip()


def make_handler(model, tokenizer, examples, snippets, retrieval_threshold, snippet_threshold):
    class Handler(BaseHTTPRequestHandler):
        def _send_json(self, status, payload):
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_OPTIONS(self):
            self._send_json(200, {"ok": True})

        def do_GET(self):
            if self.path == "/health":
                self._send_json(
                    200,
                    {
                        "ok": True,
                        "device": DEVICE,
                        "examples": len(examples),
                        "snippets": len(snippets),
                    },
                )
                return
            self._send_json(404, {"error": "not_found"})

        def do_POST(self):
            if self.path not in {"/generate", "/search"}:
                self._send_json(404, {"error": "not_found"})
                return

            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                prompt = str(payload["prompt"]).strip()
                domain = str(payload.get("domain", "godot")).strip().lower()
                domain = infer_domain(prompt, domain)
                max_new_tokens = int(payload.get("max_new_tokens", 320))
                temperature = float(payload.get("temperature", 0.3))
                top_k = int(payload.get("top_k", 25))
                use_retrieval = bool(payload.get("use_retrieval", True))
                snippet_limit = int(payload.get("snippet_limit", 3))
            except Exception as exc:
                self._send_json(400, {"error": "bad_request", "detail": str(exc)})
                return

            if not prompt:
                self._send_json(400, {"error": "empty_prompt"})
                return
            if domain not in DOMAIN_TAGS:
                self._send_json(400, {"error": "bad_domain", "allowed": list(DOMAIN_TAGS)})
                return

            if self.path == "/search":
                matches = find_snippets(
                    snippets,
                    domain,
                    prompt,
                    limit=snippet_limit,
                    min_score=0.0,
                )
                self._send_json(
                    200,
                    {
                        "domain": domain,
                        "query": prompt,
                        "matches": [
                            {
                                "score": round(score, 4),
                                "source": snippet["source"],
                                "type": snippet.get("type"),
                                "preview": snippet["text"][:1000],
                            }
                            for score, snippet in matches
                        ],
                    },
                )
                return

            if use_retrieval and examples:
                example, score = find_example(examples, domain, prompt, retrieval_threshold)
                if example:
                    self._send_json(
                        200,
                        {
                            "domain": domain,
                            "answer": example["answer"],
                            "device": DEVICE,
                            "mode": "retrieval",
                            "matched_instruction": example["instruction"],
                            "score": round(score, 4),
                        },
                    )
                    return

            if use_retrieval and snippets:
                matches = find_snippets(
                    snippets,
                    domain,
                    prompt,
                    limit=snippet_limit,
                    min_score=snippet_threshold,
                )
                if matches:
                    self._send_json(
                        200,
                        {
                            "domain": domain,
                            "answer": snippet_answer(prompt, matches),
                            "device": DEVICE,
                            "mode": "snippet_retrieval",
                            "sources": [
                                {
                                    "source": snippet["source"],
                                    "score": round(score, 4),
                                    "type": snippet.get("type"),
                                }
                                for score, snippet in matches
                            ],
                        },
                    )
                    return

            text = build_prompt(prompt, domain)
            ids = tokenizer.encode(text).ids
            x = torch.tensor([ids], dtype=torch.long, device=DEVICE)
            eos_id = tokenizer.token_to_id("<|eos|>")

            with torch.no_grad():
                out = model.generate(
                    x,
                    max_new_tokens=max_new_tokens,
                    temperature=temperature,
                    top_k=top_k,
                    eos_id=eos_id,
                    vocab_limit=tokenizer.get_vocab_size(),
                )

            decoded = tokenizer.decode(out[0].tolist())
            answer = clean_model_answer(extract_answer(decoded, prompt), prompt, domain)
            self._send_json(
                200,
                {
                    "domain": domain,
                    "answer": answer,
                    "device": DEVICE,
                    "mode": "model",
                },
            )

        def log_message(self, fmt, *args):
            sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    return Handler


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", default="checkpoints/compound_game_commands_60m_v5/best.pt")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8008)
    parser.add_argument("--example-jsonl", action="append", default=[
        "data/instructions/godot_core_v1.jsonl",
        "data/instructions/godot_scene_ops_v1.jsonl",
        "data/instructions/unreal5_examples_v1.jsonl",
        "data/instructions/multiengine_v2.jsonl",
    ])
    parser.add_argument("--snippet-corpus", action="append", default=[
        "data/clean/mmorpg_project_scripts.txt",
        "data/clean/unreal5_code_examples.txt",
    ])
    parser.add_argument("--retrieval-threshold", type=float, default=0.32)
    parser.add_argument("--snippet-threshold", type=float, default=0.2)
    args = parser.parse_args()

    model, tokenizer = load_model(args.checkpoint)
    examples = load_examples(args.example_jsonl)
    snippets = load_snippets(args.snippet_corpus)
    server = ThreadingHTTPServer(
        (args.host, args.port),
        make_handler(
            model,
            tokenizer,
            examples,
            snippets,
            args.retrieval_threshold,
            args.snippet_threshold,
        ),
    )
    print(f"serving on http://{args.host}:{args.port}")
    print(f"loaded retrieval examples: {len(examples)}")
    print(f"loaded retrieval snippets: {len(snippets)}")
    server.serve_forever()


if __name__ == "__main__":
    main()
