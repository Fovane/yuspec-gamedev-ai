# Yuspec GameDev AI

Small game-development language model experiments for Godot, Unity, and Unreal
Engine.

The code is MIT licensed. Model weights and datasets should be released
separately with their own model card and data-source notes.

## What Is Included

- A compact decoder-only GPT-style model implementation.
- Training and generation scripts.
- Godot, Unity, and Unreal instruction-data builders.
- Retrieval-assisted local HTTP API.
- Benchmarks against Qwen models.
- GitHub issue benchmark tooling for permissive-license repositories.

## Current Best Local Checkpoints

Best 60M GitHub issue model:

```text
checkpoints/github_issue_replay_cjk_60m_v5/best.pt
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
.\.venv\Scripts\python src\serve_model.py --host 127.0.0.1 --port 8008
```

Open `web_chat.html` in a browser and point it at `http://127.0.0.1:8008`.

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

## Documentation

- `MODEL_CARD.md`: model behavior, limits, and benchmark summary.
- `DATA_SOURCES.md`: data-source and license notes.
- `ROADMAP.md`: scale-up plan for RTX 4050 6GB and product direction.

## License

Code in this repository is released under the MIT License. See `LICENSE`.
