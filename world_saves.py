from __future__ import annotations

import json
import re
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from config import (
    CHUNK_SIZE,
    MAX_TERRAIN_HEIGHT,
    PLAYER_GRAVITY,
    PLAYER_HEIGHT,
    PLAYER_JUMP_HEIGHT,
    PLAYER_SPRINT_SPEED,
    PLAYER_WALK_SPEED,
    REACH_DISTANCE,
    STARTING_TOKENS,
    THIRD_PERSON_DISTANCE,
    TREE_CHANCE,
    WATER_LEVEL,
    WORLD_SIZE,
    PROJECT_ROOT,
)


SAVES_DIR = PROJECT_ROOT / "saves"
SAVE_VERSION = 1


@dataclass
class WorldSettings:
    # World generation
    world_size: int = WORLD_SIZE
    chunk_size: int = CHUNK_SIZE
    world_seed: int = 7
    water_level: int = WATER_LEVEL
    max_terrain_height: int = MAX_TERRAIN_HEIGHT
    tree_chance: float = TREE_CHANCE

    # Terrain shape
    terrain_base_height: int = 3
    terrain_x_frequency: float = 0.34
    terrain_x_amplitude: float = 1.30
    terrain_z_frequency: float = 0.29
    terrain_z_amplitude: float = 1.10
    terrain_detail_frequency: float = 0.17
    terrain_detail_amplitude: float = 0.80
    tree_min_height: int = 3
    tree_max_height: int = 4

    # Water
    water_max_flow_level: int = 7
    water_flow_tick: float = 0.12
    water_updates_per_tick: int = 24
    water_texture_flow_u: float = 0.045
    water_texture_flow_v: float = 0.018

    # Lava
    lava_lake_count: int = 4
    lava_lake_min_radius: int = 2
    lava_lake_max_radius: int = 4
    lava_safe_spawn_radius: int = 7
    lava_texture_flow_u: float = 0.018
    lava_texture_flow_v: float = 0.009
    lava_damage: float = 1.5
    lava_damage_interval: float = 1.0

    # Player
    player_height: float = PLAYER_HEIGHT
    player_walk_speed: float = PLAYER_WALK_SPEED
    player_sprint_speed: float = PLAYER_SPRINT_SPEED
    player_gravity: float = PLAYER_GRAVITY
    player_jump_height: float = PLAYER_JUMP_HEIGHT
    third_person_distance: float = THIRD_PERSON_DISTANCE
    reach_distance: float = REACH_DISTANCE

    # Maths / progression
    difficulty: str = "easy"
    easy_reward: int = 1
    medium_reward: int = 5
    hard_reward: int = 10
    starting_tokens: int = STARTING_TOKENS

    first_quest_questions_needed: int = 3
    first_quest_blocks_mined_needed: int = 5
    first_quest_blocks_placed_needed: int = 3
    first_quest_reward: int = 20
    streak_quest_needed: int = 5
    streak_quest_reward: int = 10

    # Display / audio
    sound: float = 0.80
    fov: int = 90
    vsync: bool = True

    # Day / night
    day_night_cycle: bool = True

    # Real-world minutes required for one complete 24-hour
    # Mathcraft day.
    day_length_minutes: float = 24.0

    # Time used when a new world is first created.
    start_time_hours: float = 8.0

    # Survival
    max_health: float = 10.0
    max_oxygen: int = 10
    oxygen_loss_interval: float = 1.0
    oxygen_recovery_interval: float = 0.25
    drowning_damage: float = 1.0
    drowning_damage_interval: float = 1.0

    # Zombies
    zombie_spawning: bool = True
    zombie_notice_distance: float = 18.0
    zombie_min_spawn_delay: float = 7.0
    zombie_max_spawn_delay: float = 13.0
    zombie_initial_delay: float = 3.0
    zombie_min_spawn_distance: float = 10.0
    zombie_max_spawn_distance: float = 24.0
    zombie_despawn_distance: float = 48.0
    zombie_spawn_attempts: int = 24
    zombie_max_count: int = 10
    zombie_max_health: int = 3
    zombie_speed: float = 2.2
    zombie_stop_distance: float = 1.15
    zombie_step_height: float = 0.30
    zombie_jump_speed: float = 5.4
    zombie_gravity: float = 14.0
    zombie_max_jump_height: float = 1.25
    zombie_knockback: float = 0.55
    zombie_attack_damage: float = 0.5
    zombie_attack_interval: float = 1.0

    # Zombie texture filenames inside assets/entity
    zombie_head_texture: str = "missing.png"
    zombie_head_top_texture: str = "missing.png"
    zombie_body_texture: str = "missing.png"
    zombie_left_arm_texture: str = "missing.png"
    zombie_right_arm_texture: str = "missing.png"
    zombie_left_leg_texture: str = "missing.png"
    zombie_right_leg_texture: str = "missing.png"

    def normalise(self) -> None:
        self.world_size = max(16, min(256, int(self.world_size)))
        if self.world_size % 2:
            self.world_size += 1

        self.chunk_size = max(4, min(64, int(self.chunk_size)))
        self.world_seed = int(self.world_seed)
        self.water_level = max(0, min(32, int(self.water_level)))
        self.max_terrain_height = max(1, min(32, int(self.max_terrain_height)))
        self.tree_chance = max(0.0, min(1.0, float(self.tree_chance)))

        self.terrain_base_height = max(1, min(24, int(self.terrain_base_height)))
        self.terrain_x_frequency = max(0.001, min(2.0, float(self.terrain_x_frequency)))
        self.terrain_x_amplitude = max(0.0, min(16.0, float(self.terrain_x_amplitude)))
        self.terrain_z_frequency = max(0.001, min(2.0, float(self.terrain_z_frequency)))
        self.terrain_z_amplitude = max(0.0, min(16.0, float(self.terrain_z_amplitude)))
        self.terrain_detail_frequency = max(0.001, min(2.0, float(self.terrain_detail_frequency)))
        self.terrain_detail_amplitude = max(0.0, min(16.0, float(self.terrain_detail_amplitude)))
        self.tree_min_height = max(1, min(16, int(self.tree_min_height)))
        self.tree_max_height = max(self.tree_min_height, min(24, int(self.tree_max_height)))

        self.water_max_flow_level = max(1, min(32, int(self.water_max_flow_level)))
        self.water_flow_tick = max(0.02, min(5.0, float(self.water_flow_tick)))
        self.water_updates_per_tick = max(1, min(2048, int(self.water_updates_per_tick)))
        self.water_texture_flow_u = max(-2.0, min(2.0, float(self.water_texture_flow_u)))
        self.water_texture_flow_v = max(-2.0, min(2.0, float(self.water_texture_flow_v)))

        self.lava_lake_count = max(0, min(100, int(self.lava_lake_count)))
        self.lava_lake_min_radius = max(1, min(12, int(self.lava_lake_min_radius)))
        self.lava_lake_max_radius = max(
            self.lava_lake_min_radius,
            min(16, int(self.lava_lake_max_radius)),
        )
        self.lava_safe_spawn_radius = max(0, min(32, int(self.lava_safe_spawn_radius)))
        self.lava_texture_flow_u = max(-2.0, min(2.0, float(self.lava_texture_flow_u)))
        self.lava_texture_flow_v = max(-2.0, min(2.0, float(self.lava_texture_flow_v)))
        self.lava_damage = max(
            0.5,
            min(
                100.0,
                round(float(self.lava_damage) * 2.0) / 2.0,
            ),
        )
        self.lava_damage_interval = max(
            0.05,
            min(
                60.0,
                float(self.lava_damage_interval),
            ),
        )

        self.player_height = max(0.5, min(4.0, float(self.player_height)))
        self.player_walk_speed = max(0.1, min(30.0, float(self.player_walk_speed)))
        self.player_sprint_speed = max(0.1, min(50.0, float(self.player_sprint_speed)))
        self.player_gravity = max(0.0, min(10.0, float(self.player_gravity)))
        self.player_jump_height = max(0.0, min(10.0, float(self.player_jump_height)))
        self.third_person_distance = max(0.5, min(20.0, float(self.third_person_distance)))
        self.reach_distance = max(1.0, min(20.0, float(self.reach_distance)))

        self.difficulty = str(self.difficulty).lower().strip()
        if self.difficulty not in ("easy", "medium", "hard"):
            self.difficulty = "easy"

        self.easy_reward = max(0, min(9999, int(self.easy_reward)))
        self.medium_reward = max(0, min(9999, int(self.medium_reward)))
        self.hard_reward = max(0, min(9999, int(self.hard_reward)))
        self.starting_tokens = max(0, min(999999, int(self.starting_tokens)))

        self.first_quest_questions_needed = max(0, min(999, int(self.first_quest_questions_needed)))
        self.first_quest_blocks_mined_needed = max(0, min(999, int(self.first_quest_blocks_mined_needed)))
        self.first_quest_blocks_placed_needed = max(0, min(999, int(self.first_quest_blocks_placed_needed)))
        self.first_quest_reward = max(0, min(999999, int(self.first_quest_reward)))
        self.streak_quest_needed = max(1, min(999, int(self.streak_quest_needed)))
        self.streak_quest_reward = max(0, min(999999, int(self.streak_quest_reward)))

        self.sound = max(0.0, min(1.0, float(self.sound)))
        self.fov = max(60, min(120, int(self.fov)))
        self.vsync = bool(self.vsync)

        self.day_night_cycle = bool(
            self.day_night_cycle
        )

        self.day_length_minutes = max(
            0.1,
            min(
                1440.0,
                float(
                    self.day_length_minutes
                ),
            ),
        )

        self.start_time_hours = (
            float(
                self.start_time_hours
            )
            % 24.0
        )

        self.max_health = max(0.5, min(10.0, round(float(self.max_health) * 2.0) / 2.0))
        self.max_oxygen = max(1, min(10, int(self.max_oxygen)))
        self.oxygen_loss_interval = max(0.05, min(60.0, float(self.oxygen_loss_interval)))
        self.oxygen_recovery_interval = max(0.05, min(60.0, float(self.oxygen_recovery_interval)))
        self.drowning_damage = max(0.5, min(100.0, round(float(self.drowning_damage) * 2.0) / 2.0))
        self.drowning_damage_interval = max(0.05, min(60.0, float(self.drowning_damage_interval)))

        self.zombie_spawning = bool(self.zombie_spawning)
        self.zombie_notice_distance = max(0.0, min(256.0, float(self.zombie_notice_distance)))
        self.zombie_min_spawn_delay = max(0.1, min(3600.0, float(self.zombie_min_spawn_delay)))
        self.zombie_max_spawn_delay = max(self.zombie_min_spawn_delay, min(3600.0, float(self.zombie_max_spawn_delay)))
        self.zombie_initial_delay = max(0.0, min(3600.0, float(self.zombie_initial_delay)))
        self.zombie_min_spawn_distance = max(1.0, min(256.0, float(self.zombie_min_spawn_distance)))
        self.zombie_max_spawn_distance = max(self.zombie_min_spawn_distance, min(256.0, float(self.zombie_max_spawn_distance)))
        self.zombie_despawn_distance = max(self.zombie_max_spawn_distance, min(512.0, float(self.zombie_despawn_distance)))
        self.zombie_spawn_attempts = max(1, min(2048, int(self.zombie_spawn_attempts)))
        self.zombie_max_count = max(0, min(512, int(self.zombie_max_count)))
        self.zombie_max_health = max(1, min(9999, int(self.zombie_max_health)))
        self.zombie_speed = max(0.0, min(50.0, float(self.zombie_speed)))
        self.zombie_stop_distance = max(0.1, min(10.0, float(self.zombie_stop_distance)))
        self.zombie_step_height = max(0.0, min(4.0, float(self.zombie_step_height)))
        self.zombie_jump_speed = max(0.0, min(50.0, float(self.zombie_jump_speed)))
        self.zombie_gravity = max(0.0, min(100.0, float(self.zombie_gravity)))
        self.zombie_max_jump_height = max(0.0, min(10.0, float(self.zombie_max_jump_height)))
        self.zombie_knockback = max(0.0, min(10.0, float(self.zombie_knockback)))
        self.zombie_attack_damage = max(0.5, min(100.0, round(float(self.zombie_attack_damage) * 2.0) / 2.0))
        self.zombie_attack_interval = max(0.05, min(60.0, float(self.zombie_attack_interval)))

        for key in (
            "zombie_head_texture",
            "zombie_head_top_texture",
            "zombie_body_texture",
            "zombie_left_arm_texture",
            "zombie_right_arm_texture",
            "zombie_left_leg_texture",
            "zombie_right_leg_texture",
        ):
            value = Path(str(getattr(self, key))).name.strip()
            setattr(self, key, value or "missing.png")

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "WorldSettings":
        data = data or {}
        allowed = set(cls.__dataclass_fields__)
        filtered = {key: value for key, value in data.items() if key in allowed}
        settings = cls(**filtered)
        settings.normalise()
        return settings

    @classmethod
    def from_text_values(cls, values: dict[str, str]) -> "WorldSettings":
        defaults = cls()
        data: dict[str, Any] = {}

        for key in cls.__dataclass_fields__:
            raw = values.get(key, str(getattr(defaults, key))).strip()
            current = getattr(defaults, key)

            try:
                if isinstance(current, bool):
                    lowered = raw.lower()
                    if lowered in ("true", "1", "yes", "on"):
                        data[key] = True
                    elif lowered in ("false", "0", "no", "off"):
                        data[key] = False
                    else:
                        raise ValueError("use true or false")
                elif isinstance(current, int) and not isinstance(current, bool):
                    data[key] = int(float(raw))
                elif isinstance(current, float):
                    data[key] = float(raw)
                else:
                    data[key] = raw
            except ValueError as exc:
                raise ValueError(f"Invalid value for {key}: {raw!r} ({exc})") from exc

        settings = cls(**data)
        settings.normalise()
        return settings

    def text_values(self) -> dict[str, str]:
        result = {}
        for key, value in asdict(self).items():
            if isinstance(value, bool):
                result[key] = "true" if value else "false"
            else:
                result[key] = str(value)
        return result


