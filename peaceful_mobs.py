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
# PEACEFUL MOB TEXTURES
# =========================================================

ENTITY_TEXTURE_DIR = (
    ASSET_DIR
    / "entity"
)


# =========================================================
# SHEEP UV ATLAS
# =========================================================
#
# The uploaded sheep texture is a full 1200x1200 UV layout.
# Keep the filename here editable.
#
SHEEP_TEXTURES = {
    "ATLAS": "sheep.png",
}


SHEEP_ATLAS_WIDTH = 1200
SHEEP_ATLAS_HEIGHT = 1200


def get_peaceful_mob_texture(
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
                f"Peaceful mob texture was not found: {path}"
            )

    texture = load_texture(
        path.name,
        folder=path.parent,
    )

    if texture is None:
        raise RuntimeError(
            f"Ursina could not load peaceful mob texture: {path}"
        )

    texture.filtering = "nearest"
    texture.repeat = False

    return texture


def _uv_rect(
    left: float,
    top: float,
    right: float,
    bottom: float,
):
    """
    Convert image pixel coordinates into Ursina/Panda UV coordinates.

    Image coordinates start at the top-left.
    UV coordinates start at the bottom-left.
    """
    u0 = (
        float(left)
        / SHEEP_ATLAS_WIDTH
    )

    u1 = (
        float(right)
        / SHEEP_ATLAS_WIDTH
    )

    v0 = (
        1.0
        - float(bottom)
        / SHEEP_ATLAS_HEIGHT
    )

    v1 = (
        1.0
        - float(top)
        / SHEEP_ATLAS_HEIGHT
    )

    return (
        (u0, v0),
        (u1, v0),
        (u1, v1),
        (u0, v1),
    )


def _make_uv_cuboid(
    face_rects,
):
    """
    Build a cube mesh whose six faces each point at a different rectangle
    in the full sheep atlas.
    """
    from ursina import Mesh

    vertices = []
    triangles = []
    uvs = []

    # Unit cube. Entity.scale controls its final dimensions.
    face_vertices = {
        # Sheep faces toward -Z.
        "FRONT": (
            (-0.5, -0.5, -0.5),
            (0.5, -0.5, -0.5),
            (0.5, 0.5, -0.5),
            (-0.5, 0.5, -0.5),
        ),

        "BACK": (
            (0.5, -0.5, 0.5),
            (-0.5, -0.5, 0.5),
            (-0.5, 0.5, 0.5),
            (0.5, 0.5, 0.5),
        ),

        "LEFT": (
            (-0.5, -0.5, 0.5),
            (-0.5, -0.5, -0.5),
            (-0.5, 0.5, -0.5),
            (-0.5, 0.5, 0.5),
        ),

        "RIGHT": (
            (0.5, -0.5, -0.5),
            (0.5, -0.5, 0.5),
            (0.5, 0.5, 0.5),
            (0.5, 0.5, -0.5),
        ),

        "TOP": (
            (-0.5, 0.5, -0.5),
            (0.5, 0.5, -0.5),
            (0.5, 0.5, 0.5),
            (-0.5, 0.5, 0.5),
        ),

        "BOTTOM": (
            (-0.5, -0.5, 0.5),
            (0.5, -0.5, 0.5),
            (0.5, -0.5, -0.5),
            (-0.5, -0.5, -0.5),
        ),
    }

    for face_name in (
        "FRONT",
        "BACK",
        "LEFT",
        "RIGHT",
        "TOP",
        "BOTTOM",
    ):
        base_index = len(
            vertices
        )

        vertices.extend(
            face_vertices[
                face_name
            ]
        )

        left, top, right, bottom = (
            face_rects[
                face_name
            ]
        )

        uvs.extend(
            _uv_rect(
                left,
                top,
                right,
                bottom,
            )
        )

        triangles.extend(
            (
                base_index + 0,
                base_index + 1,
                base_index + 2,

                base_index + 0,
                base_index + 2,
                base_index + 3,
            )
        )

    return Mesh(
        vertices=vertices,
        triangles=triangles,
        uvs=uvs,
        mode="triangle",
        static=True,
    )


