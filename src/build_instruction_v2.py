import argparse
import json
import random
from pathlib import Path


GODOT_EXAMPLES = [
    {
        "instruction": "Godot 4'te CharacterBody2D ile WASD hareket scripti yaz.",
        "answer": """Player node'u `CharacterBody2D` olsun. Input Map'e `move_left`, `move_right`, `move_up`, `move_down` action'larını ekle.

```gdscript
extends CharacterBody2D

@export var speed := 220.0

func _physics_process(delta: float) -> void:
    var dir := Input.get_vector("move_left", "move_right", "move_up", "move_down")
    velocity = dir * speed
    move_and_slide()
```

Godot 4'te `CharacterBody2D` kendi `velocity` alanını kullanır; `move_and_slide()` parametresiz çağrılır.""",
    },
    {
        "instruction": "Godot 4'te zıplamalı platform karakteri yaz.",
        "answer": """Bu script `CharacterBody2D` üzerine takılır. Input Map'te `move_left`, `move_right` ve `jump` action'ları olmalı.

```gdscript
extends CharacterBody2D

@export var speed := 220.0
@export var jump_velocity := -420.0
@export var gravity := 980.0

func _physics_process(delta: float) -> void:
    if not is_on_floor():
        velocity.y += gravity * delta

    var x := Input.get_axis("move_left", "move_right")
    velocity.x = x * speed

    if Input.is_action_just_pressed("jump") and is_on_floor():
        velocity.y = jump_velocity

    move_and_slide()
```""",
    },
    {
        "instruction": "Godot 4'te Area2D coin toplama sistemi nasıl yapılır?",
        "answer": """Coin sahnesinde kök node `Area2D`, altında `CollisionShape2D` ve görsel için `Sprite2D` olabilir. `body_entered` sinyalini coin scriptine bağla.

```gdscript
extends Area2D

@export var value := 1

func _on_body_entered(body: Node) -> void:
    if body.has_method("add_coin"):
        body.add_coin(value)
    queue_free()
```

Oyuncu tarafında:

```gdscript
var coins := 0

func add_coin(amount: int) -> void:
    coins += amount
```

Coin'in collision layer/mask ayarlarının oyuncuyu algıladığından emin ol.""",
    },
    {
        "instruction": "Godot'ta signal nedir ve ne zaman kullanılır?",
        "answer": """Signal, bir node'un başka node'lara olay bildirmesidir. Böylece node'lar birbirine sıkı bağlanmaz. Örneğin Health component can bitince `died` sinyali yayar, UI veya enemy spawner bu olayı dinler.

```gdscript
signal died
signal health_changed(current: int, maximum: int)

var health := 100

func take_damage(amount: int) -> void:
    health -= amount
    health_changed.emit(health, 100)
    if health <= 0:
        died.emit()
```

Signal, skor güncelleme, can değişimi, kapı açma, görev tamamlanması gibi olay tabanlı akışlarda kullanılır.""",
    },
    {
        "instruction": "Godot 4'te düşmanın oyuncuyu takip etmesi için basit GDScript yaz.",
        "answer": """Düşman node'u `CharacterBody2D` olabilir. Oyuncuyu Inspector'dan atamak için `Node2D` referansı export edilir.

```gdscript
extends CharacterBody2D

@export var target: Node2D
@export var speed := 120.0

func _physics_process(delta: float) -> void:
    if target == null:
        velocity = Vector2.ZERO
        return

    var dir := global_position.direction_to(target.global_position)
    velocity = dir * speed
    move_and_slide()
```

Daha iyi sonuç için görüş mesafesi, engel kontrolü ve animasyon state'i eklenebilir.""",
    },
    {
        "instruction": "Godot 4'te Camera2D oyuncuyu nasıl takip eder?",
        "answer": """En basit yöntem `Camera2D` node'unu Player'ın çocuğu yapmak ve `Enabled` ayarını açmaktır. Böylece kamera oyuncuyla birlikte hareket eder.

Kodla yapmak istersen:

```gdscript
extends Camera2D

@export var target: Node2D
@export var follow_speed := 8.0

func _process(delta: float) -> void:
    if target == null:
        return
    global_position = global_position.lerp(target.global_position, follow_speed * delta)
```

Kamera sınırı gerekiyorsa `limit_left`, `limit_right`, `limit_top`, `limit_bottom` değerlerini kullan.""",
    },
    {
        "instruction": "Godot'ta Invalid get index on base Nil hatası ne demek?",
        "answer": """Bu hata genelde `null` olan bir değişkenin alanına erişmeye çalıştığını gösterir. Örneğin `player.health` yazıyorsan ama `player` aslında bulunamamışsa bu hata çıkar.

Kontrol listesi:

- Node yolu doğru mu?
- `@onready var player = $Player` gerçekten sahnede var mı?
- Referans Inspector'dan atanmış mı?
- Node henüz tree'ye eklenmeden mi erişiyorsun?

Güvenli kontrol örneği:

```gdscript
@export var player: Node2D

func _ready() -> void:
    if player == null:
        push_error("Player referansı atanmadı.")
        return
    print(player.global_position)
```""",
    },
    {
        "instruction": "Godot'ta Health component benzeri yapı kur.",
        "answer": """Health'i ayrı bir node olarak tutmak yeniden kullanımı kolaylaştırır. Player, enemy ve kırılabilir objeler aynı component'i kullanabilir.

```gdscript
extends Node
class_name Health

signal changed(current: int, maximum: int)
signal died

@export var maximum := 100
var current := maximum

func take_damage(amount: int) -> void:
    current = max(current - amount, 0)
    changed.emit(current, maximum)
    if current == 0:
        died.emit()

func heal(amount: int) -> void:
    current = min(current + amount, maximum)
    changed.emit(current, maximum)
```

Kullanan node, `Health.died` sinyalini dinleyip ölüm animasyonu, skor veya sahneden silme işlemini yapar.""",
    },
]