WORLD_SETTING_FIELDS = (
    # page, key, label
    ("WORLD 1", "world_size", "World size"),
    ("WORLD 1", "chunk_size", "Chunk size"),
    ("WORLD 1", "world_seed", "World seed"),
    ("WORLD 1", "water_level", "Water level"),
    ("WORLD 1", "max_terrain_height", "Max terrain height"),
    ("WORLD 1", "tree_chance", "Tree chance (0-1)"),
    ("WORLD 1", "terrain_base_height", "Terrain base height"),

    ("WORLD 2", "terrain_x_frequency", "Terrain X frequency"),
    ("WORLD 2", "terrain_x_amplitude", "Terrain X amplitude"),
    ("WORLD 2", "terrain_z_frequency", "Terrain Z frequency"),
    ("WORLD 2", "terrain_z_amplitude", "Terrain Z amplitude"),
    ("WORLD 2", "terrain_detail_frequency", "Detail frequency"),
    ("WORLD 2", "terrain_detail_amplitude", "Detail amplitude"),
    ("WORLD 2", "tree_min_height", "Tree minimum height"),
    ("WORLD 2", "tree_max_height", "Tree maximum height"),

    ("WATER", "water_max_flow_level", "Maximum flow distance"),
    ("WATER", "water_flow_tick", "Water update interval"),
    ("WATER", "water_updates_per_tick", "Water updates per tick"),
    ("WATER", "water_texture_flow_u", "Texture flow X"),
    ("WATER", "water_texture_flow_v", "Texture flow Y"),

    ("LAVA", "lava_lake_count", "Lava lake count"),
    ("LAVA", "lava_lake_min_radius", "Minimum lake radius"),
    ("LAVA", "lava_lake_max_radius", "Maximum lake radius"),
    ("LAVA", "lava_safe_spawn_radius", "Safe radius around spawn"),
    ("LAVA", "lava_texture_flow_u", "Texture flow X"),
    ("LAVA", "lava_texture_flow_v", "Texture flow Y"),
    ("LAVA", "lava_damage", "Lava damage (hearts)"),
    ("LAVA", "lava_damage_interval", "Lava damage interval"),

    ("PLAYER", "player_height", "Player height"),
    ("PLAYER", "player_walk_speed", "Walk speed"),
    ("PLAYER", "player_sprint_speed", "Sprint speed"),
    ("PLAYER", "player_gravity", "Player gravity"),
    ("PLAYER", "player_jump_height", "Jump height"),
    ("PLAYER", "third_person_distance", "Third-person distance"),
    ("PLAYER", "reach_distance", "Reach distance"),

    ("SURVIVAL", "max_health", "Maximum hearts"),
    ("SURVIVAL", "max_oxygen", "Maximum bubbles"),
    ("SURVIVAL", "oxygen_loss_interval", "Seconds per bubble lost"),
    ("SURVIVAL", "oxygen_recovery_interval", "Seconds per bubble restored"),
    ("SURVIVAL", "drowning_damage", "Drowning damage (hearts)"),
    ("SURVIVAL", "drowning_damage_interval", "Drowning damage interval"),

    ("MATHS", "difficulty", "Difficulty: easy/medium/hard"),
    ("MATHS", "easy_reward", "Easy answer reward"),
    ("MATHS", "medium_reward", "Medium answer reward"),
    ("MATHS", "hard_reward", "Hard answer reward"),
    ("MATHS", "starting_tokens", "Starting tokens"),
    ("MATHS", "first_quest_questions_needed", "First quest: equations"),
    ("MATHS", "first_quest_blocks_mined_needed", "First quest: blocks mined"),
    ("MATHS", "first_quest_blocks_placed_needed", "First quest: blocks placed"),

    ("QUESTS", "first_quest_reward", "The First Equation reward"),
    ("QUESTS", "streak_quest_needed", "Streak quest target"),
    ("QUESTS", "streak_quest_reward", "Streak quest reward"),

    ("DISPLAY", "sound", "Sound volume (0-1)"),
    ("DISPLAY", "fov", "FOV (60-120)"),
    ("DISPLAY", "vsync", "VSync: true/false"),

    ("TIME", "day_night_cycle", "Day/night cycle: true/false"),
    ("TIME", "day_length_minutes", "Real minutes per 24-hour day"),
    ("TIME", "start_time_hours", "New world start hour (0-23.99)"),

    ("ZOMBIES 1", "zombie_spawning", "Zombie spawning: true/false"),
    ("ZOMBIES 1", "zombie_notice_distance", "Notice distance"),
    ("ZOMBIES 1", "zombie_min_spawn_delay", "Minimum spawn delay"),
    ("ZOMBIES 1", "zombie_max_spawn_delay", "Maximum spawn delay"),
    ("ZOMBIES 1", "zombie_initial_delay", "Initial spawn delay"),
    ("ZOMBIES 1", "zombie_min_spawn_distance", "Minimum spawn distance"),
    ("ZOMBIES 1", "zombie_max_spawn_distance", "Maximum spawn distance"),
    ("ZOMBIES 1", "zombie_despawn_distance", "Despawn distance"),

    ("ZOMBIES 2", "zombie_spawn_attempts", "Spawn attempts"),
    ("ZOMBIES 2", "zombie_max_count", "Maximum zombies"),
    ("ZOMBIES 2", "zombie_max_health", "Zombie health"),
    ("ZOMBIES 2", "zombie_speed", "Zombie speed"),
    ("ZOMBIES 2", "zombie_stop_distance", "Stop distance"),
    ("ZOMBIES 2", "zombie_step_height", "Step height"),
    ("ZOMBIES 2", "zombie_jump_speed", "Jump speed"),
    ("ZOMBIES 2", "zombie_gravity", "Zombie gravity"),

    ("ZOMBIES 3", "zombie_max_jump_height", "Maximum jump height"),
    ("ZOMBIES 3", "zombie_knockback", "Hit knockback"),
    ("ZOMBIES 3", "zombie_attack_damage", "Attack damage (hearts)"),
    ("ZOMBIES 3", "zombie_attack_interval", "Attack interval"),
    ("ZOMBIES 3", "zombie_head_texture", "Head texture"),
    ("ZOMBIES 3", "zombie_head_top_texture", "Head top texture"),
    ("ZOMBIES 3", "zombie_body_texture", "Body texture"),
    ("ZOMBIES 3", "zombie_left_arm_texture", "Left arm texture"),
    ("ZOMBIES 3", "zombie_right_arm_texture", "Right arm texture"),
    ("ZOMBIES 3", "zombie_left_leg_texture", "Left leg texture"),
    ("ZOMBIES 3", "zombie_right_leg_texture", "Right leg texture"),
)

