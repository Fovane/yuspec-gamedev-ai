import argparse
import json
import random
from pathlib import Path


ROWS = [
    {
        "domain": "godot",
        "prompts": [
            "sahneye kırmızı bir küp ekle",
            "sahneye kirmizi kup ekle",
            "Godot'ta sahneye kırmızı küp ekle",
            "create a red cube in godot",
            "add a cube and make it red in Godot 4",
        ],
        "answer": """Create a `MeshInstance3D`, assign a `BoxMesh`, and give it a red `StandardMaterial3D`.

```gdscript
extends Node3D

func _ready() -> void:
    var cube := MeshInstance3D.new()
    cube.name = "RedCube"
    cube.mesh = BoxMesh.new()

    var mat := StandardMaterial3D.new()
    mat.albedo_color = Color.RED
    cube.material_override = mat

    cube.position = Vector3(0, 1, 0)
    add_child(cube)
```

Attach this script to any `Node3D` in the scene. When the scene starts, it creates the red cube as a child.""",
    },
    {
        "domain": "unreal",
        "prompts": [
            "add camera follow to player",
            "make camera follow the player smoothly",
            "third person follow camera code",
            "Unreal Engine 5 C++ add camera follow to player",
            "kamerayi oyuncuyu takip edecek sekilde ayarla unreal",
        ],
        "answer": """For a third-person Unreal character, use a `USpringArmComponent` and a `UCameraComponent`. The spring arm follows the player and smooths camera placement.

```cpp
// MyPlayerCharacter.h
UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Camera")
USpringArmComponent* CameraBoom;

UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Camera")
UCameraComponent* FollowCamera;
```

```cpp
// MyPlayerCharacter.cpp
AMyPlayerCharacter::AMyPlayerCharacter()
{
    CameraBoom = CreateDefaultSubobject<USpringArmComponent>(TEXT("CameraBoom"));
    CameraBoom->SetupAttachment(RootComponent);
    CameraBoom->TargetArmLength = 350.0f;
    CameraBoom->bUsePawnControlRotation = true;

    FollowCamera = CreateDefaultSubobject<UCameraComponent>(TEXT("FollowCamera"));
    FollowCamera->SetupAttachment(CameraBoom, USpringArmComponent::SocketName);
    FollowCamera->bUsePawnControlRotation = false;
}
```

Include `GameFramework/SpringArmComponent.h` and `Camera/CameraComponent.h`. Then rotate the controller from mouse input and let the spring arm follow the character.""",
    },
    {
        "domain": "unity",
        "prompts": [
            "add wasd movement logic to the player object",
            "make my player move with WASD",
            "Unity C# add wasd movement to player",
            "player objesine wasd hareket sistemi ekle",
        ],
        "answer": """Attach this script to the Player GameObject. It reads WASD/arrow input and moves the object every frame.

```csharp
using UnityEngine;

public class PlayerMovement : MonoBehaviour
{
    [SerializeField] private float moveSpeed = 5f;

    private void Update()
    {
        float x = Input.GetAxisRaw("Horizontal");
        float z = Input.GetAxisRaw("Vertical");
        Vector3 direction = new Vector3(x, 0f, z).normalized;

        transform.position += direction * moveSpeed * Time.deltaTime;
    }
}
```

If the player uses physics, move the same direction in `FixedUpdate` with `Rigidbody.MovePosition` instead of changing `transform.position`.""",
    },
    {
        "domain": "unreal",
        "prompts": [
            "shoot projectile when player presses left mouse",
            "spawn projectile from player unreal",
            "Unreal Engine 5 C++ fire projectile from muzzle",
        ],
        "answer": """Spawn the projectile actor from a muzzle component and bind the fire function to input.

```cpp
void AMyPlayerCharacter::Fire()
{
    if (!ProjectileClass || !Muzzle)
        return;

    const FVector SpawnLocation = Muzzle->GetComponentLocation();
    const FRotator SpawnRotation = Muzzle->GetComponentRotation();

    GetWorld()->SpawnActor<AActor>(
        ProjectileClass,
        SpawnLocation,
        SpawnRotation
    );
}
```

Expose `ProjectileClass` as `TSubclassOf<AActor>` and give the projectile its own movement component.""",
    },
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="data/instructions/direct_game_commands_hardfix_v2.jsonl")
    parser.add_argument("--repeat", type=int, default=520)
    parser.add_argument("--seed", type=int, default=6062)
    args = parser.parse_args()

    rows = []
    for item in ROWS:
        for _ in range(args.repeat):
            for prompt in item["prompts"]:
                rows.append(
                    {
                        "domain": item["domain"],
                        "instruction": prompt,
                        "answer": item["answer"],
                        "source": "synthetic_direct_command_hardfix",
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
