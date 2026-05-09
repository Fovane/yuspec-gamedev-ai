import argparse
import json
import random
from pathlib import Path


UNITY_EXAMPLES = [
    {
        "instruction": "Unity'de WASD ile CharacterController kullanan FPS hareket kodu yaz.",
        "answer": """Bu script Player objesine eklenir. Objede `CharacterController` component'i olmalı.

```csharp
using UnityEngine;

[RequireComponent(typeof(CharacterController))]
public class PlayerMovement : MonoBehaviour
{
    [SerializeField] private float speed = 5f;
    [SerializeField] private float gravity = -9.81f;

    private CharacterController controller;
    private Vector3 velocity;

    private void Awake()
    {
        controller = GetComponent<CharacterController>();
    }

    private void Update()
    {
        float x = Input.GetAxisRaw("Horizontal");
        float z = Input.GetAxisRaw("Vertical");

        Vector3 move = transform.right * x + transform.forward * z;
        controller.Move(move.normalized * speed * Time.deltaTime);

        if (controller.isGrounded && velocity.y < 0f)
            velocity.y = -2f;

        velocity.y += gravity * Time.deltaTime;
        controller.Move(velocity * Time.deltaTime);
    }
}
```

Yeni Input System kullanıyorsan `Input.GetAxisRaw` yerine input action callback'leriyle vektör okuyabilirsin.""",
    },
    {
        "instruction": "Unity 2D'de Rigidbody2D ile oyuncu hareketi yaz.",
        "answer": """Bu örnek top-down 2D hareket içindir. Player objesinde `Rigidbody2D` olmalı ve gravity scale genelde 0 yapılır.

```csharp
using UnityEngine;

[RequireComponent(typeof(Rigidbody2D))]
public class PlayerMovement2D : MonoBehaviour
{
    [SerializeField] private float speed = 6f;

    private Rigidbody2D rb;
    private Vector2 input;

    private void Awake()
    {
        rb = GetComponent<Rigidbody2D>();
    }

    private void Update()
    {
        input.x = Input.GetAxisRaw("Horizontal");
        input.y = Input.GetAxisRaw("Vertical");
        input = input.normalized;
    }

    private void FixedUpdate()
    {
        rb.linearVelocity = input * speed;
    }
}
```

Eski Unity sürümlerinde `linearVelocity` yerine `velocity` kullanılır.""",
    },
    {
        "instruction": "Unity'de coin toplama sistemi C# ile nasıl yapılır?",
        "answer": """Coin objesinde trigger collider olmalı. Player objesini tag veya component ile ayırt edebilirsin.

```csharp
using UnityEngine;

public class Coin : MonoBehaviour
{
    [SerializeField] private int value = 1;

    private void OnTriggerEnter(Collider other)
    {
        if (!other.TryGetComponent<PlayerWallet>(out var wallet))
            return;

        wallet.AddCoins(value);
        Destroy(gameObject);
    }
}

public class PlayerWallet : MonoBehaviour
{
    public int Coins { get; private set; }

    public void AddCoins(int amount)
    {
        Coins += amount;
    }
}
```""",
    },
    {
        "instruction": "Unity'de Health component yaz.",
        "answer": """Health'i ayrı component yapmak Player, enemy ve kırılabilir objelerde yeniden kullanımı kolaylaştırır.

```csharp
using System;
using UnityEngine;

public class Health : MonoBehaviour
{
    [SerializeField] private int maxHealth = 100;

    public int Current { get; private set; }
    public event Action<int, int> Changed;
    public event Action Died;

    private void Awake()
    {
        Current = maxHealth;
    }

    public void TakeDamage(int amount)
    {
        Current = Mathf.Max(Current - amount, 0);
        Changed?.Invoke(Current, maxHealth);

        if (Current == 0)
            Died?.Invoke();
    }
}
```""",
    },
    {
        "instruction": "Unity'de ScriptableObject ile item tanımı nasıl yapılır?",
        "answer": """ScriptableObject, item verisini prefab veya sahne bağımlılığı olmadan saklamak için uygundur.

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

Project penceresinde sağ tıklayıp `Create > Game > Item` ile asset oluşturabilirsin. Runtime state'i ScriptableObject üzerinde değil, inventory component içinde tutulmalıdır.""",
    },
    {
        "instruction": "Unity'de null reference exception nasıl debug edilir?",
        "answer": """`NullReferenceException`, null olan bir değişkenin alanına veya metoduna eriştiğini gösterir. Inspector referansı atanmış mı, `GetComponent` sonucu null mı ve obje sahnede aktif mi kontrol et.

```csharp
[SerializeField] private Transform target;

private void Awake()
{
    if (target == null)
    {
        Debug.LogError("Target referansı Inspector'dan atanmadı.", this);
        enabled = false;
        return;
    }
}
```

Hata satırına çift tıkla, o satırdaki her referansı tek tek kontrol et.""",
    },
]