VARIANTS = [
    ("WASD", "move_left/move_right/move_up/move_down"),
    ("ok tuşları", "ui_left/ui_right/ui_up/ui_down"),
    ("gamepad sol stick", "move_left/move_right/move_up/move_down"),
]

GODOT_TOPICS = [
    ("AnimatedSprite2D ile idle/run animasyonu", "AnimatedSprite2D", "play"),
    ("Timer ile mermi ateşleme cooldown'u", "Timer", "timeout"),
    ("PackedScene ile mermi spawn etme", "PackedScene", "instantiate"),
    ("RayCast2D ile duvar kontrolü", "RayCast2D", "is_colliding"),
    ("NavigationAgent2D ile hedefe gitme", "NavigationAgent2D", "target_position"),
    ("CanvasLayer ile HUD kurma", "CanvasLayer", "Label"),
    ("AudioStreamPlayer ile ses çalma", "AudioStreamPlayer", "play"),
    ("TileMapLayer kullanan basit dünya yapısı", "TileMapLayer", "terrain"),
    ("Area2D ile hasar alanı oluşturma", "Area2D", "body_entered"),
    ("Save/load için JSON dosyası yazma", "FileAccess", "JSON"),
    ("Global autoload ile GameState tutma", "autoload", "GameState"),
    ("Pause menüsü açıp kapatma", "get_tree().paused", "process_mode"),
]

