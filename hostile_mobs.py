from __future__ import annotations

import math
import random

from ursina import (
    Entity,
    Vec3,
    color,
    destroy,
    invoke,
    load_texture,
    scene,
    time,
)

from blocks import BLOCKS, BlockType
from inventory import ItemType
from config import (
    ASSET_DIR,
    WATER_LEVEL,
    WORLD_HALF,
)


# =========================================================
# ZOMBIE TEXTURES
# =========================================================

ENTITY_TEXTURE_DIR = (
    ASSET_DIR
    / "entity"
)


def get_zombie_texture(
    filename: str,
):
    path = (
        ENTITY_TEXTURE_DIR
        / filename
    )

    if not path.exists():
        entity_missing = (
            ENTITY_TEXTURE_DIR
            / "missing.png"
        )

        block_missing = (
            ASSET_DIR
            / "textures"
            / "missing.png"
        )

        if entity_missing.exists():
            path = entity_missing
        elif block_missing.exists():
            path = block_missing
        else:
            raise FileNotFoundError(
                f"Zombie texture was not found: {path}"
            )

    texture = load_texture(
        path.name,
        folder=path.parent,
    )

    if texture is None:
        raise RuntimeError(
            f"Ursina could not load zombie texture: {path}"
        )

    texture.filtering = "nearest"
    texture.repeat = False

    return texture


# EDIT THESE FILENAMES.
# Files are loaded from: assets/entity/
# These values are NOT overridden by saved-world settings.
ZOMBIE_TEXTURES = {
    "HEAD": "missing.png",
    "HEAD_TOP": "missing.png",
    "BODY": "missing.png",
    "LEFT_ARM": "missing.png",
    "RIGHT_ARM": "missing.png",
    "LEFT_LEG": "missing.png",
    "RIGHT_LEG": "missing.png",
}


# =========================================================
# ZOMBIE SETTINGS
# =========================================================

# How many blocks away the zombie can notice the player.
ZOMBIE_NOTICE_DISTANCE = 18.0

ZOMBIE_MIN_SPAWN_DELAY = 7.0
ZOMBIE_MAX_SPAWN_DELAY = 13.0
ZOMBIE_INITIAL_DELAY = 3.0

ZOMBIE_MIN_SPAWN_DISTANCE = 10
ZOMBIE_MAX_SPAWN_DISTANCE = 24
ZOMBIE_DESPAWN_DISTANCE = 48
ZOMBIE_SPAWN_ATTEMPTS = 24
ZOMBIE_MAX_COUNT = 10

ZOMBIE_MAX_HEALTH = 3
ZOMBIE_SPEED = 2.2
ZOMBIE_STOP_DISTANCE = 1.15

# Small height differences can be stepped over normally.
# Full one-block obstacles make the zombie jump instead.
ZOMBIE_STEP_HEIGHT = 0.30

ZOMBIE_JUMP_SPEED = 5.4
ZOMBIE_GRAVITY = 14.0
ZOMBIE_MAX_JUMP_HEIGHT = 1.25

ZOMBIE_KNOCKBACK = 0.55
ZOMBIE_ATTACK_DAMAGE = 0.5
ZOMBIE_ATTACK_INTERVAL = 1.0

# Zombies lose this much health every second while touching lava.
ZOMBIE_LAVA_DAMAGE = 1
ZOMBIE_LAVA_DAMAGE_INTERVAL = 1.0

# At 12:00 or later, zombies despawn and new zombies stop spawning
# until the world clock wraps back to 00:00.
ZOMBIE_DAY_DESPAWN_HOUR = 12.0

ZOMBIE_SPAWNING_ENABLED = True


