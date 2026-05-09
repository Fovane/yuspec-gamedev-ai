import argparse
import json
import random
from pathlib import Path


PREFIXES = [
    "",
    "Kisa ve temiz yaz: ",
    "Kod ornegiyle goster: ",
    "Yeni baslayan icin anlat: ",
    "Direkt calisacak kod ver: ",
]


HARD_EXAMPLES = [
    {
        "domain": "godot",
        "prompts": [
            "Godot'ta sahneye bir kup ekle ve kupu kirmizi yap.",
            "Godot 4 sahnesinde kirmizi cube olusturan GDScript yaz.",
            "Node3D icinde MeshInstance3D BoxMesh olustur ve rengi kirmizi olsun.",
            "Godot'ta kodla kirmizi BoxMesh kup ekle.",
            "MeshInstance3D kup yap, StandardMaterial3D ile kirmizi renge boya.",
        ],
        "answer": """Godot 4'te bunu `Node3D` uzerine takilan bir script ile yapabilirsin.

```gdscript
extends Node3D

func _ready() -> void:
    var cube := MeshInstance3D.new()
    cube.name = "RedCube"
    cube.mesh = BoxMesh.new()

    var material := StandardMaterial3D.new()
    material.albedo_color = Color.RED
    cube.material_override = material

    add_child(cube)
```

`MeshInstance3D` sahnedeki objedir, `BoxMesh` kup geometrisidir. Materyali child olarak ekleme; `cube.material_override` alanina ata.""",
    },
    {
        "domain": "godot",
        "prompts": [
            "Godot 4'te Area2D ile coin toplama sistemi nasil yapilir?",
            "Godot coin collect scripti yaz.",
            "Area2D coin body_entered sinyaliyle oyuncuya para eklesin.",
            "Godot'ta coin oyuncuya degince toplansin ve silinsin.",
            "GDScript ile Area2D coin pickup ornegi ver.",
        ],
        "answer": """Coin sahnesinin kok node'u `Area2D` olsun. Altina `CollisionShape2D` ve goruntu icin `Sprite2D` ekle. `body_entered` sinyalini scriptteki fonksiyona bagla.

```gdscript
extends Area2D

@export var value := 1

func _on_body_entered(body: Node) -> void:
    if body.has_method("add_coin"):
        body.add_coin(value)
    queue_free()
```

Oyuncu tarafinda:

```gdscript
var coins := 0

func add_coin(amount: int) -> void:
    coins += amount
```

Collision layer ve mask ayarlarinin oyuncuyu algiladigindan emin ol.""",
    },
    {
        "domain": "unreal",
        "prompts": [
            "Unreal C++ ile line trace kullanarak crosshair yonune ates etme ornegi yaz.",
            "UE5 C++ line trace silah atesi ornegi ver.",
            "Unreal'da UCameraComponent ile crosshair yonune LineTraceSingleByChannel kullan.",
            "FPS karakterinde kameradan ECC_Visibility line trace at.",
            "Unreal Engine C++ FHitResult ve DrawDebugLine ile atis kodu yaz.",
        ],
        "answer": """FPS karakterinde instant-hit ates icin kameradan ileri yone line trace atabilirsin.

```cpp
#include "Camera/CameraComponent.h"
#include "DrawDebugHelpers.h"

void AMyProjectCharacter::FireLineTrace()
{
    if (!FirstPersonCameraComponent)
    {
        return;
    }

    const FVector Start = FirstPersonCameraComponent->GetComponentLocation();
    const FVector End = Start + FirstPersonCameraComponent->GetForwardVector() * 20000.0f;

    FHitResult Hit;
    FCollisionQueryParams Params;
    Params.AddIgnoredActor(this);

    const bool bHit = GetWorld()->LineTraceSingleByChannel(
        Hit,
        Start,
        End,
        ECC_Visibility,
        Params
    );

    const FVector TraceEnd = bHit ? Hit.ImpactPoint : End;
    DrawDebugLine(GetWorld(), Start, TraceEnd, FColor::Green, false, 2.0f, 0, 1.5f);

    if (bHit && Hit.GetActor())
    {
        UE_LOG(LogTemp, Log, TEXT("Hit: %s"), *Hit.GetActor()->GetName());
    }
}
```

Header tarafinda kamera icin `UPROPERTY(VisibleAnywhere) UCameraComponent* FirstPersonCameraComponent;` tutmak yaygindir.""",
    },
    {
        "domain": "unreal",
        "prompts": [
            "UE5 C++ TriggerBox begin overlap ornegi ver.",
            "Unreal C++ ile TriggerBox overlap ornegi yaz.",
            "ATriggerBox OnActorBeginOverlap AddDynamic ornegi ver.",
            "Unreal Engine'de trigger box icine girince mesaj yazdir.",
            "UE C++ BeginOverlap fonksiyonu olan ATriggerBox sinifi yaz.",
        ],
        "answer": """`ATriggerBox` turetip constructor icinde `OnActorBeginOverlap` event'ine `UFUNCTION` olan bir fonksiyon baglayabilirsin.

```cpp
// MyTriggerBox.h
#pragma once

#include "CoreMinimal.h"
#include "Engine/TriggerBox.h"
#include "MyTriggerBox.generated.h"

UCLASS()
class AMyTriggerBox : public ATriggerBox
{
    GENERATED_BODY()

public:
    AMyTriggerBox();

protected:
    UFUNCTION()
    void BeginOverlap(AActor* OverlappedActor, AActor* OtherActor);
};
```

```cpp
// MyTriggerBox.cpp
#include "MyTriggerBox.h"
#include "Engine/Engine.h"

AMyTriggerBox::AMyTriggerBox()
{
    OnActorBeginOverlap.AddDynamic(this, &AMyTriggerBox::BeginOverlap);
}

void AMyTriggerBox::BeginOverlap(AActor* OverlappedActor, AActor* OtherActor)
{
    if (OtherActor && OtherActor != this && GEngine)
    {
        GEngine->AddOnScreenDebugMessage(-1, 5.0f, FColor::Green, TEXT("Begin Overlap"));
    }
}
```""",
    },
    {
        "domain": "unity",
        "prompts": [
            "Unity'de ScriptableObject ile item tanimi nasil yapilir?",
            "Unity C# item data icin ScriptableObject ornegi ver.",
            "CreateAssetMenu ile ItemDefinition yaz.",
        ],
        "answer": """Item verisini sahneden bagimsiz tutmak icin `ScriptableObject` kullan.

```csharp
using UnityEngine;

[CreateAssetMenu(menuName = "Game/Item")]
public class ItemDefinition : ScriptableObject
{
    public string id;
    public string displayName;
    public Sprite icon;
    public int maxStack = 1;
}
```

Runtime state'i bu asset uzerinde degil, inventory component icinde tutulmalidir.""",
    },
]


def read_jsonl(path):
    rows = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def add_hard_rows(rows, repeats):
    for _ in range(repeats):
        for item in HARD_EXAMPLES:
            for prompt in item["prompts"]:
                for prefix in PREFIXES:
                    rows.append(
                        {
                            "domain": item["domain"],
                            "instruction": f"{prefix}{prompt}",
                            "answer": item["answer"],
                        }
                    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", action="append", default=[
        "data/instructions/godot_core_v1.jsonl",
        "data/instructions/godot_scene_ops_v1.jsonl",
        "data/instructions/unreal5_examples_v1.jsonl",
        "data/instructions/multiengine_v2.jsonl",
    ])
    parser.add_argument("--out", default="data/instructions/multiengine_hard_v3.jsonl")
    parser.add_argument("--hard-repeats", type=int, default=18)
    parser.add_argument("--seed", type=int, default=20260509)
    args = parser.parse_args()

    rows = []
    for path in args.base:
        rows.extend(read_jsonl(Path(path)))

    add_hard_rows(rows, args.hard_repeats)
    random.seed(args.seed)
    random.shuffle(rows)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"wrote {len(rows)} rows to {out}")


if __name__ == "__main__":
    main()
