import argparse
import json
import random
from pathlib import Path


EXAMPLES = [
    {
        "instruction": "Unreal C++ ile line trace kullanarak crosshair yönüne ateş etme örneği yaz.",
        "answer": """FPS karakterinde instant hit ateş için `UCameraComponent` üzerinden başlayıp ileri yöne line trace atabilirsin. Muzzle'dan debug line çizmek sonucu görmeyi kolaylaştırır.

```cpp
#include "DrawDebugHelpers.h"
#include "Camera/CameraComponent.h"
#include "Kismet/GameplayStatics.h"

void AMyProjectCharacter::OnFire()
{
    FVector StartLocation = FirstPersonCameraComponent->GetComponentLocation();
    FVector AimDirection = FirstPersonCameraComponent->GetForwardVector();
    FVector EndLocation = StartLocation + AimDirection * 20000.0f;

    FHitResult Hit;
    bool bHit = GetWorld()->LineTraceSingleByChannel(
        Hit,
        StartLocation,
        EndLocation,
        ECC_Visibility
    );

    FVector TraceEnd = bHit ? Hit.Location : EndLocation;
    DrawDebugLine(
        GetWorld(),
        FP_MuzzleLocation->GetComponentLocation(),
        TraceEnd,
        FColor::Green,
        false,
        2.0f
    );

    if (bHit)
    {
        DrawDebugString(GetWorld(), Hit.ImpactPoint, TEXT("Hit"), nullptr, FColor::White, 2.0f);
    }

    if (FireSound)
    {
        UGameplayStatics::PlaySoundAtLocation(this, FireSound, GetActorLocation());
    }
}
```

Gerçek oyunda hasar için `Hit.GetActor()` kontrol edilir ve interface, damage event veya gameplay ability sistemi çağrılır.""",
    },
    {
        "instruction": "Unreal C++ ile projectile'ı crosshair yönüne spawn et.",
        "answer": """Projectile tabanlı ateşte spawn konumunu muzzle'dan alıp rotation'ı kameranın bakış yönünden üretmek yaygın bir çözümdür.

```cpp
void AMyProjectCharacter::OnFire()
{
    if (!ProjectileClass)
    {
        return;
    }

    UWorld* World = GetWorld();
    if (!World)
    {
        return;
    }

    FVector SpawnLocation = FP_MuzzleLocation->GetComponentLocation();
    FRotator SpawnRotation = FirstPersonCameraComponent->GetComponentRotation();

    FActorSpawnParameters SpawnParams;
    SpawnParams.Owner = this;
    SpawnParams.Instigator = GetInstigator();

    World->SpawnActor<AMyProjectProjectile>(
        ProjectileClass,
        SpawnLocation,
        SpawnRotation,
        SpawnParams
    );
}
```

Projectile class içinde `UProjectileMovementComponent` kullanıp hız, gravity ve collision ayarlarını component üzerinden yönetebilirsin.""",
    },
    {
        "instruction": "Unreal C++ ile silah değiştirme sistemi için temel class yapısı öner.",
        "answer": """Basit bir yapı için karakterde iki mesh, weapon map ve input action bulunabilir. Silah davranışını `AMyWeapon` actor'ünde, animasyon durumunu anim instance içinde tut.

```cpp
// Character.h
UPROPERTY(VisibleAnywhere)
USkeletalMeshComponent* Pistol;

UPROPERTY(VisibleAnywhere)
USkeletalMeshComponent* Rifle;

UPROPERTY()
TMap<FName, AMyWeapon*> MyWeapons;

void EquipSidearm();
void EquipRifle();
```

```cpp
void AMyProjectCharacter::SetupPlayerInputComponent(UInputComponent* PlayerInputComponent)
{
    Super::SetupPlayerInputComponent(PlayerInputComponent);
    PlayerInputComponent->BindAction("Sidearm", IE_Pressed, this, &AMyProjectCharacter::EquipSidearm);
    PlayerInputComponent->BindAction("Rifle", IE_Pressed, this, &AMyProjectCharacter::EquipRifle);
}

void AMyProjectCharacter::EquipSidearm()
{
    if (!MyWeapons.Contains("Pistol"))
    {
        UE_LOG(LogTemp, Warning, TEXT("No Pistol"));
        return;
    }

    CurrentWeapon = *MyWeapons.Find("Pistol");
    PlayAnimMontage(EquipSidearmMontage, 1.5f);
}
```

Daha sağlam sistemde silahları string yerine enum veya gameplay tag ile tut, current weapon state'ini anim instance'a bağımlı yapma.""",
    },
    {
        "instruction": "Unreal C++ ile TriggerBox overlap örneği yaz.",
        "answer": """`ATriggerBox` türetip constructor içinde `OnActorBeginOverlap` event'ine fonksiyon bağlayabilirsin.

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
    if (GEngine)
    {
        GEngine->AddOnScreenDebugMessage(-1, 5.0f, FColor::Green, TEXT("Begin Overlap"));
    }
}
```""",
    },
    {
        "instruction": "Unreal C++ ile SweepMultiByChannel nasıl kullanılır?",
        "answer": """Sweep, bir şekli iki nokta arasında hareket ettirip çarpışan aktörleri bulur. AoE, melee hitbox veya projectile yakın kontrolü için kullanılabilir.

```cpp
TArray<FHitResult> Hits;
FVector Start = GetActorLocation();
FVector End = Start + GetActorForwardVector() * 500.0f;
FCollisionShape Sphere = FCollisionShape::MakeSphere(75.0f);

bool bHit = GetWorld()->SweepMultiByChannel(
    Hits,
    Start,
    End,
    FQuat::Identity,
    ECC_Pawn,
    Sphere
);

if (bHit)
{
    for (const FHitResult& Hit : Hits)
    {
        AActor* HitActor = Hit.GetActor();
        if (HitActor)
        {
            UE_LOG(LogTemp, Log, TEXT("Sweep hit: %s"), *HitActor->GetName());
        }
    }
}
```

Debug için `DrawDebugSphere` veya `DrawDebugCapsule` eklemek çarpışma hacmini görmeyi kolaylaştırır.""",
    },
    {
        "instruction": "Unreal C++ ile RadialForceComponent kullanan patlama projectile örneği ver.",
        "answer": """Patlayan projectile içinde `URadialForceComponent` oluşturup impact anında impulse uygulayabilirsin.

```cpp
UPROPERTY(VisibleAnywhere)
URadialForceComponent* ExplosionForce;

AMyProjectProjectile::AMyProjectProjectile()
{
    ExplosionForce = CreateDefaultSubobject<URadialForceComponent>(TEXT("ExplosionForce"));
    ExplosionForce->SetupAttachment(RootComponent);
    ExplosionForce->Radius = 500.0f;
    ExplosionForce->ImpulseStrength = 1500.0f;
    ExplosionForce->bImpulseVelChange = true;
}

void AMyProjectProjectile::OnHit(
    UPrimitiveComponent* HitComp,
    AActor* OtherActor,
    UPrimitiveComponent* OtherComp,
    FVector NormalImpulse,
    const FHitResult& Hit
)
{
    ExplosionForce->FireImpulse();
    Destroy();
}
```

Physics etkisi için hedef component'lerde simulate physics açık olmalı veya ayrıca damage sistemi çağrılmalıdır.""",
    },
]