WORLD_SETTING_PAGES = tuple(dict.fromkeys(page for page, _, _ in WORLD_SETTING_FIELDS))


def _now_text() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _slugify(name: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", name.strip()).strip("_")
    return slug[:48] or "world"


def _world_folder(save_id: str) -> Path:
    return SAVES_DIR / save_id


def _metadata_path(save_id: str) -> Path:
    return _world_folder(save_id) / "metadata.json"


def _state_path(save_id: str) -> Path:
    return _world_folder(save_id) / "world_state.json"


def _ensure_saves_dir() -> None:
    SAVES_DIR.mkdir(parents=True, exist_ok=True)


def create_world_save(name: str, settings: WorldSettings) -> str:
    _ensure_saves_dir()
    settings.normalise()

    clean_name = name.strip() or "New World"
    base = _slugify(clean_name)
    save_id = base
    number = 2

    while _world_folder(save_id).exists():
        save_id = f"{base}_{number}"
        number += 1

    folder = _world_folder(save_id)
    folder.mkdir(parents=True, exist_ok=False)

    now = _now_text()
    metadata = {
        "version": SAVE_VERSION,
        "id": save_id,
        "name": clean_name,
        "created_at": now,
        "last_played": now,
        "settings": asdict(settings),
        "progress": {
            "tokens": settings.starting_tokens,
            "player_position": None,
            "math_streak": 0,
            "quest": {},
            "inventory": {
                "selected_index": 0,
                "slots": [],
            },
            "health": settings.max_health,
            "oxygen": settings.max_oxygen,
            "world_time_minutes": (
                settings.start_time_hours
                * 60.0
            ),
        },
    }

    _metadata_path(save_id).write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )

    return save_id


