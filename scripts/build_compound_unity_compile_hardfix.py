import argparse
import json
import random
from pathlib import Path


ANSWER = """Use one C# file with two classes: one class creates the capsule, and one class moves it with a `CharacterController`.

```csharp
using UnityEngine;

public class CapsulePlayerSpawner : MonoBehaviour
{
    private void Start()
    {
        GameObject player = GameObject.CreatePrimitive(PrimitiveType.Capsule);
        player.name = "PlayerCapsule";
        player.transform.position = new Vector3(0f, 1f, 0f);

        CapsuleCollider capsuleCollider = player.GetComponent<CapsuleCollider>();
        if (capsuleCollider != null)
        {
            Object.Destroy(capsuleCollider);
        }

        CharacterController controller = player.AddComponent<CharacterController>();
        controller.height = 2f;
        controller.radius = 0.5f;
        controller.center = new Vector3(0f, 1f, 0f);

        player.AddComponent<CapsulePlayerMovement>();
    }
}

[RequireComponent(typeof(CharacterController))]
public class CapsulePlayerMovement : MonoBehaviour
{
    [SerializeField] private float moveSpeed = 5f;

    private CharacterController controller;

    private void Awake()
    {
        controller = GetComponent<CharacterController>();
    }

    private void Update()
    {
        float x = Input.GetAxisRaw("Horizontal");
        float z = Input.GetAxisRaw("Vertical");
        Vector3 direction = new Vector3(x, 0f, z).normalized;

        controller.Move(direction * moveSpeed * Time.deltaTime);
    }
}
```

Attach `CapsulePlayerSpawner` to an empty GameObject and press Play. The script creates a capsule player, replaces the primitive collider with a `CharacterController`, and adds WASD movement."""


PROMPTS = [
    "create a capsule and its collider, give wasd movement logic to it for unity project.",
    "create a capsule and its collider, give wasd movement logic to it for unity project",
    "create a capsule player with collider and WASD movement in Unity",
    "Unity project: create capsule, add collider, add wasd movement",
    "make a capsule object with collider and keyboard movement",
    "generate a capsule character controller with WASD controls",
    "capsule player objesi olustur collider ekle wasd hareket ver unity",
    "create capsule player and move it with WASD using CharacterController",
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="data/instructions/compound_unity_compile_hardfix_v5.jsonl")
    parser.add_argument("--repeat", type=int, default=1800)
    parser.add_argument("--seed", type=int, default=9905)
    args = parser.parse_args()

    rows = []
    for _ in range(args.repeat):
        for prompt in PROMPTS:
            rows.append(
                {
                    "domain": "unity",
                    "instruction": prompt,
                    "answer": ANSWER,
                    "source": "synthetic_compound_unity_compile_hardfix",
                }
            )

    random.seed(args.seed)
    random.shuffle(rows)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"wrote {len(rows)} rows -> {out}")


if __name__ == "__main__":
    main()
