# Yuspec GameDev AI

Small game-development language model experiments for Godot, Unity, and Unreal
Engine. The current public release includes a 59.08M parameter direct-command
model for lightweight self-hosted fallback usage.

The code is MIT licensed. Public model checkpoints are stored with Git LFS and
documented in `MODEL_CARD.md` and `DATA_SOURCES.md`.

## What Is Included

- A compact decoder-only GPT-style model implementation.
- Training and generation scripts.
- Godot, Unity, and Unreal instruction-data builders.
- Retrieval-assisted local HTTP API.
- Benchmarks against Qwen models.
- GitHub issue benchmark tooling for permissive-license repositories.

## Current Best Local Checkpoints

Best 60M direct game-command model:

```text
checkpoints/compound_game_commands_60m_v5/best.pt
```

Best 60M GitHub issue model:

```text
checkpoints/github_issue_lora_teacher_60m_v6/best.pt
```

Best 10M local engine model:

```text
checkpoints/benchmark_realign_v4_round4/best.pt
```

Large checkpoints are tracked with Git LFS or published separately as release
artifacts. Keep private corpora and tokenized datasets out of git.

## Quick Start

Install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
```

For CUDA PyTorch on Windows:

```powershell
.\scripts\install_torch_cuda.ps1
```

Generate from a checkpoint:

```powershell
.\.venv\Scripts\python src\generate.py --checkpoint checkpoints\benchmark_realign_v4_round4\best.pt --domain godot --prompt "Godot'ta sahneye bir kup ekle ve kupu kirmizi yap." --answer-only
```

Run the local API:

```powershell
.\.venv\Scripts\python src\serve_model.py --host 127.0.0.1 --port 8009
```

Open `web_chat.html` in a browser and point it at `http://127.0.0.1:8009`.

## Training

Build multi-engine instruction data:

```powershell
.\.venv\Scripts\python src\build_multiengine_instruction.py --out data\instructions\multiengine_v2.jsonl
.\.venv\Scripts\python src\prepare_data.py --out-dir data\tokens_multiengine_v2 --no-include-clean --include-instructions --val-ratio 0.05
```

Train:

```powershell
.\.venv\Scripts\python src\train.py --config configs\multiengine_instruction_v2.yaml
```

Hard realign example:

```powershell
.\.venv\Scripts\python src\build_benchmark_realign_v4.py
.\.venv\Scripts\python src\prepare_data.py --out-dir data\tokens_benchmark_realign_v4 --no-include-clean --instruction-glob data\instructions\benchmark_realign_v4.jsonl --val-ratio 0.03
.\.venv\Scripts\python src\train.py --config configs\benchmark_realign_v4.yaml --init-from checkpoints\benchmark_realign_v4_round3\best.pt
```

Larger RTX 4050 experiments:

```powershell
# Approx. 28M parameters
.\.venv\Scripts\python src\train.py --config configs\yuspec_gamedev_28m.yaml

# Approx. 59M parameters
.\.venv\Scripts\python src\train.py --config configs\yuspec_gamedev_60m.yaml

# Approx. 90M parameters, experimental upper range for 6GB VRAM
.\.venv\Scripts\python src\train.py --config configs\yuspec_gamedev_90m.yaml
```

## Benchmarks

Direct command benchmark:

```powershell
.\.venv\Scripts\python eval\run_direct_command_benchmark.py
```

Latest direct command benchmark:

| Candidate | Score | Avg latency |
|---|---:|---:|
| `yuspec_60m_compound_v5` | 116/120 | 2.12s |
| `qwen2.5_7b` | 102/120 | 62.99s |
| `qwen2.5_0.5b_lora` | 90/120 | 17.69s |
| `qwen2.5_0.5b` | 74/120 | 2.52s |

Engine benchmark:

```powershell
.\.venv\Scripts\python eval\eval_checkpoint_engine.py --checkpoint checkpoints\benchmark_realign_v4_round4\best.pt --name yuspec_10m_round4
```

GitHub issue benchmark collection:

```powershell
.\.venv\Scripts\python scripts\collect_github_issue_benchmark.py --repos-per-domain 4 --issues-per-repo 2
```

Run GitHub issue benchmark:

```powershell
.\.venv\Scripts\python eval\run_github_issue_benchmark.py --max-new-tokens 520
```

The current 60M checkpoint is paired with a domain-aware issue-answer
postprocessor in `src/serve_model.py` and `eval/run_github_issue_benchmark.py`.
That runtime layer removes cross-engine API leakage and appends a compact
engine-specific patch/test scaffold for GitHub issue prompts.

Direct command training:

```powershell
.\.venv\Scripts\python scripts\build_direct_game_command_sft.py --out data\instructions\direct_game_commands_v1.jsonl
.\.venv\Scripts\python src\prepare_data.py --out-dir data\tokens_direct_game_commands_v1 --no-include-clean --instruction-glob data\instructions\direct_game_commands_v1.jsonl --instruction-glob data\instructions\multiengine_v2.jsonl --instruction-glob data\instructions\unreal5_examples_v1.jsonl
.\.venv\Scripts\python src\train.py --config configs\direct_game_commands_60m.yaml --init-from checkpoints\github_issue_distill_60m_v1_fast\best.pt
```

## Documentation

- `MODEL_CARD.md`: model behavior, limits, and benchmark summary.
- `DATA_SOURCES.md`: data-source and license notes.
- `ROADMAP.md`: scale-up plan for RTX 4050 6GB and product direction.

## License

Code in this repository is released under the MIT License. See `LICENSE`.