GENERAL_EXAMPLES = [
    {
        "instruction": "Merhaba, nasılsın?",
        "answer": "Merhaba. İyiyim, sana nasıl yardımcı olabilirim?",
    },
    {
        "instruction": "Bana kısa ve net cevap verir misin?",
        "answer": "Evet. Gereksiz uzatmadan, doğrudan uygulanabilir cevap vermeye çalışırım.",
    },
    {
        "instruction": "Bir konuyu anlamadığımda nasıl çalışmalıyım?",
        "answer": "Önce konuyu küçük parçalara ayır. Her parça için basit bir örnek çöz. Sonra kendi cümlenle açıklamaya çalış. Açıklayamıyorsan o parçaya geri dön.",
    },
    {
        "instruction": "Bugün çalışma planı yapmama yardım et.",
        "answer": "Önce en önemli tek işi seç. Onu 60-90 dakikalık odak bloğuna koy. Sonra kısa bir mola verip ikinci önceliğe geç. Gün sonunda ne bittiğini ve neyin kaldığını not al.",
    },
    {
        "instruction": "Bir fikri daha profesyonel nasıl yazarım?",
        "answer": "Fikri önce tek cümlede söyle, sonra gerekçeyi ekle, en son beklenen sonucu belirt. Örneğin: 'Bu sistemi sadeleştirelim, çünkü bakım maliyeti artıyor. Böylece yeni özellik eklemek daha hızlı olur.'",
    },
    {
        "instruction": "Kısa bir yapılacaklar listesi hazırla.",
        "answer": "Önce ana hedefi yaz. Sonra bu hedef için üç somut adım belirle. Her adımın yanına tahmini süre koy ve en önemlisinden başla.",
    },
    {
        "instruction": "Bir şeyi öğrenirken notları nasıl tutmalıyım?",
        "answer": "Notları başlık, kısa özet, örnek ve kendi cümlenle açıklama şeklinde tut. Sadece kopyalama; öğrendiğin şeyi küçük bir örnekle kullan.",
    },
    {
        "instruction": "Motivasyonum yoksa ne yapmalıyım?",
        "answer": "Motivasyon beklemek yerine işi çok küçült. Sadece beş dakikalık ilk adımı seç. Başladıktan sonra devam edip etmeyeceğine karar ver.",
    },
    {
        "instruction": "Bir e-postayı daha düzgün yazmama yardım et.",
        "answer": "Mesajı kısa tut: selamla başla, neden yazdığını söyle, beklediğin aksiyonu net belirt ve teşekkür ederek bitir.",
    },
    {
        "instruction": "Karmaşık bir problemi nasıl çözmeliyim?",
        "answer": "Önce problemi tek cümleyle tanımla. Bilinenleri ve bilinmeyenleri ayır. Sonra en küçük test edilebilir adımı seçip sonucu kontrol et.",
    },
    {
        "instruction": "Bana sade bir açıklama yap.",
        "answer": "Konuyu teknik kelimelere boğmadan anlatırım. Önce ana fikri söylerim, sonra küçük bir örnek veririm.",
    },
    {
        "instruction": "Bir karar verirken nasıl düşünmeliyim?",
        "answer": "Seçenekleri yaz, her seçeneğin maliyetini ve faydasını karşılaştır. Geri alınabilir kararları hızlı, geri alınması zor kararları daha dikkatli ver.",
    },
    {
        "instruction": "Bugün çok işim var, nereden başlayayım?",
        "answer": "Önce teslim tarihi en yakın ve etkisi en yüksek işi seç. Küçük bir ilk adım belirle, 25 dakika sadece ona odaklan, sonra listeyi yeniden sırala.",
    },
]

MOVEMENT_ANSWER = """Player node'u `CharacterBody2D` olsun. Input Map'e `move_left`, `move_right`, `move_up`, `move_down` action'larını ekle.

```gdscript
extends CharacterBody2D

@export var speed := 220.0

func _physics_process(delta: float) -> void:
    var dir := Input.get_vector("move_left", "move_right", "move_up", "move_down")
    velocity = dir * speed
    move_and_slide()
```

Godot 4'te `CharacterBody2D` hareketinde `velocity` atanır ve `_physics_process` içinde `move_and_slide()` çağrılır."""

