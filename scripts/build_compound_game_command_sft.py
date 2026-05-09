import argparse
import json
import random
from pathlib import Path


UNITY_CAPSULE = """Create the capsule player object and attach movement logic to it. A Unity capsule primitive already has a `CapsuleCollider`, so the clean option is to add a `CharacterController` and move through it.

```csharp
using UnityEngine;

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
            Object.Destroy(capsuleCollider);

        CharacterController controller = player.AddComponent<CharacterController>();
        controller.height = 2f;
        controller.radius = 0.5f;
        controller.center = new Vector3(0f, 1f, 0f);

        player.AddComponent<CapsulePlayerMovement>();
    }
}
```

Attach `CapsulePlayerSpawner` to an empty GameObject in the scene. Press Play and the script creates a capsule player with collider-based WASD movement."""


UNITY_RIGIDBODY_CAPSULE = """Create a capsule with a `CapsuleCollider`, add a `Rigidbody`, and move it with WASD in `FixedUpdate`.

```csharp
using UnityEngine;

[RequireComponent(typeof(Rigidbody))]
[RequireComponent(typeof(CapsuleCollider))]
public class RigidbodyCapsuleMovement : MonoBehaviour
{
    [SerializeField] private float moveSpeed = 5f;

    private Rigidbody rb;
    private Vector3 input;

    private void Awake()
    {
        rb = GetComponent<Rigidbody>();
        rb.freezeRotation = true;
    }

    private void Update()
    {
        float x = Input.GetAxisRaw("Horizontal");
        float z = Input.GetAxisRaw("Vertical");
        input = new Vector3(x, 0f, z).normalized;
    }

    private void FixedUpdate()
    {
        Vector3 nextPosition = rb.position + input * moveSpeed * Time.fixedDeltaTime;
        rb.MovePosition(nextPosition);
    }
}
```

```csharp
using UnityEngine;

public class RigidbodyCapsuleSpawner : MonoBehaviour
{
    private void Start()
    {
        GameObject player = GameObject.CreatePrimitive(PrimitiveType.Capsule);
        player.name = "RigidbodyCapsulePlayer";
        player.transform.position = new Vector3(0f, 1f, 0f);

        Rigidbody rb = player.AddComponent<Rigidbody>();
        rb.freezeRotation = true;

        player.AddComponent<RigidbodyCapsuleMovement>();
    }
}
```"""


GODOT_CAPSULE = """Create a `CharacterBody3D` with a capsule mesh, capsule collision shape, and WASD movement.

```gdscript
extends Node3D

func _ready() -> void:
    var player := CharacterBody3D.new()
    player.name = "CapsulePlayer"

    var mesh := MeshInstance3D.new()
    mesh.mesh = CapsuleMesh.new()
    player.add_child(mesh)

    var collision := CollisionShape3D.new()
    collision.shape = CapsuleShape3D.new()
    player.add_child(collision)

    player.set_script(preload("res://CapsulePlayerMovement.gd"))
    add_child(player)
```

```gdscript
# CapsulePlayerMovement.gd
extends CharacterBody3D

@export var move_speed := 5.0

func _physics_process(_delta: float) -> void:
    var input_dir := Input.get_vector("move_left", "move_right", "move_forward", "move_back")
    var direction := Vector3(input_dir.x, 0.0, input_dir.y).normalized()
    velocity.x = direction.x * move_speed
    velocity.z = direction.z * move_speed
    move_and_slide()
```

Add input actions for `move_left`, `move_right`, `move_forward`, and `move_back`, then bind them to A, D, W, and S."""


UNITY_CAMERA_CAPSULE = """Create a capsule player, add collider-based WASD movement, and make the camera follow it.

```csharp
using UnityEngine;

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
        Vector3 direction = new Vector3(Input.GetAxisRaw("Horizontal"), 0f, Input.GetAxisRaw("Vertical")).normalized;
        controller.Move(direction * moveSpeed * Time.deltaTime);
    }
}
```

```csharp
using UnityEngine;

public class FollowCamera : MonoBehaviour
{
    [SerializeField] private Transform target;
    [SerializeField] private Vector3 offset = new Vector3(0f, 4f, -6f);
    [SerializeField] private float smoothTime = 0.15f;
    private Vector3 velocity;

    public void SetTarget(Transform newTarget)
    {
        target = newTarget;
    }

    private void LateUpdate()
    {
        if (target == null)
            return;

        transform.position = Vector3.SmoothDamp(transform.position, target.position + offset, ref velocity, smoothTime);
        transform.LookAt(target);
    }
}
```

```csharp
using UnityEngine;

public class CapsulePlayerSceneSetup : MonoBehaviour
{
    private void Start()
    {
        GameObject player = GameObject.CreatePrimitive(PrimitiveType.Capsule);
        player.name = "PlayerCapsule";
        player.transform.position = new Vector3(0f, 1f, 0f);

        Object.Destroy(player.GetComponent<CapsuleCollider>());
        player.AddComponent<CharacterController>();
        player.AddComponent<CapsulePlayerMovement>();

        Camera mainCamera = Camera.main;
        if (mainCamera != null)
        {
            FollowCamera follow = mainCamera.gameObject.AddComponent<FollowCamera>();
            follow.SetTarget(player.transform);
        }
    }
}
```"""


COMMANDS = [
    {
        "domain": "unity",
        "answer": UNITY_CAPSULE,
        "prompts": [
            "create a capsule and its collider, give wasd movement logic to it for unity project",
            "create a capsule player with collider and WASD movement in Unity",
            "Unity project: create capsule, add collider, add wasd movement",
            "make a capsule object with collider and keyboard movement",
            "capsule player objesi olustur collider ekle wasd hareket ver unity",
            "generate a capsule character controller with WASD controls",
        ],
    },
    {
        "domain": "unity",
        "answer": UNITY_RIGIDBODY_CAPSULE,
        "prompts": [
            "create a physics capsule with rigidbody collider and wasd movement",
            "Unity rigidbody capsule movement with WASD",
            "make a capsule player using rigidbody MovePosition",
            "capsule collider rigidbody ile wasd hareket sistemi yaz",
        ],
    },
    {
        "domain": "godot",
        "answer": GODOT_CAPSULE,
        "prompts": [
            "create a capsule character and give it wasd movement in godot",
            "Godot 4 create capsule with collision and WASD movement",
            "capsule player collision shape and movement gdscript",
            "godot kapsul karakter olustur collider ekle wasd hareket ver",
        ],
    },
    {
        "domain": "unity",
        "answer": UNITY_CAMERA_CAPSULE,
        "prompts": [
            "create a capsule player with collider wasd movement and camera follow",
            "Unity capsule controller plus follow camera",
            "make capsule player move with WASD and make camera follow it",
            "capsule player olustur wasd hareket ve kamera takip ekle",
        ],
    },
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="data/instructions/compound_game_commands_v4.jsonl")
    parser.add_argument("--repeat", type=int, default=900)
    parser.add_argument("--seed", type=int, default=9904)
    args = parser.parse_args()

    rows = []
    for item in COMMANDS:
        for _ in range(args.repeat):
            for prompt in item["prompts"]:
                rows.append(
                    {
                        "domain": item["domain"],
                        "instruction": prompt,
                        "answer": item["answer"],
                        "source": "synthetic_compound_game_command",
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