# =========================================================
# UV REGIONS FROM THE USER'S SHEEP ATLAS
# =========================================================

# Head skin / face.
# The eye-and-mouth face is deliberately mapped to FRONT.
SHEEP_HEAD_UVS = {
    "TOP": (
        417,
        784,
        575,
        929,
    ),

    "LEFT": (
        131,
        929,
        282,
        1061,
    ),

    "FRONT": (
        282,
        929,
        424,
        1061,
    ),

    "RIGHT": (
        424,
        929,
        575,
        1061,
    ),

    "BACK": (
        0,
        1061,
        132,
        1199,
    ),

    "BOTTOM": (
        132,
        1061,
        286,
        1199,
    ),
}


# White wool body.
SHEEP_BODY_UVS = {
    "LEFT": (
        605,
        925,
        697,
        1016,
    ),

    "FRONT": (
        697,
        925,
        788,
        1016,
    ),

    "RIGHT": (
        788,
        925,
        903,
        1016,
    ),

    "BACK": (
        903,
        925,
        1088,
        1016,
    ),

    "TOP": (
        903,
        810,
        1180,
        925,
    ),

    "BOTTOM": (
        788,
        1016,
        904,
        1198,
    ),
}


def _leg_uvs(
    left,
    top,
    right,
    bottom,
):
    """
    Convert one of the four brown leg UV islands into six face rectangles.
    All four leg islands use the same cross-style arrangement.
    """
    width = (
        right
        - left
    )

    height = (
        bottom
        - top
    )

    # Relative boundaries measured from the supplied atlas.
    x0 = left + width * 0.015
    x1 = left + width * 0.255
    x2 = left + width * 0.505
    x3 = left + width * 0.735
    x4 = left + width * 0.995

    y0 = top
    y1 = top + height * 0.34
    y2 = top + height * 0.66
    y3 = bottom

    return {
        "TOP": (
            x0,
            y0,
            x1,
            y1,
        ),

        "LEFT": (
            x0,
            y1,
            x1,
            y2,
        ),

        "FRONT": (
            x1,
            y1,
            x2,
            y2,
        ),

        "RIGHT": (
            x2,
            y1,
            x3,
            y2,
        ),

        "BACK": (
            x3,
            y1,
            x4,
            y2,
        ),

        "BOTTOM": (
            x0,
            y2,
            x1,
            y3,
        ),
    }


# Four separate brown leg islands from the uploaded image.
SHEEP_LEG_UVS = (
    _leg_uvs(
        332,
        143,
        562,
        320,
    ),

    _leg_uvs(
        937,
        59,
        1166,
        237,
    ),

    _leg_uvs(
        936,
        321,
        1167,
        498,
    ),

    _leg_uvs(
        938,
        584,
        1167,
        760,
    ),
)


SHEEP_HEAD_MODEL = (
    _make_uv_cuboid(
        SHEEP_HEAD_UVS
    )
)

SHEEP_BODY_MODEL = (
    _make_uv_cuboid(
        SHEEP_BODY_UVS
    )
)

SHEEP_LEG_MODELS = tuple(
    _make_uv_cuboid(
        uv_data
    )
    for uv_data
    in SHEEP_LEG_UVS
)


# =========================================================
# PEACEFUL MOB SETTINGS
# =========================================================

PEACEFUL_MOB_SPAWNING_ENABLED = True

SHEEP_INITIAL_SPAWN_DELAY = 2.0
SHEEP_MIN_SPAWN_DELAY = 8.0
SHEEP_MAX_SPAWN_DELAY = 16.0

SHEEP_MIN_SPAWN_DISTANCE = 7.0
SHEEP_MAX_SPAWN_DISTANCE = 22.0
SHEEP_DESPAWN_DISTANCE = 55.0
SHEEP_SPAWN_ATTEMPTS = 30
SHEEP_MAX_COUNT = 8

