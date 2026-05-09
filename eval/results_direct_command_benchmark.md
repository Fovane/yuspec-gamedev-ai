# Direct Game Command Benchmark

| Candidate | Total | Average | Avg latency |
|---|---:|---:|---:|
| `yuspec_60m_compound_v5` | 116/120 | 96.67% | 2.12s |
| `qwen2.5_0.5b_lora` | 90/120 | 75.00% | 17.69s |
| `qwen2.5_0.5b` | 74/120 | 61.67% | 2.52s |
| `qwen2.5_7b` | 102/120 | 85.00% | 62.99s |

## Per Command

| Command | Domain | `yuspec_60m_compound_v5` | `qwen2.5_0.5b_lora` | `qwen2.5_0.5b` | `qwen2.5_7b` |
|---|---|---:|---:|---:|---:|
| `create a capsule character and give it wasd movement in godot` | godot | 10 | 5 | 5 | 5 |
| `oyuncuya can sistemi ekle` | godot | 9 | 5 | 5 | 7 |
| `sahneye kırmızı bir küp ekle` | godot | 9 | 4 | 5 | 8 |
| `make my player move with WASD` | godot | 10 | 8 | 6 | 7 |
| `create a capsule and its collider, give wasd movement logic to it for unity project.` | unity | 10 | 8 | 6 | 9 |
| `make camera follow the player smoothly` | unity | 10 | 8 | 7 | 9 |
| `add health system to the player` | unity | 8 | 10 | 9 | 10 |
| `add wasd movement logic to the player object` | unity | 10 | 10 | 8 | 10 |
| `add camera follow to player` | unreal | 10 | 9 | 5 | 8 |
| `add reusable health component to actor` | unreal | 10 | 10 | 6 | 10 |
| `add jump to the player` | unreal | 10 | 7 | 6 | 10 |
| `shoot projectile when player presses left mouse` | unreal | 10 | 6 | 6 | 9 |
