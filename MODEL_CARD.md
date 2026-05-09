# Yuspec GameDev AI Model Card

## Overview

Yuspec GameDev AI is a small decoder-only Transformer project for game
development assistance across Godot, Unity, and Unreal Engine.

The repository code is MIT licensed. Model weights and training corpora should
be published as separate release artifacts with their own source and license
notes.

## Current Local Models

| Model | Type | Notes |
|---|---|---|
| `yuspec_10m_round4` | 10.66M parameter local model | Best small-model checkpoint for the local benchmark. |
| `yuspec_60m_replay_cjk_v5_clean` | 59.08M parameter local model | Best GitHub issue benchmark checkpoint. |
| `qwen2.5_0.5b_lora` | PEFT LoRA adapter | Fine-tuned from `Qwen/Qwen2.5-0.5B-Instruct`. |
| `qwen2.5_7b` | External baseline | Ollama baseline used for issue-solving comparisons. |

## Benchmark Summary

Local engine benchmark:

| Candidate | Score |
|---|---:|
| `yuspec_10m_round4` | 100/100 |
| `qwen2.5_0.5b_lora` | 99/100 |
| `qwen2.5:0.5b` | 52/100 |

GitHub issue benchmark:

| Candidate | Score |
|---|---:|
| `yuspec_60m_replay_cjk_v5_clean` | 200/200 |
| `qwen2.5_7b` | 172/200 |
| `qwen2.5_0.5b_lora` | 158/200 |

Interpretation: the 60M model is currently the strongest Yuspec native model on
the public GitHub issue benchmark. This score is benchmark-specific and should
be validated against hidden issue sets before making broad generalization
claims.

## Intended Use

- Game-development code snippets for Godot, Unity, and Unreal Engine.
- Local experimentation with small language models.
- Retrieval-augmented assistant prototypes for `yuspecai.com.tr`.
- Distillation experiments from larger models into smaller local models.

## Limitations

- The 10M model has limited reasoning capacity and context handling.
- It can overfit narrow benchmark examples.
- It should not be trusted as the only reviewer for production patches.
- Legal and license compatibility must be checked before redistributing any
  dataset or model weights.

## Recommended Public Release Shape

- GitHub repository: code, configs, benchmark scripts, docs.
- GitHub Releases or Hugging Face: optional model weights.
- Keep private project scripts, raw downloaded repositories, generated token
  files, and local checkpoints out of git.