SHEEP_MAX_HEALTH = 4
SHEEP_SPEED = 1.15

# How long a sheep keeps walking in roughly the same direction.
SHEEP_MIN_WANDER_TIME = 1.5
SHEEP_MAX_WANDER_TIME = 4.5

# Chance to stop instead of choosing a new walking direction.
SHEEP_IDLE_CHANCE = 0.30

# How long an idle sheep waits before choosing again.
SHEEP_MIN_IDLE_TIME = 1.0
SHEEP_MAX_IDLE_TIME = 3.5

SHEEP_STEP_HEIGHT = 0.55
SHEEP_MAX_DROP_HEIGHT = 1.40

SHEEP_KNOCKBACK = 0.45

# Sheep take one point of health every second while touching lava.
SHEEP_LAVA_DAMAGE = 1
SHEEP_LAVA_DAMAGE_INTERVAL = 1.0


def apply_peaceful_mob_settings(
    settings,
) -> None:
    """
    Sync world-sized values when a saved world is loaded.

    Sheep-specific tuning currently stays in the editable constants above.
    """
    global WATER_LEVEL
    global WORLD_HALF

    WATER_LEVEL = int(
        settings.water_level
    )

    WORLD_HALF = (
        int(
            settings.world_size
        )
        // 2
    )


# =========================================================
# SHEEP
# =========================================================

