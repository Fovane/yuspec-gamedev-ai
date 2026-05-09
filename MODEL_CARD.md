# Yuspec GameDev AI Model Card

## Overview

Yuspec GameDev AI is a small decoder-only Transformer project for game
development assistance across Godot, Unity, and Unreal Engine.

The repository code is MIT licensed. Public checkpoints are distributed through
Git LFS in this repository. Training corpora and derived datasets are documented
in `DATA_SOURCES.md`; raw third-party corpora are not included.

## Current Local Models

| Model | Type | Notes |
|---|---|---|
| `yuspec_10m_round4` | 10.66M parameter local model | Best small-model checkpoint for the local benchmark. |
| `yuspec_60m_replay_cjk_v5_clean` | 59.08M parameter local model | Best GitHub issue benchmark checkpoint. |
| `yuspec_60m_lora_teacher_v6_shaped` | 59.08M parameter local model + runtime shaping | Current best local GitHub issue assistant mode. |
| `yuspec_60m_direct_commands_v2` | 59.08M parameter local model | Current best pure-model fallback for direct game-development commands. |
| `yuspec_60m_compound_commands_v5` | 59.08M parameter local model | Current best pure-model fallback for multi-step object/collider/movement commands. |
| `qwen2.5_0.5b_lora` | PEFT LoRA adapter | Fine-tuned from `Qwen/Qwen2.5-0.5B-Instruct`. |
| `qwen2.5_7b` | External baseline | Ollama baseline used for issue-solving comparisons. |

## Benchmark Summary

Local engine benchmark:

| Candidate | Score |
|---|---:|
| `yuspec_10m_round4` | 100/100 |
| `qwen2.5_0.5b_lora` | 99/100 |
| `qwen2.5:0.5b` | 52/100 |

Direct game-command benchmark:

| Candidate | Score | Average | Avg latency |
|---|---:|---:|---:|
| `yuspec_60m_compound_v5` | 116/120 | 96.67% | 2.12s |
| `qwen2.5_7b` | 102/120 | 85.00% | 62.99s |
| `qwen2.5_0.5b_lora` | 90/120 | 75.00% | 17.69s |
| `qwen2.5_0.5b` | 74/120 | 61.67% | 2.52s |

GitHub issue benchmark:

| Candidate | Score |
|---|---:|
| `yuspec_60m_replay_cjk_v5_clean` | 200/200 |
| `qwen2.5_7b` | 172/200 |
| `qwen2.5_0.5b_lora` | 158/200 |

Hidden GitHub issue benchmark, local holdout:

| Candidate | Score |
|---|---:|
| `yuspec_60m_lora_teacher_v6_shaped` | 160/160 |
| `qwen2.5_0.5b_lora` | 138/160 |
| `qwen2.5_7b` | 136/160 |

Direct command spot checks, pure model output:

| Prompt | Domain | Result |
|---|---|---|
| `add wasd movement logic to the player object` | Unity | Produced valid `MonoBehaviour` WASD movement code. |
| `sahneye kırmızı bir küp ekle` | Godot | Produced valid `MeshInstance3D` + `BoxMesh` + red material code. |
| `create a capsule and its collider, give wasd movement logic to it for unity project.` | Unity | Produced a compile-ready capsule spawner plus `CharacterController` movement code. |
| `add camera follow to player` | Unreal | Produced valid spring-arm camera setup snippet. |

Interpretation: `yuspec_60m_compound_v5` is the recommended pure-model release
for short direct game-development commands. The issue-solving benchmark uses a
separate issue-specialized stack with answer shaping. Keep validating against
fresh hidden issue sets before making broad generalization claims.

## Intended Use

- Game-development code snippets for Godot, Unity, and Unreal Engine.
- Local experimentation with small language models.
- Retrieval-augmented assistant prototypes for `yuspecai.com.tr`.
- Distillation experiments from larger models into smaller local models.

## Limitations

- The 10M model has limited reasoning capacity and context handling.
- The 60M direct-command model is much better for short Godot/Unity/Unreal
  coding commands than the issue-specialized checkpoint.
- The 60M direct-command model is still fragile on exact Unreal C++ function
  signatures and should be validated before applying generated patches.
- It can overfit narrow benchmark examples.
- It should not be trusted as the only reviewer for production patches.
- Legal and license compatibility must be checked before redistributing any
  dataset or model weights.

## Recommended Public Release Shape

- GitHub repository: code, configs, benchmark scripts, docs.
- GitHub Releases or Hugging Face: optional model weights.
- Keep private project scripts, raw downloaded repositories, generated token
  files, and local checkpoints out of git.
