import argparse
import json
import random
from pathlib import Path


TASKS = [
    {
        "name": "wasd_movement",
        "prompts": [
            "add wasd movement logic to the player object",
            "make my player move with WASD",
            "create a basic player movement script",
            "player objesine wasd hareket sistemi ekle",
            "karakteri klavye ile hareket ettiren kod yaz",
        ],
        "answers": {
            "unity": """Attach this script to the Player GameObject. It reads WASD/arrow input and moves the object every frame.

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
            "godot": """Attach this script to a `CharacterBody3D` player. It reads WASD actions and moves the character.

```gdscript
extends CharacterBody3D

@export var move_speed := 5.0

func _physics_process(delta: float) -> void:
    var input_dir := Input.get_vector("move_left", "move_right", "move_forward", "move_back")
    var direction := Vector3(input_dir.x, 0.0, input_dir.y).normalized()
    velocity.x = direction.x * move_speed
    velocity.z = direction.z * move_speed
    move_and_slide()
```

Add input map actions for `move_left`, `move_right`, `move_forward`, and `move_back`, then bind them to A, D, W, and S.""",
            "unreal": """Add movement input in your character class and bind WASD axis mappings to it.

```cpp
void AMyPlayerCharacter::SetupPlayerInputComponent(UInputComponent* PlayerInputComponent)
{
    Super::SetupPlayerInputComponent(PlayerInputComponent);
    PlayerInputComponent->BindAxis("MoveForward", this, &AMyPlayerCharacter::MoveForward);
    PlayerInputComponent->BindAxis("MoveRight", this, &AMyPlayerCharacter::MoveRight);
}

void AMyPlayerCharacter::MoveForward(float Value)
{
    if (Controller && Value != 0.0f)
    {
        AddMovementInput(GetActorForwardVector(), Value);
    }
}

void AMyPlayerCharacter::MoveRight(float Value)
{
    if (Controller && Value != 0.0f)
    {
        AddMovementInput(GetActorRightVector(), Value);
    }
}
```

Create `MoveForward` and `MoveRight` axis mappings in Project Settings or Enhanced Input, then bind W/S and A/D.""",
        },
    },
    {
        "name": "jump",
        "prompts": [
            "add jump to the player",
            "make the character jump when space is pressed",
            "space tusuyla ziplama ekle",
            "player jump logic yaz",
        ],
        "answers": {
            "unity": """Use a Rigidbody-based jump and only allow jumping while grounded.

```csharp
using UnityEngine;

[RequireComponent(typeof(Rigidbody))]
public class PlayerJump : MonoBehaviour
{
    [SerializeField] private float jumpForce = 6f;
    [SerializeField] private Transform groundCheck;
    [SerializeField] private float groundRadius = 0.2f;
    [SerializeField] private LayerMask groundMask;

    private Rigidbody rb;

    private void Awake()
    {
        rb = GetComponent<Rigidbody>();
    }

    private void Update()
    {
        bool grounded = Physics.CheckSphere(groundCheck.position, groundRadius, groundMask);
        if (grounded && Input.GetKeyDown(KeyCode.Space))
        {
            rb.AddForce(Vector3.up * jumpForce, ForceMode.Impulse);
        }
    }
}
```""",
            "godot": """For `CharacterBody3D`, apply jump velocity only when the body is on the floor.

```gdscript
extends CharacterBody3D

@export var move_speed := 5.0
@export var jump_velocity := 6.0
@export var gravity := 20.0

func _physics_process(delta: float) -> void:
    if not is_on_floor():
        velocity.y -= gravity * delta

    if Input.is_action_just_pressed("jump") and is_on_floor():
        velocity.y = jump_velocity

    move_and_slide()
```""",
            "unreal": """If your class inherits from `ACharacter`, Unreal already provides jump helpers.

```cpp
void AMyPlayerCharacter::SetupPlayerInputComponent(UInputComponent* PlayerInputComponent)
{
    Super::SetupPlayerInputComponent(PlayerInputComponent);
    PlayerInputComponent->BindAction("Jump", IE_Pressed, this, &ACharacter::Jump);
    PlayerInputComponent->BindAction("Jump", IE_Released, this, &ACharacter::StopJumping);
}
```

Set `Jump Z Velocity` on the Character Movement component to tune the jump height.""",
        },
    },
    {
        "name": "red_cube",
        "prompts": [
            "create a red cube in the scene",
            "add a cube and make it red",
            "sahneye kirmizi kup ekle",
            "spawn red cube object",
        ],
        "answers": {
            "unity": """Create a cube, assign a red material, and place it in front of the camera.

```csharp
using UnityEngine;

public class RedCubeSpawner : MonoBehaviour
{
    private void Start()
    {
        GameObject cube = GameObject.CreatePrimitive(PrimitiveType.Cube);
        cube.name = "Red Cube";
        cube.transform.position = new Vector3(0f, 1f, 0f);

        Renderer renderer = cube.GetComponent<Renderer>();
        renderer.material = new Material(Shader.Find("Standard"));
        renderer.material.color = Color.red;
    }
}
```""",
            "godot": """Create a `MeshInstance3D`, assign a `BoxMesh`, and give it a red material.

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
```""",
            "unreal": """Spawn a cube mesh actor and assign a red material instance in C++.

```cpp
// In BeginPlay after assigning CubeMesh and RedMaterial in the editor.
FActorSpawnParameters Params;
AStaticMeshActor* Cube = GetWorld()->SpawnActor<AStaticMeshActor>(AStaticMeshActor::StaticClass(), FVector(0, 0, 100), FRotator::ZeroRotator, Params);
Cube->GetStaticMeshComponent()->SetStaticMesh(CubeMesh);
Cube->GetStaticMeshComponent()->SetMaterial(0, RedMaterial);
Cube->SetActorLabel(TEXT("RedCube"));
```

Expose `CubeMesh` and `RedMaterial` as `UPROPERTY(EditAnywhere)` fields so they can be assigned in the editor.""",
        },
    },
    {
        "name": "health",
        "prompts": [
            "add health system to the player",
            "write player health logic",
            "player can take damage and die",
            "oyuncuya can sistemi ekle",
        ],
        "answers": {
            "unity": """Put health in its own component so player, enemies, and destructible objects can reuse it.

```csharp
using System;
using UnityEngine;

public class Health : MonoBehaviour
{
    [SerializeField] private int maxHealth = 100;

    public int CurrentHealth { get; private set; }
    public event Action<int, int> Changed;
    public event Action Died;

    private void Awake()
    {
        CurrentHealth = maxHealth;
    }

    public void TakeDamage(int amount)
    {
        CurrentHealth = Mathf.Max(CurrentHealth - amount, 0);
        Changed?.Invoke(CurrentHealth, maxHealth);

        if (CurrentHealth == 0)
            Died?.Invoke();
    }
}
```""",
            "godot": """Use a small health component node and emit signals when health changes.

```gdscript
extends Node

signal health_changed(current: int, maximum: int)
signal died

@export var max_health := 100
var current_health := 100

func _ready() -> void:
    current_health = max_health

func take_damage(amount: int) -> void:
    current_health = max(current_health - amount, 0)
    health_changed.emit(current_health, max_health)
    if current_health == 0:
        died.emit()
```""",
            "unreal": """A reusable `UActorComponent` is the cleanest place for health.

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
    }
};
```""",
        },
    },
    {
        "name": "camera_follow",
        "prompts": [
            "add camera follow to player",
            "make camera follow the player smoothly",
            "kamerayi oyuncuyu takip edecek sekilde ayarla",
            "third person follow camera code",
        ],
        "answers": {
            "unity": """Put this script on the Camera and assign the player Transform.

```csharp
using UnityEngine;

public class FollowCamera : MonoBehaviour
{
    [SerializeField] private Transform target;
    [SerializeField] private Vector3 offset = new Vector3(0f, 4f, -6f);
    [SerializeField] private float smoothTime = 0.15f;

    private Vector3 velocity;

    private void LateUpdate()
    {
        if (target == null)
            return;

        Vector3 desired = target.position + offset;
        transform.position = Vector3.SmoothDamp(transform.position, desired, ref velocity, smoothTime);
        transform.LookAt(target);
    }
}
```""",
            "godot": """Put a `Camera3D` under a spring arm or update the camera in `_physics_process`.

```gdscript
extends Camera3D

@export var target: Node3D
@export var offset := Vector3(0, 4, -6)
@export var follow_speed := 8.0

func _physics_process(delta: float) -> void:
    if target == null:
        return
    global_position = global_position.lerp(target.global_position + offset, follow_speed * delta)
    look_at(target.global_position)
```""",
            "unreal": """For a third-person character, use a spring arm plus camera component.

```cpp
CameraBoom = CreateDefaultSubobject<USpringArmComponent>(TEXT("CameraBoom"));
CameraBoom->SetupAttachment(RootComponent);
CameraBoom->TargetArmLength = 350.0f;
CameraBoom->bUsePawnControlRotation = true;

FollowCamera = CreateDefaultSubobject<UCameraComponent>(TEXT("FollowCamera"));
FollowCamera->SetupAttachment(CameraBoom, USpringArmComponent::SocketName);
FollowCamera->bUsePawnControlRotation = false;
```

Then rotate the controller from mouse input and let the spring arm follow the character.""",
        },
    },
    {
        "name": "projectile",
        "prompts": [
            "shoot projectile when player presses left mouse",
            "add fireball shooting logic",
            "sol tikla mermi atma sistemi yaz",
            "spawn projectile from player",
        ],
        "answers": {
            "unity": """Instantiate a projectile prefab from a fire point and push it forward.

```csharp
using UnityEngine;

public class PlayerShooter : MonoBehaviour
{
    [SerializeField] private Rigidbody projectilePrefab;
    [SerializeField] private Transform firePoint;
    [SerializeField] private float projectileSpeed = 18f;

    private void Update()
    {
        if (Input.GetMouseButtonDown(0))
        {
            Rigidbody projectile = Instantiate(projectilePrefab, firePoint.position, firePoint.rotation);
            projectile.linearVelocity = firePoint.forward * projectileSpeed;
        }
    }
}
```""",
            "godot": """Instantiate a projectile scene from a marker node and pass it velocity.

```gdscript
extends Node3D

@export var projectile_scene: PackedScene
@export var fire_point: Node3D
@export var projectile_speed := 18.0

func _process(_delta: float) -> void:
    if Input.is_action_just_pressed("fire"):
        var projectile := projectile_scene.instantiate()
        projectile.global_transform = fire_point.global_transform
        projectile.velocity = -fire_point.global_transform.basis.z * projectile_speed
        get_tree().current_scene.add_child(projectile)
```""",
            "unreal": """Spawn a projectile actor from a muzzle transform.

```cpp
void AMyPlayerCharacter::Fire()
{
    if (!ProjectileClass)
        return;

    const FVector SpawnLocation = Muzzle->GetComponentLocation();
    const FRotator SpawnRotation = Muzzle->GetComponentRotation();
    GetWorld()->SpawnActor<AActor>(ProjectileClass, SpawnLocation, SpawnRotation);
}
```

Bind `Fire` to the left mouse button and give the projectile a movement component.""",
        },
    },
]


DOMAIN_PREFIXES = {
    "unity": [
        "Unity C# olarak yaz:",
        "Write this for Unity:",
        "Use MonoBehaviour and valid Unity API:",
    ],
    "godot": [
        "Godot 4 GDScript olarak yaz:",
        "Write this for Godot:",
        "Use Godot 4 nodes and GDScript:",
    ],
    "unreal": [
        "Unreal Engine 5 C++ olarak yaz:",
        "Write this for Unreal Engine:",
        "Use UE5 C++ macros and APIs:",
    ],
}


def make_rows(repeat):
    rows = []
    for task in TASKS:
        for domain, answer in task["answers"].items():
            prompts = []
            for prompt in task["prompts"]:
                prompts.append(prompt)
                for prefix in DOMAIN_PREFIXES[domain]:
                    prompts.append(f"{prefix} {prompt}")
            prompts.append(f"{domain} {task['name']} code")
            prompts.append(f"{domain} icin {task['name']} sistemi yaz")

            for _ in range(repeat):
                for prompt in prompts:
                    rows.append(
                        {
                            "domain": domain,
                            "instruction": prompt,
                            "answer": answer,
                            "source": f"synthetic_direct_command/{task['name']}",
                        }
                    )
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="data/instructions/direct_game_commands_v1.jsonl")
    parser.add_argument("--repeat", type=int, default=140)
    parser.add_argument("--seed", type=int, default=6061)
    args = parser.parse_args()

    rows = make_rows(args.repeat)
    random.seed(args.seed)
    random.shuffle(rows)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"wrote {len(rows)} rows -> {out}")
    for domain in ("godot", "unity", "unreal"):
        print(f"{domain}: {sum(1 for row in rows if row['domain'] == domain)}")


if __name__ == "__main__":
    main()