class Sheep(Entity):
    def __init__(
        self,
        manager,
        position: Vec3,
    ):
        super().__init__(
            parent=manager.mob_root,
            position=position,
        )

        self.manager = manager

        self.health = (
            SHEEP_MAX_HEALTH
        )

        self.alive = True

        self.lava_damage_timer = 0.0

        self.wander_timer = 0.0

        self.wander_direction = Vec3(
            0,
            0,
            0,
        )

        self.body_parts = []

        sheep_texture = (
            get_peaceful_mob_texture(
                SHEEP_TEXTURES[
                    "ATLAS"
                ]
            )
        )

        # -----------------------------------------------------
        # BODY
        # -----------------------------------------------------

        self.body = self._part(
            sheep_texture,
            SHEEP_BODY_MODEL,
            scale=(
                1.15,
                0.78,
                0.62,
            ),
            position=(
                0,
                0.92,
                0,
            ),
        )

        self.head = self._part(
            sheep_texture,
            SHEEP_HEAD_MODEL,
            scale=(
                0.52,
                0.56,
                0.50,
            ),
            position=(
                0,
                1.08,
                -0.66,
            ),
        )

        # -----------------------------------------------------
        # LEGS
        # -----------------------------------------------------

        leg_scale = (
            0.20,
            0.70,
            0.20,
        )

        self.front_left_leg = self._part(
            sheep_texture,
            SHEEP_LEG_MODELS[0],
            scale=leg_scale,
            position=(
                -0.38,
                0.36,
                -0.33,
            ),
        )

        self.front_right_leg = self._part(
            sheep_texture,
            SHEEP_LEG_MODELS[1],
            scale=leg_scale,
            position=(
                0.38,
                0.36,
                -0.33,
            ),
        )

        self.back_left_leg = self._part(
            sheep_texture,
            SHEEP_LEG_MODELS[2],
            scale=leg_scale,
            position=(
                -0.38,
                0.36,
                0.33,
            ),
        )

        self.back_right_leg = self._part(
            sheep_texture,
            SHEEP_LEG_MODELS[3],
            scale=leg_scale,
            position=(
                0.38,
                0.36,
                0.33,
            ),
        )

        # -----------------------------------------------------
        # HITBOX
        # -----------------------------------------------------

        self.collider_entity = Entity(
            parent=self,
            model="cube",
            scale=(
                1.20,
                1.55,
                0.92,
            ),
            y=0.78,
            color=color.rgba32(
                255,
                255,
                255,
                0,
            ),
            collider="box",
        )

        # Generic mob marker used by player.py.
        self.collider_entity.mob = self
        self.collider_entity.sheep = self

        self._choose_new_wander()

    def _part(
        self,
        texture,
        model,
        scale,
        position,
    ):
        part = Entity(
            parent=self,
            model=model,
            texture=texture,
            color=color.white,
            scale=scale,
            position=position,
            double_sided=True,
        )

        self.body_parts.append(
            part
        )

        return part

    # =========================================================
    # DAMAGE
    # =========================================================

    def _restore_hit_colour(
        self,
    ) -> None:
        if not self.alive:
            return

        for part in (
            self.body_parts
        ):
            part.color = (
                color.white
            )

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

        for part in (
            self.body_parts
        ):
            part.color = (
                color.rgb32(
                    255,
                    105,
                    105,
                )
            )

        invoke(
            self._restore_hit_colour,
            delay=0.10,
        )

        if attacker_position is not None:
            away = Vec3(
                self.x
                - attacker_position.x,
                0,
                self.z
                - attacker_position.z,
            )

            if away.length() > 0:
                away = away.normalized()

                target = Vec3(
                    self.position
                )

                target.x += (
                    away.x
                    * SHEEP_KNOCKBACK
                )

                target.z += (
                    away.z
                    * SHEEP_KNOCKBACK
                )

                ground_y = (
                    self._surface_height_at(
                        target.x,
                        target.z,
                    )
                )

                if ground_y is not None:
                    target.y = ground_y

                    if self._space_clear_at(
                        target
                    ):
                        self.position = (
                            target
                        )

        if self.health <= 0:
            self.alive = False

            if attacker_position is not None:
                drop_count = random.randint(
                    1,
                    2,
                )

                added = 0

                for _ in range(
                    drop_count
                ):
                    if (
                        self.manager.game.inventory.add(
                            ItemType.WOOL,
                            1,
                        )
                    ):
                        added += 1
                    else:
                        break

                if added > 0:
                    self.manager.game.ui.set_message(
                        (
                            "Sheep dropped "
                            + str(added)
                            + " Wool."
                        )
                    )

                    self.manager.game.ui.update_hud()

            self.manager.remove_sheep(
                self
            )

    # =========================================================
    # TERRAIN
    # =========================================================

    def _surface_height_at(
        self,
        x: float,
        z: float,
    ) -> float | None:
        world = (
            self.manager.game.world
        )

        if world is None:
            return None

        grid_x = round(
            x
        )

        grid_z = round(
            z
        )

        if not (
            -WORLD_HALF
            <= grid_x
            < WORLD_HALF
            and -WORLD_HALF
            <= grid_z
            < WORLD_HALF
        ):
            return None

        # Search from just above the sheep downwards. This means sheep
        # can walk down into carved terrain such as a lava lake rather
        # than floating at the original terrain_height().
        start_y = max(
            1,
            int(
                math.floor(
                    self.y
                    + SHEEP_STEP_HEIGHT
                    + 1.5
                )
            ),
        )

        for y in range(
            start_y,
            -1,
            -1,
        ):
            block_type = (
                world.get_block(
                    (
                        grid_x,
                        y,
                        grid_z,
                    )
                )
            )

            if block_type is None:
                continue

            if BLOCKS[
                block_type
            ].solid:
                return (
                    y
                    + 0.5
                )

        return None

    def _space_clear_at(
        self,
        position: Vec3,
    ) -> bool:
        world = (
            self.manager.game.world
        )

        if world is None:
            return False

        x = round(
            position.x
        )

        z = round(
            position.z
        )

        feet_y = int(
            math.floor(
                position.y
                + 0.5
            )
        )

        # Two cells of body clearance.
        for y in (
            feet_y,
            feet_y + 1,
        ):
            block_type = (
                world.get_block(
                    (
                        x,
                        y,
                        z,
                    )
                )
            )

            if block_type is None:
                continue

            # Liquids do not block sheep movement. This lets a wandering
            # sheep enter lava and then take damage from it.
            if BLOCKS[
                block_type
            ].liquid:
                continue

            if BLOCKS[
                block_type
            ].solid:
                return False

        return True

    def _try_move(
        self,
        direction: Vec3,
    ) -> None:
        if direction.length() == 0:
            return

        step = (
            direction
            * SHEEP_SPEED
            * time.dt
        )

        target = Vec3(
            self.position
            + step
        )

        ground_y = (
            self._surface_height_at(
                target.x,
                target.z,
            )
        )

        if ground_y is None:
            self._choose_new_wander()
            return

        height_change = (
            ground_y
            - self.y
        )

        if (
            height_change
            > SHEEP_STEP_HEIGHT
            or height_change
            < -SHEEP_MAX_DROP_HEIGHT
        ):
            self._choose_new_wander()
            return

        target.y = (
            ground_y
        )

        if not self._space_clear_at(
            target
        ):
            self._choose_new_wander()
            return

        self.position = target

    # =========================================================
    # RANDOM WANDERING
    # =========================================================

    def _choose_new_wander(
        self,
    ) -> None:
        if random.random() < (
            SHEEP_IDLE_CHANCE
        ):
            self.wander_direction = Vec3(
                0,
                0,
                0,
            )

            self.wander_timer = (
                random.uniform(
                    SHEEP_MIN_IDLE_TIME,
                    SHEEP_MAX_IDLE_TIME,
                )
            )

            return

        angle = random.uniform(
            0,
            math.tau,
        )

        self.wander_direction = Vec3(
            math.sin(
                angle
            ),
            0,
            math.cos(
                angle
            ),
        )

        self.wander_timer = (
            random.uniform(
                SHEEP_MIN_WANDER_TIME,
                SHEEP_MAX_WANDER_TIME,
            )
        )

        self.rotation_y = (
            math.degrees(
                math.atan2(
                    self.wander_direction.x,
                    self.wander_direction.z,
                )
            )
        )

    def _update_wander(
        self,
    ) -> None:
        self.wander_timer -= (
            time.dt
        )

        if self.wander_timer <= 0:
            self._choose_new_wander()

        if (
            self.wander_direction.length()
            > 0
        ):
            self._try_move(
                self.wander_direction
            )

    # =========================================================
    # LAVA
    # =========================================================

    def _body_is_in_lava(
        self,
    ) -> bool:
        world = (
            self.manager.game.world
        )

        if world is None:
            return False

        centre_x = round(
            self.x
        )

        centre_z = round(
            self.z
        )

        min_y = int(
            math.floor(
                self.y
                + 0.5
            )
        )

        max_y = int(
            math.floor(
                self.y
                + 1.35
                + 0.5
            )
        )

        # Check the centre and four near-body horizontal cells.
        positions = (
            (
                centre_x,
                centre_z,
            ),
            (
                round(
                    self.x + 0.40
                ),
                centre_z,
            ),
            (
                round(
                    self.x - 0.40
                ),
                centre_z,
            ),
            (
                centre_x,
                round(
                    self.z + 0.35
                ),
            ),
            (
                centre_x,
                round(
                    self.z - 0.35
                ),
            ),
        )

        for x, z in positions:
            for y in range(
                min_y,
                max_y + 1,
            ):
                if (
                    world.get_block(
                        (
                            x,
                            y,
                            z,
                        )
                    )
                    == BlockType.LAVA
                ):
                    return True

        return False

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
            >= SHEEP_LAVA_DAMAGE_INTERVAL
        ):
            self.lava_damage_timer -= (
                SHEEP_LAVA_DAMAGE_INTERVAL
            )

            self.take_damage(
                SHEEP_LAVA_DAMAGE
            )

            if not self.alive:
                return

    # =========================================================
    # UPDATE
    # =========================================================

    def horizontal_distance_to(
        self,
        position: Vec3,
    ) -> float:
        dx = (
            self.x
            - position.x
        )

        dz = (
            self.z
            - position.z
        )

        return math.sqrt(
            dx * dx
            + dz * dz
        )

    def update(
        self,
    ) -> None:
        if not self.alive:
            return

        if not (
            self.manager
            ._game_is_active()
        ):
            return

        self._update_lava_damage()

        if not self.alive:
            return

        # Sheep never chase or attack the player.
        self._update_wander()