UNREAL_EXAMPLES = [
    {
        "instruction": "Unreal Engine C++ ile basit Character hareket sınıfı yaz.",
        "answer": """Enhanced Input kurulu projelerde input binding genelde Character içinde yapılır. Aşağıdaki iskelet hareket fonksiyonlarını gösterir.

```cpp
// MyPlayerCharacter.h
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "MyPlayerCharacter.generated.h"

UCLASS()
class AMyPlayerCharacter : public ACharacter
{
    GENERATED_BODY()

public:
    AMyPlayerCharacter();

protected:
    virtual void SetupPlayerInputComponent(UInputComponent* PlayerInputComponent) override;

    void MoveForward(float Value);
    void MoveRight(float Value);
};
```

```cpp
// MyPlayerCharacter.cpp
#include "MyPlayerCharacter.h"

AMyPlayerCharacter::AMyPlayerCharacter()
{
    PrimaryActorTick.bCanEverTick = true;
}

void AMyPlayerCharacter::SetupPlayerInputComponent(UInputComponent* PlayerInputComponent)
{
    Super::SetupPlayerInputComponent(PlayerInputComponent);
    PlayerInputComponent->BindAxis("MoveForward", this, &AMyPlayerCharacter::MoveForward);
    PlayerInputComponent->BindAxis("MoveRight", this, &AMyPlayerCharacter::MoveRight);
}

void AMyPlayerCharacter::MoveForward(float Value)
{
    AddMovementInput(GetActorForwardVector(), Value);
}

void AMyPlayerCharacter::MoveRight(float Value)
{
    AddMovementInput(GetActorRightVector(), Value);
}
```""",
    },
    {
        "instruction": "Unreal C++ ile Actor içinde rotating pickup yaz.",
        "answer": """Pickup için `AActor` türetip mesh'i root'a bağlayabilir ve Tick içinde döndürebilirsin.

```cpp
UCLASS()
class ARotatingPickup : public AActor
{
    GENERATED_BODY()

public:
    ARotatingPickup();
    virtual void Tick(float DeltaSeconds) override;

protected:
    UPROPERTY(VisibleAnywhere)
    UStaticMeshComponent* Mesh;

    UPROPERTY(EditAnywhere, Category="Pickup")
    float RotationSpeed = 90.0f;
};
```

```cpp
ARotatingPickup::ARotatingPickup()
{
    PrimaryActorTick.bCanEverTick = true;
    Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));
    RootComponent = Mesh;
}

void ARotatingPickup::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    AddActorLocalRotation(FRotator(0.0f, RotationSpeed * DeltaSeconds, 0.0f));
}
```""",
    },
    {
        "instruction": "Unreal Engine'de UPROPERTY ve UFUNCTION ne işe yarar?",
        "answer": """`UPROPERTY`, değişkeni Unreal reflection sistemine tanıtır. Böylece garbage collector, Blueprint, editor ve serialization sistemi değişkeni görebilir.

`UFUNCTION`, C++ fonksiyonunu reflection sistemine açar. Blueprint'ten çağırmak veya event olarak kullanmak için gerekir.

```cpp
UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Stats")
float MaxHealth = 100.0f;

UFUNCTION(BlueprintCallable, Category="Stats")
void TakeDamageAmount(float Amount);
```

Unreal'da UObject referanslarını çoğu zaman `UPROPERTY` ile tutmak önemlidir; aksi halde GC davranışı sorun çıkarabilir.""",
    },
    {
        "instruction": "Unreal C++ ile Health component yaz.",
        "answer": """Reusable health için `UActorComponent` uygundur.

```cpp
UCLASS(ClassGroup=(Custom), meta=(BlueprintSpawnableComponent))
class UHealthComponent : public UActorComponent
{
    GENERATED_BODY()

public:
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Health")
    float MaxHealth = 100.0f;

    UPROPERTY(BlueprintReadOnly, Category="Health")
    float CurrentHealth = 100.0f;

    UFUNCTION(BlueprintCallable, Category="Health")
    void ApplyDamage(float Amount)
    {
        CurrentHealth = FMath::Clamp(CurrentHealth - Amount, 0.0f, MaxHealth);
        if (CurrentHealth <= 0.0f)
        {
            // Death event veya BlueprintImplementableEvent çağrılabilir.
        }
    }
};
```

Daha gelişmiş sürümde multicast delegate ile UI ve gameplay sistemlerine haber verilir.""",
    },
    {
        "instruction": "Unreal Blueprint ile kapı açma mantığını anlat.",
        "answer": """Kapı actor'ünde `Box Collision`, kapı mesh'i ve timeline bulunur. Player overlap olduğunda timeline çalışır, timeline değeriyle kapının rotation veya location değeri interpolate edilir.

Akış:

- `OnComponentBeginOverlap` tetiklenir.
- Overlap eden actor player mı kontrol edilir.
- Timeline `Play` çağrılır.
- Timeline update pin'inde `SetRelativeRotation` veya `SetRelativeLocation` kullanılır.
- Çıkışta `OnComponentEndOverlap` ile timeline reverse yapılabilir.

C++ gerekiyorsa aynı mantık `UBoxComponent` ve `FTimeline` ile kurulabilir.""",
    },
    {
        "instruction": "Unreal C++ derleme hatalarında nasıl debug yapılır?",
        "answer": """Önce derleyicinin verdiği ilk hataya bak. Unreal build çıktısında sonraki hatalar çoğu zaman ilk hatanın sonucudur.

Kontrol listesi:

- Header dosyasında `GENERATED_BODY()` doğru yerde mi?
- `.generated.h` include'u en son include mu?
- Sınıf adı dosya ve constructor adıyla uyumlu mu?
- Eksik module dependency var mı?
- Pointer tipleri forward declaration ile yetiyor mu, yoksa include gerekli mi?

Reflection hatalarında Unreal Editor'ü kapatıp temiz build almak da gerekebilir.""",
    },
]


