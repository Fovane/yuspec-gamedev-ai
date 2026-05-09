# Release Notes

## v0.3.0 - Yuspec GameDev AI 60M Compound Commands

This release packages Yuspec GameDev AI as a lightweight, self-hostable
game-development coding assistant for Godot, Unity, and Unreal Engine.

### Recommended Checkpoint

```text
checkpoints/compound_game_commands_60m_v5/best.pt
```

This is the recommended pure-model fallback checkpoint for short direct
game-development commands, especially multi-step Unity/Godot commands such as:

- create object + collider + movement logic
- red cube / capsule player setup
- WASD player movement
- health component snippets
- camera follow snippets

### Benchmark

Direct game-command benchmark:

| Candidate | Score | Average | Avg latency |
|---|---:|---:|---:|
| `yuspec_60m_compound_v5` | 116/120 | 96.67% | 2.12s |
| `qwen2.5_7b` | 102/120 | 85.00% | 62.99s |
| `qwen2.5_0.5b_lora` | 90/120 | 75.00% | 17.69s |
| `qwen2.5_0.5b` | 74/120 | 61.67% | 2.52s |

Benchmark files:

```text
eval/direct_command_benchmark.jsonl
eval/run_direct_command_benchmark.py
eval/results_direct_command_benchmark.md
```

### Local API

```powershell
.\.venv\Scripts\python src\serve_model.py --host 127.0.0.1 --port 8009
```

Then open:

```text
web_chat.html
```

and use:

```text
http://127.0.0.1:8009
```

### Known Limits

- This is a small 59.08M parameter model, not a general-purpose frontier model.
- It is strongest on direct Godot/Unity/Unreal coding commands seen in the
  benchmark style.
- It can still make syntax or API mistakes, especially on complex Unreal C++.
- Generated code should be compiled, tested, and reviewed before production use.