# =========================================================
# PEACEFUL MOB MANAGER
# =========================================================

class PeacefulMobManager(Entity):
    def __init__(
        self,
        game,
    ):
        super().__init__(
            parent=scene,
            eternal=True,
        )

        self.game = game

        self.mob_root = Entity(
            parent=scene,
            enabled=False,
        )

        self.sheep: list[
            Sheep
        ] = []

        self.spawn_timer = (
            SHEEP_INITIAL_SPAWN_DELAY
        )

        self.cleanup_timer = 1.0

        self.was_in_game = False

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
        self.spawn_timer = (
            random.uniform(
                SHEEP_MIN_SPAWN_DELAY,
                SHEEP_MAX_SPAWN_DELAY,
            )
        )

    def _random_spawn_position(
        self,
    ) -> Vec3 | None:
        player = (
            self.game.player
        )

        world = (
            self.game.world
        )

        if (
            player is None
            or world is None
        ):
            return None

        for _ in range(
            SHEEP_SPAWN_ATTEMPTS
        ):
            angle = random.uniform(
                0,
                math.tau,
            )

            distance = random.uniform(
                SHEEP_MIN_SPAWN_DISTANCE,
                SHEEP_MAX_SPAWN_DISTANCE,
            )

            x = round(
                player.x
                + math.cos(
                    angle
                )
                * distance
            )

            z = round(
                player.z
                + math.sin(
                    angle
                )
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

            terrain_y = (
                world.terrain_height(
                    x,
                    z,
                )
            )

            if terrain_y <= (
                WATER_LEVEL
            ):
                continue

            surface_block = (
                world.get_block(
                    (
                        x,
                        terrain_y,
                        z,
                    )
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

            if not BLOCKS[
                surface_block
            ].solid:
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
                < SHEEP_MIN_SPAWN_DISTANCE
            ):
                continue

            return (
                spawn_position
            )

        return None

    def spawn_sheep(
        self,
    ) -> Sheep | None:
        if not (
            PEACEFUL_MOB_SPAWNING_ENABLED
        ):
            return None

        if len(
            self.sheep
        ) >= SHEEP_MAX_COUNT:
            return None

        position = (
            self._random_spawn_position()
        )

        if position is None:
            return None

        sheep = Sheep(
            self,
            position,
        )

        self.sheep.append(
            sheep
        )

        return sheep

    def remove_sheep(
        self,
        sheep: Sheep,
    ) -> None:
        if sheep in self.sheep:
            self.sheep.remove(
                sheep
            )

        destroy(
            sheep
        )

    def clear(
        self,
    ) -> None:
        for sheep in list(
            self.sheep
        ):
            self.remove_sheep(
                sheep
            )

    def _cleanup_far_sheep(
        self,
    ) -> None:
        player = (
            self.game.player
        )

        if player is None:
            return

        for sheep in list(
            self.sheep
        ):
            if (
                sheep.horizontal_distance_to(
                    player.position
                )
                > SHEEP_DESPAWN_DISTANCE
            ):
                self.remove_sheep(
                    sheep
                )

    def update(
        self,
    ) -> None:
        active = (
            self._game_is_active()
        )

        self.mob_root.enabled = (
            active
        )

        if not active:
            self.was_in_game = False
            return

        if not self.was_in_game:
            self.spawn_timer = (
                SHEEP_INITIAL_SPAWN_DELAY
            )

            self.cleanup_timer = 1.0

            self.was_in_game = True

        self.spawn_timer -= (
            time.dt
        )

        if (
            self.spawn_timer <= 0
        ):
            self.spawn_sheep()
            self._reset_spawn_timer()

        self.cleanup_timer -= (
            time.dt
        )

        if self.cleanup_timer <= 0:
            self.cleanup_timer = 1.0

            self._cleanup_far_sheep()
