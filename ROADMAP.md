# Yuspec GameDev AI Roadmap

## Goal

Build a practical game-development AI for Godot, Unity, and Unreal Engine that
can run cheaply on consumer hardware and power `yuspecai.com.tr`.

## Phase 1: Open Source Release

- Rename/public position: `yuspec-gamedev-ai`.
- Publish source code under MIT.
- Keep checkpoints and local corpora out of git.
- Add model cards, data-source notes, benchmark scripts, and reproducible
  training commands.

## Phase 2: Make the 10M Model Better

Focus on data quality instead of only increasing size:

- Distill GitHub issue answers from `qwen2.5_7b`.
- Add negative examples for wrong-engine answers.
- Add more real bug-fix tasks, not only short code snippets.
- Add general conversation and reasoning tasks in Turkish and English.
- Keep a hidden evaluation set so the model cannot just memorize the public
  benchmark.

## Phase 3: Scale Beyond 10M on RTX 4050 6GB

The RTX 4050 Laptop GPU with 6GB VRAM can train larger small models if we use:

- mixed precision training,
- gradient accumulation,
- small micro-batches,
- optional gradient checkpointing,
- careful sequence length control.

Candidate model sizes:

| Target | Example shape | Expected role |
|---|---|---|
| 10M | 8 layers, 256 dim, 4 heads | Very fast web/free tier. |
| 28M | 12 layers, 384 dim, 6 heads | Better syntax and short reasoning. |
| 59M | 16 layers, 512 dim, 8 heads | Stronger code patterns, still local. |
| 90M | 16 layers, 640 dim, 8 heads | Upper experimental range for 6GB training. |

The practical ceiling depends on sequence length and optimizer memory. Inference
is easy; training is the limiting part.

## Phase 4: Better Benchmarks

- Keep the simple engine benchmark for regression checks.
- Keep the GitHub issue benchmark for real-world behavior.
- Add patch-application tests where possible.
- Add compile/syntax checks:
  - GDScript parser checks where available,
  - Unity C# compilation where a project fixture exists,
  - Unreal C++ static checks for snippets.

## Phase 5: Product Architecture

Recommended public web setup:

- Free tier: small Yuspec model with retrieval.
- Strong local/dev tier: Qwen 0.5B LoRA.
- Heavy issue-solving tier: Qwen 7B or later distilled Yuspec model.

The long-term target is a stronger Yuspec model distilled from larger models
plus retrieval over trusted game-development sources.