MOVEMENT_PROMPTS = [
    "Godot 4'te CharacterBody2D ile WASD hareket scripti yaz.",
    "Godot 4 için basit WASD oyuncu hareketi kodu ver.",
    "CharacterBody2D kullanarak 2D oyuncuyu dört yöne hareket ettir.",
    "Godot'ta yukarı aşağı sağ sol hareket eden Player scripti yaz.",
    "Input.get_vector ile Godot 4 oyuncu hareketi örneği ver.",
    "GDScript ile CharacterBody2D top-down movement yaz.",
    "Godot 4'te move_and_slide kullanan oyuncu hareketi göster.",
    "Yeni başlayan için WASD CharacterBody2D hareketini kodla.",
    "Godot 4 Player node'u için temel movement scripti ver.",
    "WASD action'larıyla çalışan kısa GDScript hareket örneği yaz.",
]


def add_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def general_row(item):
    return {
        "domain": "general",
        "instruction": item["instruction"],
        "answer": item["answer"],
    }


def make_topic_example(topic, node_name, api_name, style):
    if style == "code":
        answer = f"""Aşağıdaki örnek {topic} için başlangıç iskeleti verir.

```gdscript
extends Node2D

@export var target: Node2D

func _ready() -> void:
    if target == null:
        push_warning("Target atanmadı.")

func _process(delta: float) -> void:
    if target == null:
        return
    # {node_name} ve {api_name} kullanımını sahne yapına göre genişlet.
```

Bu yapıyı önce küçük sahnede test et, sonra ana sahneye taşı."""
    else:
        answer = f"""{topic} için ana fikir `{node_name}` node'unu doğru sahneye koyup `{api_name}` tarafını açık bir akışla yönetmektir. Önce küçük bir test sahnesi kur, node referanslarını Inspector'dan ata ve hataları `push_warning` ile görünür hale getir.

Bu özellik gameplay'i etkiliyorsa kodu Player içine gömmek yerine ayrı bir component veya child node olarak tutmak daha temiz olur."""

    return {
        "instruction": f"Godot 4'te {topic} nasıl yapılır?",
        "answer": answer,
    }


def build_rows(seed):
    random.seed(seed)
    rows = []
    rows.extend(GODOT_EXAMPLES)

    for prompt in MOVEMENT_PROMPTS:
        rows.append({"instruction": prompt, "answer": MOVEMENT_ANSWER})

    for controls, actions in VARIANTS:
        rows.append(
            {
                "instruction": f"Godot 4'te {controls} ile 2D oyuncu hareketi yaz.",
                "answer": f"""Input Map'te {actions} action'larını tanımla. Player node'u `CharacterBody2D` olsun.

```gdscript
extends CharacterBody2D

@export var speed := 220.0

func _physics_process(delta: float) -> void:
    var dir := Input.get_vector("move_left", "move_right", "move_up", "move_down")
    velocity = dir * speed
    move_and_slide()
```

Action adlarını kendi Input Map isimlerinle aynı tutmalısın.""",
            }
        )

    prefixes = [
        "Kısa açıkla:",
        "Yeni başlayan biri için anlat:",
        "Kod örneğiyle göster:",
        "Hata ayıklama açısından açıkla:",
        "En temiz mimariyle öner:",
    ]
    base_godot = list(rows)
    for prefix in prefixes:
        for item in base_godot:
            rows.append(
                {
                    "instruction": f"{prefix} {item['instruction']}",
                    "answer": item["answer"],
                }
            )

    general_rows = []
    general_rows.extend(general_row(item) for item in GENERAL_EXAMPLES)
    for item in GENERAL_EXAMPLES:
        general_rows.append(
            {
                "domain": "general",
                "instruction": f"Kısa cevap ver: {item['instruction']}",
                "answer": item["answer"],
            }
        )
        general_rows.append(
            {
                "domain": "general",
                "instruction": f"Daha açıklayıcı cevap ver: {item['instruction']}",
                "answer": item["answer"],
            }
        )

    for _ in range(8):
        rows.extend(general_rows)

    random.shuffle(rows)
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="data/instructions/godot_general_v2.jsonl")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    rows = build_rows(args.seed)
    add_jsonl(Path(args.out), rows)
    print(f"wrote {len(rows)} rows to {args.out}")


if __name__ == "__main__":
    main()