PROMPT_VARIANTS = {
    0: [
        "Unreal'da crosshair doğrultusunda LineTraceSingleByChannel ile ateş et.",
        "UE5 C++ FPS karakterinde kameradan line trace atıp hit debug çiz.",
        "Unreal Engine line trace silah ateşi C++ örneği ver.",
    ],
    1: [
        "Unreal'da muzzle konumundan projectile spawn etme kodu yaz.",
        "UE5 C++ projectile weapon fire örneği ver.",
    ],
    2: [
        "UE5 C++ weapon switch sistemi nasıl kurulur?",
        "Unreal'da pistol ve rifle arasında geçiş yapan karakter kodu öner.",
    ],
    3: [
        "UE5 C++ TriggerBox begin overlap örneği ver.",
        "Unreal TriggerBox ile overlap olduğunda ekrana mesaj yaz.",
    ],
    4: [
        "Unreal SweepMultiByChannel ile yakın alan tarama örneği yaz.",
        "UE5 C++ sphere sweep ile hit aktörleri bul.",
    ],
    5: [
        "UE5 C++ RadialForceComponent ile patlama kuvveti uygula.",
        "Unreal projectile impact olunca radial impulse versin.",
    ],
}


def build_rows(seed):
    rows = []
    for index, item in enumerate(EXAMPLES):
        rows.append({"domain": "unreal", **item})
        for prompt in PROMPT_VARIANTS.get(index, []):
            rows.append({"domain": "unreal", "instruction": prompt, "answer": item["answer"]})

    prefixes = ["Kod örneğiyle göster:", "Yeni başlayan için anlat:", "Kısa ve temiz yaz:"]
    base = list(rows)
    for prefix in prefixes:
        for item in base:
            rows.append(
                {
                    "domain": "unreal",
                    "instruction": f"{prefix} {item['instruction']}",
                    "answer": item["answer"],
                }
            )

    rows = rows * 5
    random.seed(seed)
    random.shuffle(rows)
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="data/instructions/unreal5_examples_v1.jsonl")
    parser.add_argument("--seed", type=int, default=77)
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