def list_world_saves() -> list[dict[str, Any]]:
    _ensure_saves_dir()
    result = []

    for folder in SAVES_DIR.iterdir():
        if not folder.is_dir():
            continue

        path = folder / "metadata.json"
        if not path.exists():
            continue

        try:
            metadata = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue

        metadata.setdefault("id", folder.name)
        metadata.setdefault("name", folder.name)
        metadata.setdefault("last_played", "")
        result.append(metadata)

    result.sort(key=lambda item: item.get("last_played", ""), reverse=True)
    return result


def load_world_save(save_id: str) -> dict[str, Any]:
    path = _metadata_path(save_id)
    if not path.exists():
        raise FileNotFoundError(f"Saved world does not exist: {save_id}")

    data = json.loads(path.read_text(encoding="utf-8"))
    data["settings"] = asdict(WorldSettings.from_dict(data.get("settings")))
    data.setdefault("progress", {})
    return data


def write_world_metadata(save_id: str, metadata: dict[str, Any]) -> None:
    folder = _world_folder(save_id)
    folder.mkdir(parents=True, exist_ok=True)
    metadata["id"] = save_id
    _metadata_path(save_id).write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )


def touch_last_played(save_id: str) -> None:
    metadata = load_world_save(save_id)
    metadata["last_played"] = _now_text()
    write_world_metadata(save_id, metadata)


def save_world_state(save_id: str, state: dict[str, Any]) -> None:
    folder = _world_folder(save_id)
    folder.mkdir(parents=True, exist_ok=True)
    _state_path(save_id).write_text(
        json.dumps(state, separators=(",", ":")),
        encoding="utf-8",
    )


def load_world_state(save_id: str) -> dict[str, Any] | None:
    path = _state_path(save_id)
    if not path.exists():
        return None

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def delete_world_save(save_id: str) -> None:
    folder = _world_folder(save_id)
    if folder.exists():
        shutil.rmtree(folder)