def apply_hostile_mob_settings(settings) -> None:
    global WATER_LEVEL
    global WORLD_HALF
    global ZOMBIE_NOTICE_DISTANCE
    global ZOMBIE_MIN_SPAWN_DELAY
    global ZOMBIE_MAX_SPAWN_DELAY
    global ZOMBIE_INITIAL_DELAY
    global ZOMBIE_MIN_SPAWN_DISTANCE
    global ZOMBIE_MAX_SPAWN_DISTANCE
    global ZOMBIE_DESPAWN_DISTANCE
    global ZOMBIE_SPAWN_ATTEMPTS
    global ZOMBIE_MAX_COUNT
    global ZOMBIE_MAX_HEALTH
    global ZOMBIE_SPEED
    global ZOMBIE_STOP_DISTANCE
    global ZOMBIE_STEP_HEIGHT
    global ZOMBIE_JUMP_SPEED
    global ZOMBIE_GRAVITY
    global ZOMBIE_MAX_JUMP_HEIGHT
    global ZOMBIE_KNOCKBACK
    global ZOMBIE_ATTACK_DAMAGE
    global ZOMBIE_ATTACK_INTERVAL
    global ZOMBIE_SPAWNING_ENABLED

    WATER_LEVEL = int(settings.water_level)
    WORLD_HALF = int(settings.world_size) // 2

    ZOMBIE_SPAWNING_ENABLED = bool(settings.zombie_spawning)
    ZOMBIE_NOTICE_DISTANCE = float(settings.zombie_notice_distance)
    ZOMBIE_MIN_SPAWN_DELAY = float(settings.zombie_min_spawn_delay)
    ZOMBIE_MAX_SPAWN_DELAY = float(settings.zombie_max_spawn_delay)
    ZOMBIE_INITIAL_DELAY = float(settings.zombie_initial_delay)
    ZOMBIE_MIN_SPAWN_DISTANCE = float(settings.zombie_min_spawn_distance)
    ZOMBIE_MAX_SPAWN_DISTANCE = float(settings.zombie_max_spawn_distance)
    ZOMBIE_DESPAWN_DISTANCE = float(settings.zombie_despawn_distance)
    ZOMBIE_SPAWN_ATTEMPTS = int(settings.zombie_spawn_attempts)
    ZOMBIE_MAX_COUNT = int(settings.zombie_max_count)
    ZOMBIE_MAX_HEALTH = int(settings.zombie_max_health)
    ZOMBIE_SPEED = float(settings.zombie_speed)
    ZOMBIE_STOP_DISTANCE = float(settings.zombie_stop_distance)
    ZOMBIE_STEP_HEIGHT = float(settings.zombie_step_height)
    ZOMBIE_JUMP_SPEED = float(settings.zombie_jump_speed)
    ZOMBIE_GRAVITY = float(settings.zombie_gravity)
    ZOMBIE_MAX_JUMP_HEIGHT = float(settings.zombie_max_jump_height)
    ZOMBIE_KNOCKBACK = float(settings.zombie_knockback)
    ZOMBIE_ATTACK_DAMAGE = float(settings.zombie_attack_damage)
    ZOMBIE_ATTACK_INTERVAL = float(settings.zombie_attack_interval)

    # Zombie texture filenames are intentionally NOT changed here.
    # The ZOMBIE_TEXTURES dictionary at the top of this file is the
    # single source of truth for entity textures. This prevents saved
    # world defaults such as "missing.png" from overwriting custom
    # filenames every time a world is loaded.


# =========================================================
# ZOMBIE
# =========================================================