UNITY_PROMPTS = [
    "Unity için basit player movement yaz.",
    "Unity C# ile karakter hareketi örneği ver.",
    "MonoBehaviour içinde WASD movement nasıl yazılır?",
    "Unity'de oyuncu hareket kodunu temiz şekilde göster.",
]

UNREAL_PROMPTS = [
    "Unreal C++ ile basit player movement yaz.",
    "Unreal Engine Character class içinde hareket input'u bağla.",
    "UE C++ AddMovementInput örneği ver.",
    "Unreal'da Character hareket kodunu temiz şekilde göster.",
]

UNREAL_HEALTH_PROMPTS = [
    "Unreal C++ ile Health component yaz.",
    "UE C++ UActorComponent tabanlı health component örneği ver.",
    "Unreal Engine'de can sistemi için UHealthComponent yaz.",
    "Unreal'da BlueprintCallable TakeDamage fonksiyonu olan health component oluştur.",
]


def add_variants(rows, domain, prompts, answer):
    for prompt in prompts:
        rows.append({"domain": domain, "instruction": prompt, "answer": answer})


def build_rows(seed):
    random.seed(seed)
    rows = []

    for item in UNITY_EXAMPLES:
        rows.append({"domain": "unity", **item})
    for item in UNREAL_EXAMPLES:
        rows.append({"domain": "unreal", **item})

    add_variants(rows, "unity", UNITY_PROMPTS, UNITY_EXAMPLES[0]["answer"])
    add_variants(rows, "unreal", UNREAL_PROMPTS, UNREAL_EXAMPLES[0]["answer"])
    add_variants(rows, "unreal", UNREAL_HEALTH_PROMPTS, UNREAL_EXAMPLES[3]["answer"])

    for _ in range(6):
        rows.append({"domain": "unreal", **UNREAL_EXAMPLES[3]})
        rows.append({"domain": "unity", **UNITY_EXAMPLES[3]})
        rows.append({"domain": "unity", **UNITY_EXAMPLES[0]})
        rows.append({"domain": "unreal", **UNREAL_EXAMPLES[0]})

    prefixes = [
        "Kısa açıkla:",
        "Yeni başlayan biri için anlat:",
        "Kod örneğiyle göster:",
        "Hata ayıklama açısından açıkla:",
        "En temiz mimariyle öner:",
    ]
    base_rows = list(rows)
    for prefix in prefixes:
        for item in base_rows:
            rows.append(
                {
                    "domain": item["domain"],
                    "instruction": f"{prefix} {item['instruction']}",
                    "answer": item["answer"],
                }
            )

    # Extra weight helps the small model keep engine-specific syntax separated.
    rows = rows * 3
    random.shuffle(rows)
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="data/instructions/multiengine_v1.jsonl")
    parser.add_argument("--seed", type=int, default=123)
    args = parser.parse_args()

    rows = build_rows(args.seed)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"wrote {len(rows)} rows to {out}")


if __name__ == "__main__":
    main()