class Zombie(Entity):
    def __init__(
        self,
        manager,
        position: Vec3,
    ):
        super().__init__(
            parent=manager.zombie_root,
            position=position,
        )

        self.manager = manager
        self.health = ZOMBIE_MAX_HEALTH
        self.alive = True
        self.attack_timer = 0.0
        self.lava_damage_timer = 0.0

        self.is_jumping = False
        self.vertical_velocity = 0.0
        self.jump_direction = Vec3(0, 0, 0)
        self.jump_start_y = self.y

        self.body_parts = []

        head_texture = get_zombie_texture(
            ZOMBIE_TEXTURES["HEAD"]
        )

        head_top_texture = get_zombie_texture(
            ZOMBIE_TEXTURES["HEAD_TOP"]
        )

        body_texture = get_zombie_texture(
            ZOMBIE_TEXTURES["BODY"]
        )

        left_arm_texture = get_zombie_texture(
            ZOMBIE_TEXTURES["LEFT_ARM"]
        )

        right_arm_texture = get_zombie_texture(
            ZOMBIE_TEXTURES["RIGHT_ARM"]
        )

        left_leg_texture = get_zombie_texture(
            ZOMBIE_TEXTURES["LEFT_LEG"]
        )

        right_leg_texture = get_zombie_texture(
            ZOMBIE_TEXTURES["RIGHT_LEG"]
        )

        # Taller legs make the zombie proportions closer to a
        # Minecraft-style humanoid and keep the feet on the ground.
        self.left_leg = self._part(
            left_leg_texture,
            scale=(0.24, 0.98, 0.26),
            position=(-0.17, 0.49, 0),
        )

        self.right_leg = self._part(
            right_leg_texture,
            scale=(0.24, 0.98, 0.26),
            position=(0.17, 0.49, 0),
        )

        self.body = self._part(
            body_texture,
            scale=(0.62, 0.92, 0.42),
            position=(0, 1.43, 0),
        )

        self.head = self._part(
            head_texture,
            scale=(0.58, 0.58, 0.58),
            position=(0, 2.18, 0),
        )

        # Separate top face so you can supply a dedicated head-top PNG.
        # HEAD remains the texture for the cube; HEAD_TOP is drawn just
        # above it and covers the visible top surface.
        self.head_top = Entity(
            parent=self,
            model="quad",
            texture=head_top_texture,
            color=color.white,
            scale=(0.58, 0.58),
            position=(0, 2.471, 0),
            rotation_x=90,
            double_sided=True,
        )

        self.body_parts.append(
            self.head_top
        )

        self.left_arm = self._part(
            left_arm_texture,
            scale=(0.20, 0.96, 0.20),
            position=(-0.43, 1.42, -0.18),
            rotation_x=-68,
        )

        self.right_arm = self._part(
            right_arm_texture,
            scale=(0.20, 0.96, 0.20),
            position=(0.43, 1.42, -0.18),
            rotation_x=-68,
        )

        # The invisible hitbox is what the player's attack ray hits.
        self.collider_entity = Entity(
            parent=self,
            model="cube",
            scale=(0.76, 2.50, 0.76),
            y=1.25,
            color=color.rgba32(
                255,
                255,
                255,
                0,
            ),
            collider="box",
        )

        self.collider_entity.mob = self
        self.collider_entity.zombie = self

    def _part(
        self,
        texture,
        scale,
        position,
        rotation_x=0,
    ):
        part = Entity(
            parent=self,
            model="cube",
            texture=texture,
            color=color.white,
            scale=scale,
            position=position,
            rotation_x=rotation_x,
        )

        self.body_parts.append(
            part
        )

        return part

    def horizontal_distance_to(
        self,
        position: Vec3,
    ) -> float:
        dx = self.x - position.x
        dz = self.z - position.z

        return math.sqrt(
            dx * dx
            + dz * dz
        )

    def _restore_hit_colour(
        self,
    ) -> None:
        if not self.alive:
            return

        for part in self.body_parts:
            part.color = color.white

    def take_damage(
        self,
        amount: int = 1,
        attacker_position: Vec3 | None = None,
    ) -> None:
        if not self.alive:
            return

        self.health -= max(
            1,
            int(amount),
        )

        for part in self.body_parts:
            part.color = color.rgb32(
                255,
                105,
                105,
            )

        invoke(
            self._restore_hit_colour,
            delay=0.10,
        )

        if attacker_position is not None:
            away = Vec3(
                self.x - attacker_position.x,
                0,
                self.z - attacker_position.z,
            )

            if away.length() > 0:
                away = away.normalized()

                knockback_position = Vec3(
                    self.position
                )

                knockback_position.x += (
                    away.x
                    * ZOMBIE_KNOCKBACK
                )

                knockback_position.z += (
                    away.z
                    * ZOMBIE_KNOCKBACK
                )

                if self._can_move_to(
                    knockback_position
                ):
                    self.position = (
                        self._grounded_position(
                            knockback_position
                        )
                    )

        if self.health <= 0:
            self.alive = False

            if attacker_position is not None:
                drop_count = random.randint(
                    1,
                    3,
                )

                added = 0

                for _ in range(
                    drop_count
                ):
                    if (
                        self.manager.game.inventory.add(
                            ItemType.ROTTEN_FLESH,
                            1,
                        )
                    ):
                        added += 1
                    else:
                        break

                if added > 0:
                    self.manager.game.ui.set_message(
                        (
                            "Zombie dropped "
                            + str(added)
                            + " Rotten Flesh."
                        )
                    )

                    self.manager.game.ui.update_hud()

            self.manager.remove_zombie(
                self
            )

    def _surface_height_at(
        self,
        x: float,
        z: float,
        maximum_surface_y: float,
    ) -> float:
        world = self.manager.game.world

        grid_x = round(
            x
        )

        grid_z = round(
            z
        )

        highest_block_y = int(
            math.floor(
                maximum_surface_y
                - 0.5
            )
        )

        for y in range(
            highest_block_y,
            -1,
            -1,
        ):
            block_type = world.get_block(
                (
                    grid_x,
                    y,
                    grid_z,
                )
            )

            if (
                block_type is not None
                and BLOCKS[
                    block_type
                ].solid
            ):
                return (
                    y
                    + 0.5
                )

        return (
            world.terrain_height(
                grid_x,
                grid_z,
            )
            + 0.5
        )

    def _ground_height_at(
        self,
        x: float,
        z: float,
    ) -> float:
        return self._surface_height_at(
            x,
            z,
            self.y
            + ZOMBIE_STEP_HEIGHT
            + 0.05,
        )

    def _grounded_position(
        self,
        position: Vec3,
    ) -> Vec3:
        return Vec3(
            position.x,
            self._ground_height_at(
                position.x,
                position.z,
            ),
            position.z,
        )

    def _inside_world(
        self,
        x: float,
        z: float,
    ) -> bool:
        grid_x = round(
            x
        )

        grid_z = round(
            z
        )

        return (
            -WORLD_HALF + 1
            <= grid_x
            < WORLD_HALF - 1
            and -WORLD_HALF + 1
            <= grid_z
            < WORLD_HALF - 1
        )

    def _space_clear_at(
        self,
        x: float,
        feet_y: float,
        z: float,
    ) -> bool:
        world = self.manager.game.world

        grid_x = round(
            x
        )

        grid_z = round(
            z
        )

        first_body_y = int(
            math.floor(
                feet_y
                + 0.5
            )
        )

        # The zombie is a little taller than two blocks visually,
        # so check three vertical cells to avoid walking through roofs.
        for y in (
            first_body_y,
            first_body_y + 1,
            first_body_y + 2,
        ):
            block_type = world.get_block(
                (
                    grid_x,
                    y,
                    grid_z,
                )
            )

            if block_type is None:
                continue

            if block_type in (
                BlockType.WATER,
                BlockType.LAVA,
            ):
                return False

            if BLOCKS[
                block_type
            ].solid:
                return False

        return True

    def _can_move_to(
        self,
        position: Vec3,
    ) -> bool:
        if not self._inside_world(
            position.x,
            position.z,
        ):
            return False

        ground_y = (
            self._ground_height_at(
                position.x,
                position.z,
            )
        )

        if abs(
            ground_y - self.y
        ) > ZOMBIE_STEP_HEIGHT:
            return False

        return self._space_clear_at(
            position.x,
            ground_y,
            position.z,
        )

    def _jump_surface_height(
        self,
        position: Vec3,
    ) -> float:
        return self._surface_height_at(
            position.x,
            position.z,
            self.jump_start_y
            + ZOMBIE_MAX_JUMP_HEIGHT
            + 0.05,
        )

    def _can_jump_towards(
        self,
        position: Vec3,
    ) -> bool:
        if not self._inside_world(
            position.x,
            position.z,
        ):
            return False

        surface_y = (
            self._surface_height_at(
                position.x,
                position.z,
                self.y
                + ZOMBIE_MAX_JUMP_HEIGHT
                + 0.05,
            )
        )

        height_difference = (
            surface_y
            - self.y
        )

        if not (
            ZOMBIE_STEP_HEIGHT
            < height_difference
            <= ZOMBIE_MAX_JUMP_HEIGHT
        ):
            return False

        return self._space_clear_at(
            position.x,
            surface_y,
            position.z,
        )

    def _start_jump(
        self,
        direction: Vec3,
    ) -> None:
        if self.is_jumping:
            return

        if direction.length() == 0:
            return

        self.is_jumping = True

        self.vertical_velocity = (
            ZOMBIE_JUMP_SPEED
        )

        self.jump_direction = Vec3(
            direction.x,
            0,
            direction.z,
        ).normalized()

        self.jump_start_y = self.y

    def _update_jump(
        self,
    ) -> None:
        if not self.is_jumping:
            return

        horizontal_step = (
            self.jump_direction
            * ZOMBIE_SPEED
            * time.dt
        )

        target_x = (
            self.x
            + horizontal_step.x
        )

        target_z = (
            self.z
            + horizontal_step.z
        )

        if self._inside_world(
            target_x,
            target_z,
        ):
            jump_surface = (
                self._surface_height_at(
                    target_x,
                    target_z,
                    self.jump_start_y
                    + ZOMBIE_MAX_JUMP_HEIGHT
                    + 0.05,
                )
            )

            if (
                jump_surface
                <= self.jump_start_y
                + ZOMBIE_MAX_JUMP_HEIGHT
                and self._space_clear_at(
                    target_x,
                    jump_surface,
                    target_z,
                )
            ):
                self.x = target_x
                self.z = target_z

        self.vertical_velocity -= (
            ZOMBIE_GRAVITY
            * time.dt
        )

        self.y += (
            self.vertical_velocity
            * time.dt
        )

        landing_y = (
            self._surface_height_at(
                self.x,
                self.z,
                self.jump_start_y
                + ZOMBIE_MAX_JUMP_HEIGHT
                + 0.05,
            )
        )

        if (
            self.vertical_velocity <= 0
            and self.y <= landing_y
        ):
            self.y = landing_y

            self.vertical_velocity = 0.0

            self.is_jumping = False

            self.jump_direction = Vec3(
                0,
                0,
                0,
            )

    def _try_move(
        self,
        movement: Vec3,
    ) -> None:
        if movement.length() == 0:
            return

        target = Vec3(
            self.position
            + movement
        )

        if self._can_move_to(
            target
        ):
            self.position = (
                self._grounded_position(
                    target
                )
            )
            return

        if self._can_jump_towards(
            target
        ):
            self._start_jump(
                movement
            )
            return

        # If a diagonal move is blocked, try sliding on X or Z.
        x_only = Vec3(
            self.x + movement.x,
            self.y,
            self.z,
        )

        if self._can_move_to(
            x_only
        ):
            self.position = (
                self._grounded_position(
                    x_only
                )
            )
            return

        if self._can_jump_towards(
            x_only
        ):
            self._start_jump(
                Vec3(
                    movement.x,
                    0,
                    0,
                )
            )
            return

        z_only = Vec3(
            self.x,
            self.y,
            self.z + movement.z,
        )

        if self._can_move_to(
            z_only
        ):
            self.position = (
                self._grounded_position(
                    z_only
                )
            )
            return

        if self._can_jump_towards(
            z_only
        ):
            self._start_jump(
                Vec3(
                    0,
                    0,
                    movement.z,
                )
            )

    def _body_is_in_lava(
        self,
    ) -> bool:
        world = self.manager.game.world

        if world is None:
            return False

        # Check feet/body cells so a zombie touching a lava block
        # takes damage even if only its lower half is submerged.
        x = round(
            self.x
        )

        z = round(
            self.z
        )

        feet_y = int(
            math.floor(
                self.y + 0.5
            )
        )

        body_y = int(
            math.floor(
                self.y + 1.2
            )
        )

        return (
            world.get_block(
                (
                    x,
                    feet_y,
                    z,
                )
            )
            == BlockType.LAVA
            or world.get_block(
                (
                    x,
                    body_y,
                    z,
                )
            )
            == BlockType.LAVA
        )

    def _update_lava_damage(
        self,
    ) -> None:
        if not self._body_is_in_lava():
            self.lava_damage_timer = 0.0
            return

        self.lava_damage_timer += (
            time.dt
        )

        while (
            self.lava_damage_timer
            >= ZOMBIE_LAVA_DAMAGE_INTERVAL
        ):
            self.lava_damage_timer -= (
                ZOMBIE_LAVA_DAMAGE_INTERVAL
            )

            self.take_damage(
                ZOMBIE_LAVA_DAMAGE
            )

            if not self.alive:
                return

    def chase_player(
        self,
    ) -> None:
        if not self.alive:
            return

        game = self.manager.game
        player = game.player

        if (
            player is None
            or not player.enabled
        ):
            return

        dx = player.x - self.x
        dz = player.z - self.z

        distance = math.sqrt(
            dx * dx
            + dz * dz
        )

        # Ignore the player until they are close enough to be noticed.
        if distance > ZOMBIE_NOTICE_DISTANCE:
            return

        if distance <= 0:
            return

        if distance <= ZOMBIE_STOP_DISTANCE:
            if (
                abs(
                    player.y - self.y
                ) <= 2.5
                and self.attack_timer <= 0
            ):
                player.take_damage(
                    ZOMBIE_ATTACK_DAMAGE,
                    source="zombie",
                )

                self.attack_timer = (
                    ZOMBIE_ATTACK_INTERVAL
                )

            return

        direction = Vec3(
            dx,
            0,
            dz,
        ).normalized()

        # Face the player.
        self.rotation_y = (
            math.degrees(
                math.atan2(
                    direction.x,
                    direction.z,
                )
            )
        )

        movement = (
            direction
            * ZOMBIE_SPEED
            * time.dt
        )

        self._try_move(
            movement
        )

    def update(
        self,
    ) -> None:
        if not self.alive:
            return

        if not self.manager._game_is_active():
            return

        if self.attack_timer > 0:
            self.attack_timer = max(
                0.0,
                self.attack_timer
                - time.dt,
            )

        self._update_lava_damage()

        if not self.alive:
            return

        if self.is_jumping:
            self._update_jump()
            return

        self.chase_player()


# =========================================================
# ZOMBIE MANAGER
# =========================================================

class HostileMobManager(Entity):
    def __init__(
        self,
        game,
    ):
        super().__init__(
            parent=scene,
            eternal=True,
        )

        self.game = game

        self.zombie_root = Entity(
            parent=scene,
            enabled=False,
        )

        self.zombies: list[
            Zombie
        ] = []

        self.spawn_timer = (
            ZOMBIE_INITIAL_DELAY
        )

        self.cleanup_timer = 1.0
        self.was_in_game = False

    def _daytime_despawn_active(
        self,
    ) -> bool:
        day_night = getattr(
            self.game,
            "day_night",
            None,
        )

        if day_night is None:
            return False

        hour = (
            float(
                day_night.world_minutes
            )
            / 60.0
        )

        return (
            hour
            >= ZOMBIE_DAY_DESPAWN_HOUR
        )

    def _game_is_active(
        self,
    ) -> bool:
        return (
            self.game.in_game
            and self.game.world
            is not None
            and self.game.player
            is not None
            and self.game.player.enabled
        )

    def _reset_spawn_timer(
        self,
    ) -> None:
        self.spawn_timer = random.uniform(
            ZOMBIE_MIN_SPAWN_DELAY,
            ZOMBIE_MAX_SPAWN_DELAY,
        )

    def _random_spawn_position(
        self,
    ) -> Vec3 | None:
        player = self.game.player
        world = self.game.world

        if (
            player is None
            or world is None
        ):
            return None

        for _ in range(
            ZOMBIE_SPAWN_ATTEMPTS
        ):
            angle = random.uniform(
                0,
                math.tau,
            )

            distance = random.uniform(
                ZOMBIE_MIN_SPAWN_DISTANCE,
                ZOMBIE_MAX_SPAWN_DISTANCE,
            )

            x = round(
                player.x
                + math.cos(angle)
                * distance
            )

            z = round(
                player.z
                + math.sin(angle)
                * distance
            )

            x = max(
                -WORLD_HALF + 2,
                min(
                    WORLD_HALF - 2,
                    x,
                ),
            )

            z = max(
                -WORLD_HALF + 2,
                min(
                    WORLD_HALF - 2,
                    z,
                ),
            )

            terrain_y = world.terrain_height(
                x,
                z,
            )

            if terrain_y <= WATER_LEVEL:
                continue

            surface_block = world.get_block(
                (
                    x,
                    terrain_y,
                    z,
                )
            )

            if (
                surface_block is None
                or surface_block
                in (
                    BlockType.WATER,
                    BlockType.LAVA,
                )
            ):
                continue

            spawn_position = Vec3(
                x,
                terrain_y + 0.5,
                z,
            )

            if (
                (
                    spawn_position
                    - player.position
                ).length()
                < ZOMBIE_MIN_SPAWN_DISTANCE
            ):
                continue

            return spawn_position

        return None

    def spawn_zombie(
        self,
    ) -> Zombie | None:
        if len(
            self.zombies
        ) >= ZOMBIE_MAX_COUNT:
            return None

        position = (
            self._random_spawn_position()
        )

        if position is None:
            return None

        zombie = Zombie(
            self,
            position,
        )

        self.zombies.append(
            zombie
        )

        return zombie

    def remove_zombie(
        self,
        zombie: Zombie,
    ) -> None:
        if zombie in self.zombies:
            self.zombies.remove(
                zombie
            )

        destroy(
            zombie
        )

    def clear(
        self,
    ) -> None:
        for zombie in list(
            self.zombies
        ):
            self.remove_zombie(
                zombie
            )

    def _cleanup_far_zombies(
        self,
    ) -> None:
        player = self.game.player

        if player is None:
            return

        for zombie in list(
            self.zombies
        ):
            if (
                zombie.horizontal_distance_to(
                    player.position
                )
                > ZOMBIE_DESPAWN_DISTANCE
            ):
                self.remove_zombie(
                    zombie
                )

    def update(
        self,
    ) -> None:
        active = (
            self._game_is_active()
        )

        self.zombie_root.enabled = (
            active
        )

        if not active:
            self.was_in_game = False
            return

        if self._daytime_despawn_active():
            if self.zombies:
                self.clear()

            self.spawn_timer = (
                ZOMBIE_INITIAL_DELAY
            )

            return

        if not self.was_in_game:
            self.spawn_timer = (
                ZOMBIE_INITIAL_DELAY
            )

            self.cleanup_timer = 1.0
            self.was_in_game = True

        self.spawn_timer -= (
            time.dt
        )

        if self.spawn_timer <= 0:
            if ZOMBIE_SPAWNING_ENABLED:
                self.spawn_zombie()

            self._reset_spawn_timer()

        self.cleanup_timer -= (
            time.dt
        )

        if self.cleanup_timer <= 0:
            self.cleanup_timer = 1.0
            self._cleanup_far_zombies()



# =========================================================
# BACKWARD COMPATIBILITY
# =========================================================

ZombieManager = HostileMobManager
apply_zombie_settings = apply_hostile_mob_settings
