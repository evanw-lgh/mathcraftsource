from __future__ import annotations

import math
import random
from collections import defaultdict, deque
from typing import Dict, Tuple

from ursina import Entity, Mesh, Vec3, color, destroy, time

from blocks import BLOCKS, BlockType
from config import (
    CHUNK_SIZE,
    MAX_TERRAIN_HEIGHT,
    TREE_CHANCE,
    WATER_LEVEL,
    WORLD_HALF,
)
from textures import (
    SPECIAL_BLOCK_TEXTURES,
    get_atlas_texture,
    get_face_uvs,
    get_texture,
)

GridPos = Tuple[int, int, int]
ChunkPos = Tuple[int, int]

# Actual block-to-block water flow.
# 0 = source water, 1..7 = progressively weaker flowing water.
WATER_MAX_FLOW_LEVEL = 7
WATER_FLOW_TICK = 0.12
WATER_UPDATES_PER_TICK = 24
WATER_TEXTURE_FLOW_U = 0.045
WATER_TEXTURE_FLOW_V = 0.018

WORLD_SEED = 7
TERRAIN_BASE_HEIGHT = 3
TERRAIN_X_FREQUENCY = 0.34
TERRAIN_X_AMPLITUDE = 1.3
TERRAIN_Z_FREQUENCY = 0.29
TERRAIN_Z_AMPLITUDE = 1.1
TERRAIN_DETAIL_FREQUENCY = 0.17
TERRAIN_DETAIL_AMPLITUDE = 0.8
TREE_MIN_HEIGHT = 3
TREE_MAX_HEIGHT = 4

LAVA_LAKE_COUNT = 4
LAVA_LAKE_MIN_RADIUS = 2
LAVA_LAKE_MAX_RADIUS = 4
LAVA_SAFE_SPAWN_RADIUS = 7
LAVA_TEXTURE_FLOW_U = 0.018
LAVA_TEXTURE_FLOW_V = 0.009


def apply_world_settings(settings) -> None:
    global CHUNK_SIZE
    global MAX_TERRAIN_HEIGHT
    global TREE_CHANCE
    global WATER_LEVEL
    global WORLD_HALF
    global WATER_MAX_FLOW_LEVEL
    global WATER_FLOW_TICK
    global WATER_UPDATES_PER_TICK
    global WATER_TEXTURE_FLOW_U
    global WATER_TEXTURE_FLOW_V
    global WORLD_SEED
    global TERRAIN_BASE_HEIGHT
    global TERRAIN_X_FREQUENCY
    global TERRAIN_X_AMPLITUDE
    global TERRAIN_Z_FREQUENCY
    global TERRAIN_Z_AMPLITUDE
    global TERRAIN_DETAIL_FREQUENCY
    global TERRAIN_DETAIL_AMPLITUDE
    global TREE_MIN_HEIGHT
    global TREE_MAX_HEIGHT
    global LAVA_LAKE_COUNT
    global LAVA_LAKE_MIN_RADIUS
    global LAVA_LAKE_MAX_RADIUS
    global LAVA_SAFE_SPAWN_RADIUS
    global LAVA_TEXTURE_FLOW_U
    global LAVA_TEXTURE_FLOW_V

    CHUNK_SIZE = int(settings.chunk_size)
    MAX_TERRAIN_HEIGHT = int(settings.max_terrain_height)
    TREE_CHANCE = float(settings.tree_chance)
    WATER_LEVEL = int(settings.water_level)
    WORLD_HALF = int(settings.world_size) // 2

    WATER_MAX_FLOW_LEVEL = int(settings.water_max_flow_level)
    WATER_FLOW_TICK = float(settings.water_flow_tick)
    WATER_UPDATES_PER_TICK = int(settings.water_updates_per_tick)
    WATER_TEXTURE_FLOW_U = float(settings.water_texture_flow_u)
    WATER_TEXTURE_FLOW_V = float(settings.water_texture_flow_v)

    WORLD_SEED = int(settings.world_seed)
    TERRAIN_BASE_HEIGHT = int(settings.terrain_base_height)
    TERRAIN_X_FREQUENCY = float(settings.terrain_x_frequency)
    TERRAIN_X_AMPLITUDE = float(settings.terrain_x_amplitude)
    TERRAIN_Z_FREQUENCY = float(settings.terrain_z_frequency)
    TERRAIN_Z_AMPLITUDE = float(settings.terrain_z_amplitude)
    TERRAIN_DETAIL_FREQUENCY = float(settings.terrain_detail_frequency)
    TERRAIN_DETAIL_AMPLITUDE = float(settings.terrain_detail_amplitude)
    TREE_MIN_HEIGHT = int(settings.tree_min_height)
    TREE_MAX_HEIGHT = int(settings.tree_max_height)

    LAVA_LAKE_COUNT = int(settings.lava_lake_count)
    LAVA_LAKE_MIN_RADIUS = int(settings.lava_lake_min_radius)
    LAVA_LAKE_MAX_RADIUS = int(settings.lava_lake_max_radius)
    LAVA_SAFE_SPAWN_RADIUS = int(settings.lava_safe_spawn_radius)
    LAVA_TEXTURE_FLOW_U = float(settings.lava_texture_flow_u)
    LAVA_TEXTURE_FLOW_V = float(settings.lava_texture_flow_v)

# Face order:
# top, north, south, east, west, bottom
FACE_DATA = (
    (
        (0, 1, 0),
        (0, 1, 0),
        (
            (-0.5, 0.5, -0.5),
            (-0.5, 0.5, 0.5),
            (0.5, 0.5, 0.5),
            (0.5, 0.5, -0.5),
        ),
    ),
    (
        (0, 0, 1),
        (0, 0, 1),
        (
            (-0.5, -0.5, 0.5),
            (0.5, -0.5, 0.5),
            (0.5, 0.5, 0.5),
            (-0.5, 0.5, 0.5),
        ),
    ),
    (
        (0, 0, -1),
        (0, 0, -1),
        (
            (0.5, -0.5, -0.5),
            (-0.5, -0.5, -0.5),
            (-0.5, 0.5, -0.5),
            (0.5, 0.5, -0.5),
        ),
    ),
    (
        (1, 0, 0),
        (1, 0, 0),
        (
            (0.5, -0.5, 0.5),
            (0.5, -0.5, -0.5),
            (0.5, 0.5, -0.5),
            (0.5, 0.5, 0.5),
        ),
    ),
    (
        (-1, 0, 0),
        (-1, 0, 0),
        (
            (-0.5, -0.5, -0.5),
            (-0.5, -0.5, 0.5),
            (-0.5, 0.5, 0.5),
            (-0.5, 0.5, -0.5),
        ),
    ),
    (
        (0, -1, 0),
        (0, -1, 0),
        (
            (-0.5, -0.5, 0.5),
            (-0.5, -0.5, -0.5),
            (0.5, -0.5, -0.5),
            (0.5, -0.5, 0.5),
        ),
    ),
)

# Panda3D/Ursina culls the opposite winding from the order we were using.
# Reversing every triangle makes the visible side of each block face point
# outward, which also lets the player's downward collision ray hit the tops
# of terrain blocks correctly.
QUAD_TRIANGLES = (
    2, 1, 0,
    3, 2, 0,
)


# Full-texture UVs used only by the separate animated water mesh.
WATER_FACE_UVS = (
    (
        (0.0, 0.0),
        (0.0, 1.0),
        (1.0, 1.0),
        (1.0, 0.0),
    ),
    (
        (0.0, 0.0),
        (1.0, 0.0),
        (1.0, 1.0),
        (0.0, 1.0),
    ),
    (
        (0.0, 0.0),
        (1.0, 0.0),
        (1.0, 1.0),
        (0.0, 1.0),
    ),
    (
        (0.0, 0.0),
        (1.0, 0.0),
        (1.0, 1.0),
        (0.0, 1.0),
    ),
    (
        (0.0, 0.0),
        (1.0, 0.0),
        (1.0, 1.0),
        (0.0, 1.0),
    ),
    (
        (0.0, 1.0),
        (0.0, 0.0),
        (1.0, 0.0),
        (1.0, 1.0),
    ),
)


class FlowingWaterEntity(Entity):
    def __init__(self, **kwargs):
        super().__init__(
            **kwargs
        )

        self.flow_u = 0.0
        self.flow_v = 0.0

        if self.texture is not None:
            self.texture.repeat = True
            self.texture.filtering = "nearest"

    def update(self):
        # Slow diagonal texture movement gives a visible flowing-water
        # effect without rebuilding the water mesh every frame.
        self.flow_u = (
            self.flow_u
            + time.dt * WATER_TEXTURE_FLOW_U
        ) % 1.0

        self.flow_v = (
            self.flow_v
            + time.dt * WATER_TEXTURE_FLOW_V
        ) % 1.0

        self.texture_offset = (
            self.flow_u,
            self.flow_v,
        )


class FlowingLavaEntity(Entity):
    def __init__(self, **kwargs):
        super().__init__(
            **kwargs
        )

        self.flow_u = 0.0
        self.flow_v = 0.0

        if self.texture is not None:
            self.texture.repeat = True
            self.texture.filtering = "nearest"

    def update(self):
        self.flow_u = (
            self.flow_u
            + time.dt
            * LAVA_TEXTURE_FLOW_U
        ) % 1.0

        self.flow_v = (
            self.flow_v
            + time.dt
            * LAVA_TEXTURE_FLOW_V
        ) % 1.0

        self.texture_offset = (
            self.flow_u,
            self.flow_v,
        )


class WaterSimulation(Entity):
    def __init__(self, world):
        super().__init__()

        self.world = world
        self.timer = 0.0

    def update(self):
        self.timer += time.dt

        if self.timer < WATER_FLOW_TICK:
            return

        self.timer = 0.0

        self.world.process_water_flow(
            WATER_UPDATES_PER_TICK
        )


class ChunkRender:
    def __init__(self):
        self.opaque: Entity | None = None
        self.transparent: Entity | None = None
        self.water: Entity | None = None
        self.lava: Entity | None = None
        self.obsidian: Entity | None = None
        self.collision: Entity | None = None

    def destroy(self) -> None:
        if self.opaque is not None:
            destroy(
                self.opaque
            )

        if self.transparent is not None:
            destroy(
                self.transparent
            )

        if self.water is not None:
            destroy(
                self.water
            )

        if self.lava is not None:
            destroy(
                self.lava
            )

        if self.obsidian is not None:
            destroy(
                self.obsidian
            )

        if self.collision is not None:
            destroy(
                self.collision
            )


class World:
    def __init__(
        self,
        initial_state=None,
        dimension: str = "overworld",
    ):
        self.dimension = (
            "nether"
            if str(dimension).lower() == "nether"
            else "overworld"
        )
        self.blocks: Dict[
            GridPos,
            BlockType,
        ] = {}

        self.chunk_blocks: dict[
            ChunkPos,
            set[GridPos],
        ] = defaultdict(set)

        self.chunk_renders: Dict[
            ChunkPos,
            ChunkRender,
        ] = {}

        self.water_levels: Dict[
            GridPos,
            int,
        ] = {}

        self.water_queue = deque()
        self.water_queued: set[
            GridPos
        ] = set()

        if initial_state:
            self.load_state(initial_state)
        else:
            self.generate()

        self.rebuild_all_chunks()

        self.water_simulation = (
            WaterSimulation(
                self
            )
        )

    @staticmethod
    def key_from_vec(
        position: Vec3,
    ) -> GridPos:
        return (
            math.floor(
                position.x + 0.5
            ),
            math.floor(
                position.y + 0.5
            ),
            math.floor(
                position.z + 0.5
            ),
        )

    @staticmethod
    def terrain_height(
        x: int,
        z: int,
    ) -> int:
        seed_offset = (
            WORLD_SEED - 7
        ) * 0.013

        wave = (
            math.sin(
                x * TERRAIN_X_FREQUENCY
                + seed_offset
            )
            * TERRAIN_X_AMPLITUDE
            + math.cos(
                z * TERRAIN_Z_FREQUENCY
                - seed_offset * 0.71
            )
            * TERRAIN_Z_AMPLITUDE
        )

        detail = (
            math.sin(
                (x + z)
                * TERRAIN_DETAIL_FREQUENCY
                + seed_offset * 0.37
            )
            * TERRAIN_DETAIL_AMPLITUDE
        )

        return max(
            1,
            min(
                MAX_TERRAIN_HEIGHT,
                TERRAIN_BASE_HEIGHT
                + round(
                    wave
                    + detail
                ),
            ),
        )

    def get_spawn_position(
        self,
    ) -> Vec3:
        top_y = self.terrain_height(
            0,
            0,
        )

        return Vec3(
            0,
            max(
                top_y,
                WATER_LEVEL,
            ) + 1.5,
            0,
        )

    @staticmethod
    def chunk_position_for_block(
        position: GridPos,
    ) -> ChunkPos:
        x, _, z = position

        return (
            x // CHUNK_SIZE,
            z // CHUNK_SIZE,
        )

    def _store_block(
        self,
        position: GridPos,
        block_type: BlockType,
        water_level: int | None = None,
    ) -> None:
        if position in self.blocks:
            return

        self.blocks[
            position
        ] = block_type

        if block_type == BlockType.WATER:
            self.water_levels[
                position
            ] = (
                0
                if water_level is None
                else max(
                    0,
                    min(
                        WATER_MAX_FLOW_LEVEL,
                        int(water_level),
                    ),
                )
            )

        chunk_position = (
            self.chunk_position_for_block(
                position
            )
        )

        self.chunk_blocks[
            chunk_position
        ].add(position)

    def _erase_block(
        self,
        position: GridPos,
    ) -> None:
        if position not in self.blocks:
            return

        self.blocks.pop(
            position,
            None,
        )

        self.water_levels.pop(
            position,
            None,
        )

        self.water_queued.discard(
            position
        )

        chunk_position = (
            self.chunk_position_for_block(
                position
            )
        )

        positions = (
            self.chunk_blocks.get(
                chunk_position
            )
        )

        if positions is None:
            return

        positions.discard(
            position
        )

        if not positions:
            self.chunk_blocks.pop(
                chunk_position,
                None,
            )

    def _replace_block_type(
        self,
        position: GridPos,
        block_type: BlockType,
    ) -> None:
        old_type = self.blocks.get(
            position
        )

        if old_type is None:
            self._store_block(
                position,
                block_type,
            )
            return

        if old_type == block_type:
            return

        if old_type == BlockType.WATER:
            self.water_levels.pop(
                position,
                None,
            )
            self.water_queued.discard(
                position
            )

        self.blocks[
            position
        ] = block_type

        if block_type == BlockType.WATER:
            self.water_levels[
                position
            ] = 0

    @staticmethod
    def _neighbour_positions(
        position: GridPos,
    ):
        x, y, z = position

        return (
            (x + 1, y, z),
            (x - 1, y, z),
            (x, y + 1, z),
            (x, y - 1, z),
            (x, y, z + 1),
            (x, y, z - 1),
        )

    def _react_water_and_lava(
        self,
        position: GridPos,
    ) -> set[GridPos]:
        changed: set[
            GridPos
        ] = set()

        current = self.blocks.get(
            position
        )

        if current == BlockType.LAVA:
            if any(
                self.blocks.get(
                    neighbour
                )
                == BlockType.WATER
                for neighbour
                in self._neighbour_positions(
                    position
                )
            ):
                self._replace_block_type(
                    position,
                    BlockType.OBSIDIAN,
                )
                changed.add(
                    position
                )

        elif current == BlockType.WATER:
            for neighbour in (
                self._neighbour_positions(
                    position
                )
            ):
                if (
                    self.blocks.get(
                        neighbour
                    )
                    == BlockType.LAVA
                ):
                    self._replace_block_type(
                        neighbour,
                        BlockType.OBSIDIAN,
                    )
                    changed.add(
                        neighbour
                    )

        return changed

    def get_block(
        self,
        position: GridPos,
    ) -> BlockType | None:
        return self.blocks.get(
            position
        )

    @staticmethod
    def _inside_world_horizontal(
        position: GridPos,
    ) -> bool:
        x, _y, z = position

        return (
            -WORLD_HALF <= x < WORLD_HALF
            and -WORLD_HALF <= z < WORLD_HALF
        )

    def _queue_water(
        self,
        position: GridPos,
    ) -> None:
        if (
            self.blocks.get(
                position
            )
            != BlockType.WATER
        ):
            return

        if position in self.water_queued:
            return

        self.water_queued.add(
            position
        )

        self.water_queue.append(
            position
        )

    def _queue_water_around(
        self,
        position: GridPos,
    ) -> None:
        x, y, z = position

        neighbours = (
            (x, y + 1, z),
            (x + 1, y, z),
            (x - 1, y, z),
            (x, y, z + 1),
            (x, y, z - 1),
        )

        for neighbour in neighbours:
            self._queue_water(
                neighbour
            )

    def _set_flowing_water(
        self,
        position: GridPos,
        level: int,
    ) -> bool:
        if position[1] < 0:
            return False

        if not self._inside_world_horizontal(
            position
        ):
            return False

        existing = self.blocks.get(
            position
        )

        if existing == BlockType.LAVA:
            self._replace_block_type(
                position,
                BlockType.OBSIDIAN,
            )

            return True

        if existing is None:
            self._store_block(
                position,
                BlockType.WATER,
                water_level=level,
            )

            self._queue_water(
                position
            )

            return True

        if existing != BlockType.WATER:
            return False

        old_level = self.water_levels.get(
            position,
            0,
        )

        # Source blocks (level 0) never get weakened.
        if old_level == 0:
            return False

        if level >= old_level:
            return False

        self.water_levels[
            position
        ] = level

        self._queue_water(
            position
        )

        return True

    def _water_dirty_chunks(
        self,
        position: GridPos,
    ) -> set[ChunkPos]:
        x, y, z = position

        return {
            self.chunk_position_for_block(
                position
            ),
            self.chunk_position_for_block(
                (x + 1, y, z)
            ),
            self.chunk_position_for_block(
                (x - 1, y, z)
            ),
            self.chunk_position_for_block(
                (x, y, z + 1)
            ),
            self.chunk_position_for_block(
                (x, y, z - 1)
            ),
        }

    def process_water_flow(
        self,
        maximum_updates: int,
    ) -> None:
        if not self.water_queue:
            return

        dirty_chunks: set[
            ChunkPos
        ] = set()

        updates = 0

        while (
            self.water_queue
            and updates
            < maximum_updates
        ):
            position = (
                self.water_queue.popleft()
            )

            self.water_queued.discard(
                position
            )

            if (
                self.blocks.get(
                    position
                )
                != BlockType.WATER
            ):
                continue

            x, y, z = position

            level = self.water_levels.get(
                position,
                0,
            )

            below = (
                x,
                y - 1,
                z,
            )

            # Water always tries to fall first.
            if (
                y > 0
                and self.blocks.get(
                    below
                )
                in (
                    None,
                    BlockType.LAVA,
                )
            ):
                falling_level = (
                    1
                    if level == 0
                    else level
                )

                if self._set_flowing_water(
                    below,
                    falling_level,
                ):
                    dirty_chunks.update(
                        self._water_dirty_chunks(
                            below
                        )
                    )

                updates += 1
                continue

            # Once supported, water spreads sideways and gets weaker
            # by one level per block, up to seven blocks from a source.
            if level < WATER_MAX_FLOW_LEVEL:
                next_level = (
                    level + 1
                )

                for target in (
                    (x + 1, y, z),
                    (x - 1, y, z),
                    (x, y, z + 1),
                    (x, y, z - 1),
                ):
                    if self._set_flowing_water(
                        target,
                        next_level,
                    ):
                        dirty_chunks.update(
                            self._water_dirty_chunks(
                                target
                            )
                        )

            updates += 1

        # Rebuild each affected chunk only once per water tick.
        for chunk_position in (
            dirty_chunks
        ):
            if (
                chunk_position
                in self.chunk_blocks
                or chunk_position
                in self.chunk_renders
            ):
                self.rebuild_chunk(
                    chunk_position
                )

    def scoop_liquid(
        self,
        position: Vec3 | GridPos,
    ) -> BlockType | None:
        if isinstance(
            position,
            Vec3,
        ):
            key = self.key_from_vec(
                position
            )
        else:
            key = tuple(
                int(value)
                for value in position
            )

        liquid_type = self.blocks.get(
            key
        )

        if liquid_type not in (
            BlockType.WATER,
            BlockType.LAVA,
        ):
            return None

        self._erase_block(
            key
        )

        if liquid_type == BlockType.WATER:
            self._queue_water_around(
                key
            )

        self.rebuild_around_position(
            key
        )

        return liquid_type

    def add_block(
        self,
        block_type: BlockType,
        position: Vec3 | GridPos,
        rotation_y: float = 0.0,
    ):
        if isinstance(
            position,
            Vec3,
        ):
            key = self.key_from_vec(
                position
            )
        else:
            key = tuple(
                int(value)
                for value in position
            )

        if key in self.blocks:
            return None

        self._store_block(
            key,
            block_type,
        )

        if block_type == BlockType.WATER:
            self._queue_water(
                key
            )

        changed = (
            self._react_water_and_lava(
                key
            )
        )

        self.rebuild_around_position(
            key
        )

        for changed_position in changed:
            self.rebuild_around_position(
                changed_position
            )

        return key

    def remove_block(
        self,
        position: Vec3 | GridPos,
    ) -> bool:
        if isinstance(
            position,
            Vec3,
        ):
            key = self.key_from_vec(
                position
            )
        else:
            key = tuple(
                int(value)
                for value in position
            )

        block_type = (
            self.blocks.get(
                key
            )
        )

        if block_type is None:
            return False

        if not BLOCKS[
            block_type
        ].breakable:
            return False

        self._erase_block(
            key
        )

        # If this block was holding water back, nearby water is now
        # scheduled to flow into the newly opened space.
        self._queue_water_around(
            key
        )

        self.rebuild_around_position(
            key
        )

        return True

    def serialize_state(self) -> dict:
        blocks = [
            [x, y, z, block_type.value]
            for (x, y, z), block_type in self.blocks.items()
        ]

        water_levels = [
            [x, y, z, level]
            for (x, y, z), level in self.water_levels.items()
        ]

        return {
            "blocks": blocks,
            "water_levels": water_levels,
        }

    def load_state(self, state: dict) -> None:
        self.blocks.clear()
        self.chunk_blocks.clear()
        self.water_levels.clear()
        self.water_queue.clear()
        self.water_queued.clear()

        levels = {
            (int(x), int(y), int(z)): int(level)
            for x, y, z, level in state.get(
                "water_levels",
                [],
            )
        }

        for item in state.get(
            "blocks",
            [],
        ):
            if len(item) != 4:
                continue

            x, y, z, value = item

            try:
                block_type = BlockType(value)
            except ValueError:
                continue

            position = (
                int(x),
                int(y),
                int(z),
            )

            self._store_block(
                position,
                block_type,
                water_level=levels.get(
                    position
                ),
            )

        for position, block_type in list(
            self.blocks.items()
        ):
            if block_type == BlockType.WATER:
                self._queue_water(
                    position
                )

        for position, block_type in list(
            self.blocks.items()
        ):
            if block_type in (
                BlockType.WATER,
                BlockType.LAVA,
            ):
                self._react_water_and_lava(
                    position
                )

    def destroy(self) -> None:
        for chunk_render in list(
            self.chunk_renders.values()
        ):
            chunk_render.destroy()

        self.chunk_renders.clear()

        if getattr(
            self,
            "water_simulation",
            None,
        ) is not None:
            destroy(
                self.water_simulation
            )

    def generate(
        self,
    ) -> None:
        random.seed(WORLD_SEED)

        for x in range(
            -WORLD_HALF,
            WORLD_HALF,
        ):
            for z in range(
                -WORLD_HALF,
                WORLD_HALF,
            ):
                top_y = (
                    self.terrain_height(
                        x,
                        z,
                    )
                )

                # The terrain is real solid block data from y=0 to the
                # surface. Internal faces are culled later, so this does not
                # create thousands of visible cube entities.
                for y in range(
                    0,
                    top_y + 1,
                ):
                    block_type = (
                        BlockType.GRASS_BLOCK
                        if y == top_y
                        else BlockType.DIRT
                    )

                    self._store_block(
                        (x, y, z),
                        block_type,
                    )

                if top_y < WATER_LEVEL:
                    for y in range(
                        top_y + 1,
                        WATER_LEVEL + 1,
                    ):
                        self._store_block(
                            (x, y, z),
                            BlockType.WATER,
                        )

                away_from_edge = (
                    abs(x)
                    < WORLD_HALF - 2
                    and abs(z)
                    < WORLD_HALF - 2
                )

                if (
                    away_from_edge
                    and top_y
                    > WATER_LEVEL
                    and random.random()
                    < TREE_CHANCE
                    and abs(x) > 3
                    and abs(z) > 3
                ):
                    self._generate_tree(
                        x,
                        top_y + 1,
                        z,
                    )

        self._generate_lava_lakes()

        print(
            f"blocks = {len(self.blocks)}"
        )

    def _generate_lava_lakes(
        self,
    ) -> None:
        """
        Carve visible surface lava pools into newly generated worlds.

        The previous generator rejected many locations because it required
        extremely flat terrain. This version deliberately carves a shallow
        basin, so the configured number of pools is much more reliable.
        """
        if LAVA_LAKE_COUNT <= 0:
            return

        generated = 0

        # Plenty of attempts, but still bounded.
        attempts_left = max(
            100,
            LAVA_LAKE_COUNT * 80,
        )

        used_centres = []

        while (
            generated < LAVA_LAKE_COUNT
            and attempts_left > 0
        ):
            attempts_left -= 1

            radius = random.randint(
                LAVA_LAKE_MIN_RADIUS,
                LAVA_LAKE_MAX_RADIUS,
            )

            margin = radius + 3

            if WORLD_HALF <= margin + 1:
                break

            center_x = random.randint(
                -WORLD_HALF + margin,
                WORLD_HALF - margin - 1,
            )

            center_z = random.randint(
                -WORLD_HALF + margin,
                WORLD_HALF - margin - 1,
            )

            # Keep the player's initial spawn area safe.
            if (
                center_x * center_x
                + center_z * center_z
                < LAVA_SAFE_SPAWN_RADIUS
                * LAVA_SAFE_SPAWN_RADIUS
            ):
                continue

            # Keep separate lakes from merging into one huge pool.
            too_close = False

            for old_x, old_z, old_radius in used_centres:
                minimum_distance = (
                    radius
                    + old_radius
                    + 4
                )

                if (
                    (center_x - old_x) ** 2
                    + (center_z - old_z) ** 2
                    < minimum_distance ** 2
                ):
                    too_close = True
                    break

            if too_close:
                continue

            center_height = self.terrain_height(
                center_x,
                center_z,
            )

            # Don't intentionally create a lake inside an ocean/pond.
            if center_height <= WATER_LEVEL:
                continue

            # The lava surface sits one block below the original centre
            # surface so the lake looks carved into the ground.
            lava_y = max(
                1,
                center_height - 1,
            )

            lake_positions = []

            for dx in range(
                -radius - 1,
                radius + 2,
            ):
                for dz in range(
                    -radius - 1,
                    radius + 2,
                ):
                    distance = math.sqrt(
                        dx * dx
                        + dz * dz
                    )

                    # A tiny random wobble prevents every lake from being
                    # a mathematically perfect circle.
                    edge_noise = random.uniform(
                        -0.25,
                        0.20,
                    )

                    if distance > radius + edge_noise:
                        continue

                    x = center_x + dx
                    z = center_z + dz

                    if not (
                        -WORLD_HALF
                        <= x
                        < WORLD_HALF
                        and -WORLD_HALF
                        <= z
                        < WORLD_HALF
                    ):
                        continue

                    # Don't cut into deep water columns.
                    local_height = self.terrain_height(
                        x,
                        z,
                    )

                    if local_height < WATER_LEVEL:
                        continue

                    # Clear the column from the intended lava surface
                    # upward. This removes grass, dirt, water, trees and
                    # leaves occupying the bowl.
                    clear_top = (
                        MAX_TERRAIN_HEIGHT
                        + TREE_MAX_HEIGHT
                        + 8
                    )

                    for y in range(
                        lava_y,
                        clear_top,
                    ):
                        if (
                            (x, y, z)
                            in self.blocks
                        ):
                            self._erase_block(
                                (
                                    x,
                                    y,
                                    z,
                                )
                            )

                    # Make sure lava never opens into the void underneath.
                    floor_position = (
                        x,
                        lava_y - 1,
                        z,
                    )

                    if floor_position not in self.blocks:
                        self._store_block(
                            floor_position,
                            BlockType.DIRT,
                        )

                    lava_position = (
                        x,
                        lava_y,
                        z,
                    )

                    self._store_block(
                        lava_position,
                        BlockType.LAVA,
                    )

                    lake_positions.append(
                        lava_position
                    )

            # Require a real pool, not one or two lucky cells.
            minimum_blocks = max(
                5,
                radius * radius,
            )

            if len(lake_positions) < minimum_blocks:
                for position in lake_positions:
                    if (
                        self.blocks.get(
                            position
                        )
                        == BlockType.LAVA
                    ):
                        self._erase_block(
                            position
                        )

                continue

            # If the edge touches generated water, lava on that edge turns
            # into obsidian immediately.
            for position in lake_positions:
                self._react_water_and_lava(
                    position
                )

            used_centres.append(
                (
                    center_x,
                    center_z,
                    radius,
                )
            )

            generated += 1

        print(
            f"lava lakes = "
            f"{generated}/"
            f"{LAVA_LAKE_COUNT}"
        )

    def _generate_tree(
        self,
        x: int,
        y: int,
        z: int,
    ) -> None:
        height = random.randint(
            TREE_MIN_HEIGHT,
            TREE_MAX_HEIGHT,
        )

        for dy in range(
            height
        ):
            self._store_block(
                (
                    x,
                    y + dy,
                    z,
                ),
                BlockType.OAK_LOG,
            )

        canopy_y = (
            y + height
        )

        for dx in range(-2, 3):
            for dz in range(-2, 3):
                for dy in range(-1, 2):
                    if (
                        abs(dx)
                        + abs(dz)
                        + abs(dy)
                        <= 4
                    ):
                        position = (
                            x + dx,
                            canopy_y + dy,
                            z + dz,
                        )

                        if (
                            position
                            not in self.blocks
                        ):
                            self._store_block(
                                position,
                                BlockType.OAK_LEAVES,
                            )

    def _face_is_visible(
        self,
        block_type: BlockType,
        neighbour_type: BlockType | None,
    ) -> bool:
        if neighbour_type is None:
            return True

        current = BLOCKS[
            block_type
        ]

        neighbour = BLOCKS[
            neighbour_type
        ]

        if (
            current.transparent
            and neighbour_type
            == block_type
        ):
            return False

        if not current.transparent:
            return neighbour.transparent

        if (
            neighbour.solid
            and not neighbour.transparent
        ):
            return False

        return True

    @staticmethod
    def _collision_face_visible(
        neighbour_type: BlockType | None,
    ) -> bool:
        if neighbour_type is None:
            return True

        return not BLOCKS[
            neighbour_type
        ].solid

    def rebuild_all_chunks(
        self,
    ) -> None:
        for chunk_position in list(
            self.chunk_blocks.keys()
        ):
            self.rebuild_chunk(
                chunk_position
            )

    def rebuild_around_position(
        self,
        position: GridPos,
    ) -> None:
        x, _y, z = position

        chunk_x, chunk_z = (
            self.chunk_position_for_block(
                position
            )
        )

        chunk_positions = {
            (
                chunk_x,
                chunk_z,
            )
        }

        local_x = (
            x
            - chunk_x
            * CHUNK_SIZE
        )

        local_z = (
            z
            - chunk_z
            * CHUNK_SIZE
        )

        # Only a block on a chunk edge can change a face in a neighbour.
        if local_x == 0:
            chunk_positions.add(
                (
                    chunk_x - 1,
                    chunk_z,
                )
            )

        elif local_x == (
            CHUNK_SIZE - 1
        ):
            chunk_positions.add(
                (
                    chunk_x + 1,
                    chunk_z,
                )
            )

        if local_z == 0:
            chunk_positions.add(
                (
                    chunk_x,
                    chunk_z - 1,
                )
            )

        elif local_z == (
            CHUNK_SIZE - 1
        ):
            chunk_positions.add(
                (
                    chunk_x,
                    chunk_z + 1,
                )
            )

        for chunk_position in (
            chunk_positions
        ):
            self.rebuild_chunk(
                chunk_position
            )

    @staticmethod
    def _new_mesh_data():
        return (
            [],
            [],
            [],
            [],
        )

    def _append_render_face(
        self,
        data,
        local_x: float,
        y: float,
        local_z: float,
        block_type: BlockType,
        face_index: int,
    ) -> None:
        vertices, triangles, uvs, normals = data

        _offset, normal, face_vertices = (
            FACE_DATA[
                face_index
            ]
        )

        start = len(
            vertices
        )

        for (
            vx,
            vy,
            vz,
        ) in face_vertices:
            vertices.append(
                (
                    local_x + vx,
                    y + vy,
                    local_z + vz,
                )
            )

            normals.append(
                normal
            )

        triangles.extend(
            start + index
            for index in QUAD_TRIANGLES
        )

        uvs.extend(
            get_face_uvs(
                block_type.value,
                face_index,
            )
        )

    def _append_water_face(
        self,
        data,
        local_x: float,
        y: float,
        local_z: float,
        face_index: int,
    ) -> None:
        vertices, triangles, uvs, normals = data

        _offset, normal, face_vertices = (
            FACE_DATA[
                face_index
            ]
        )

        start = len(
            vertices
        )

        for (
            vx,
            vy,
            vz,
        ) in face_vertices:
            vertices.append(
                (
                    local_x + vx,
                    y + vy,
                    local_z + vz,
                )
            )

            normals.append(
                normal
            )

        triangles.extend(
            start + index
            for index in QUAD_TRIANGLES
        )

        uvs.extend(
            WATER_FACE_UVS[
                face_index
            ]
        )

    def _append_collision_face(
        self,
        vertices,
        triangles,
        local_x: float,
        y: float,
        local_z: float,
        face_index: int,
    ) -> None:
        _offset, _normal, face_vertices = (
            FACE_DATA[
                face_index
            ]
        )

        start = len(
            vertices
        )

        for (
            vx,
            vy,
            vz,
        ) in face_vertices:
            vertices.append(
                (
                    local_x + vx,
                    y + vy,
                    local_z + vz,
                )
            )

        triangles.extend(
            start + index
            for index in QUAD_TRIANGLES
        )

    @staticmethod
    def _make_render_mesh(
        data,
    ):
        vertices, triangles, uvs, normals = data

        if not vertices:
            return None

        return Mesh(
            vertices=vertices,
            triangles=triangles,
            uvs=uvs,
            normals=normals,
            static=True,
        )

    @staticmethod
    def _make_collision_mesh(
        vertices,
        triangles,
    ):
        if not vertices:
            return None

        return Mesh(
            vertices=vertices,
            triangles=triangles,
            static=True,
        )

    def rebuild_chunk(
        self,
        chunk_position: ChunkPos,
    ) -> None:
        old_render = (
            self.chunk_renders.pop(
                chunk_position,
                None,
            )
        )

        if old_render is not None:
            old_render.destroy()

        positions = (
            self.chunk_blocks.get(
                chunk_position
            )
        )

        if not positions:
            return

        chunk_x, chunk_z = (
            chunk_position
        )

        origin_x = (
            chunk_x
            * CHUNK_SIZE
        )

        origin_z = (
            chunk_z
            * CHUNK_SIZE
        )

        opaque_data = (
            self._new_mesh_data()
        )

        transparent_data = (
            self._new_mesh_data()
        )

        water_data = (
            self._new_mesh_data()
        )

        lava_data = (
            self._new_mesh_data()
        )

        obsidian_data = (
            self._new_mesh_data()
        )

        collision_vertices = []
        collision_triangles = []

        for position in positions:
            x, y, z = position

            block_type = (
                self.blocks.get(
                    position
                )
            )

            if block_type is None:
                continue

            definition = BLOCKS[
                block_type
            ]

            local_x = (
                x - origin_x
            )

            local_z = (
                z - origin_z
            )

            if block_type == BlockType.WATER:
                render_data = water_data

            elif block_type == BlockType.LAVA:
                render_data = lava_data

            elif block_type == BlockType.OBSIDIAN:
                render_data = obsidian_data

            elif definition.transparent:
                render_data = (
                    transparent_data
                )

            else:
                render_data = (
                    opaque_data
                )

            for face_index, (
                offset,
                _normal,
                _vertices,
            ) in enumerate(
                FACE_DATA
            ):
                ox, oy, oz = offset

                neighbour_type = (
                    self.blocks.get(
                        (
                            x + ox,
                            y + oy,
                            z + oz,
                        )
                    )
                )

                if (
                    self._face_is_visible(
                        block_type,
                        neighbour_type,
                    )
                ):
                    # y=0 bottom faces can never be seen during normal
                    # gameplay and only waste vertices.
                    if not (
                        face_index == 5
                        and y == 0
                    ):
                        if block_type in (
                            BlockType.WATER,
                            BlockType.LAVA,
                            BlockType.OBSIDIAN,
                        ):
                            self._append_water_face(
                                render_data,
                                local_x,
                                y,
                                local_z,
                                face_index,
                            )

                        else:
                            self._append_render_face(
                                render_data,
                                local_x,
                                y,
                                local_z,
                                block_type,
                                face_index,
                            )

                if (
                    definition.solid
                    and self._collision_face_visible(
                        neighbour_type
                    )
                ):
                    if not (
                        face_index == 5
                        and y == 0
                    ):
                        self._append_collision_face(
                            collision_vertices,
                            collision_triangles,
                            local_x,
                            y,
                            local_z,
                            face_index,
                        )

        if self.dimension == "nether":
            atlas = get_texture(
                "nether_atlas.png"
            )
        else:
            atlas = (
                get_atlas_texture()
            )

        chunk_render = (
            ChunkRender()
        )

        chunk_origin = Vec3(
            origin_x,
            0,
            origin_z,
        )

        opaque_mesh = (
            self._make_render_mesh(
                opaque_data
            )
        )

        if opaque_mesh is not None:
            chunk_render.opaque = Entity(
                model=opaque_mesh,
                texture=atlas,
                position=chunk_origin,
                color=color.white,
            )

        transparent_mesh = (
            self._make_render_mesh(
                transparent_data
            )
        )

        if transparent_mesh is not None:
            chunk_render.transparent = Entity(
                model=transparent_mesh,
                texture=atlas,
                position=chunk_origin,
                color=color.white,
                double_sided=True,
            )

        water_mesh = (
            self._make_render_mesh(
                water_data
            )
        )

        if water_mesh is not None:
            chunk_render.water = (
                FlowingWaterEntity(
                    model=water_mesh,
                    texture=get_texture(
                        "nether_all.png"
                        if self.dimension
                        == "nether"
                        else SPECIAL_BLOCK_TEXTURES[
                            "WATER"
                        ]
                    ),
                    position=chunk_origin,
                    color=color.rgba32(
                        255,
                        255,
                        255,
                        205,
                    ),
                    double_sided=True,
                )
            )

        lava_mesh = (
            self._make_render_mesh(
                lava_data
            )
        )

        if lava_mesh is not None:
            chunk_render.lava = (
                FlowingLavaEntity(
                    model=lava_mesh,
                    texture=get_texture(
                        "nether_all.png"
                        if self.dimension
                        == "nether"
                        else SPECIAL_BLOCK_TEXTURES[
                            "LAVA"
                        ]
                    ),
                    position=chunk_origin,
                    color=color.rgba32(
                        255,
                        255,
                        255,
                        235,
                    ),
                    double_sided=True,
                )
            )

        obsidian_mesh = (
            self._make_render_mesh(
                obsidian_data
            )
        )

        if obsidian_mesh is not None:
            chunk_render.obsidian = Entity(
                model=obsidian_mesh,
                texture=get_texture(
                    "nether_all.png"
                    if self.dimension
                    == "nether"
                    else SPECIAL_BLOCK_TEXTURES[
                        "OBSIDIAN"
                    ]
                ),
                position=chunk_origin,
                color=color.white,
            )

        collision_mesh = (
            self._make_collision_mesh(
                collision_vertices,
                collision_triangles,
            )
        )

        if collision_mesh is not None:
            chunk_render.collision = Entity(
                model=collision_mesh,
                position=chunk_origin,
                color=color.rgba32(
                    255,
                    255,
                    255,
                    0,
                ),
                collider="mesh",
            )

            chunk_render.collision.is_world_chunk_collider = True

        self.chunk_renders[
            chunk_position
        ] = chunk_render

    @staticmethod
    def _nearest_block_coordinate(
        value: float,
    ) -> int:
        return math.floor(
            value + 0.5
        )

    def player_overlaps_solid(
        self,
        position: Vec3,
        height: float,
        half_width: float = 0.30,
    ) -> bool:
        epsilon = 0.015

        player_min_x = (
            position.x
            - half_width
            + epsilon
        )

        player_max_x = (
            position.x
            + half_width
            - epsilon
        )

        player_min_y = (
            position.y
            + epsilon
        )

        player_max_y = (
            position.y
            + height
            - epsilon
        )

        player_min_z = (
            position.z
            - half_width
            + epsilon
        )

        player_max_z = (
            position.z
            + half_width
            - epsilon
        )

        min_x = math.floor(
            player_min_x
            + 0.5
        )

        max_x = math.floor(
            player_max_x
            + 0.5
        )

        min_y = math.floor(
            player_min_y
            + 0.5
        )

        max_y = math.floor(
            player_max_y
            + 0.5
        )

        min_z = math.floor(
            player_min_z
            + 0.5
        )

        max_z = math.floor(
            player_max_z
            + 0.5
        )

        for x in range(
            min_x,
            max_x + 1,
        ):
            for y in range(
                min_y,
                max_y + 1,
            ):
                for z in range(
                    min_z,
                    max_z + 1,
                ):
                    block_type = (
                        self.blocks.get(
                            (x, y, z)
                        )
                    )

                    if block_type is None:
                        continue

                    if not BLOCKS[
                        block_type
                    ].solid:
                        continue

                    block_min_x = (
                        x - 0.5
                    )

                    block_max_x = (
                        x + 0.5
                    )

                    block_min_y = (
                        y - 0.5
                    )

                    block_max_y = (
                        y + 0.5
                    )

                    block_min_z = (
                        z - 0.5
                    )

                    block_max_z = (
                        z + 0.5
                    )

                    if (
                        player_min_x
                        < block_max_x
                        and player_max_x
                        > block_min_x
                        and player_min_y
                        < block_max_y
                        and player_max_y
                        > block_min_y
                        and player_min_z
                        < block_max_z
                        and player_max_z
                        > block_min_z
                    ):
                        return True

        return False

    def raycast_blocks(
        self,
        origin: Vec3,
        direction: Vec3,
        max_distance: float,
    ) -> tuple[
        GridPos | None,
        GridPos | None,
    ]:
        direction = Vec3(
            direction
        )

        if (
            direction.length()
            == 0
        ):
            return (
                None,
                None,
            )

        direction = (
            direction.normalized()
        )

        # Shift by 0.5 because block centres live at integer coordinates
        # while voxel boundaries live at n +/- 0.5.
        grid_origin = Vec3(
            origin.x + 0.5,
            origin.y + 0.5,
            origin.z + 0.5,
        )

        cell_x = math.floor(
            grid_origin.x
        )

        cell_y = math.floor(
            grid_origin.y
        )

        cell_z = math.floor(
            grid_origin.z
        )

        def axis_setup(
            position,
            cell,
            component,
        ):
            if component > 0:
                return (
                    1,
                    (
                        cell
                        + 1
                        - position
                    )
                    / component,
                    1.0
                    / component,
                )

            if component < 0:
                return (
                    -1,
                    (
                        position
                        - cell
                    )
                    / -component,
                    1.0
                    / -component,
                )

            return (
                0,
                float("inf"),
                float("inf"),
            )

        (
            step_x,
            t_max_x,
            t_delta_x,
        ) = axis_setup(
            grid_origin.x,
            cell_x,
            direction.x,
        )

        (
            step_y,
            t_max_y,
            t_delta_y,
        ) = axis_setup(
            grid_origin.y,
            cell_y,
            direction.y,
        )

        (
            step_z,
            t_max_z,
            t_delta_z,
        ) = axis_setup(
            grid_origin.z,
            cell_z,
            direction.z,
        )

        current = (
            cell_x,
            cell_y,
            cell_z,
        )

        previous = (
            current
        )

        travelled = 0.0

        while (
            travelled
            <= max_distance
        ):
            block_type = (
                self.blocks.get(
                    current
                )
            )

            if block_type is not None:
                # Treat liquids as full voxel targets for interaction
                # raycasts, just like solid blocks.
                #
                # This does NOT make water/lava physically solid:
                # player collision still only uses BlockDefinition.solid,
                # so the player can continue walking/swimming through
                # liquids.
                return (
                    current,
                    previous,
                )

            previous = (
                current
            )

            if (
                t_max_x
                <= t_max_y
                and t_max_x
                <= t_max_z
            ):
                travelled = (
                    t_max_x
                )

                cell_x += (
                    step_x
                )

                t_max_x += (
                    t_delta_x
                )

            elif (
                t_max_y
                <= t_max_z
            ):
                travelled = (
                    t_max_y
                )

                cell_y += (
                    step_y
                )

                t_max_y += (
                    t_delta_y
                )

            else:
                travelled = (
                    t_max_z
                )

                cell_z += (
                    step_z
                )

                t_max_z += (
                    t_delta_z
                )

            current = (
                cell_x,
                cell_y,
                cell_z,
            )

        return (
            None,
            None,
        )

    def block_position_from_hit(
        self,
        hit,
        outside: bool = False,
    ) -> GridPos | None:
        if not hit.hit:
            return None

        normal = hit.world_normal

        abs_x = abs(
            normal.x
        )

        abs_y = abs(
            normal.y
        )

        abs_z = abs(
            normal.z
        )

        if (
            abs_x >= abs_y
            and abs_x >= abs_z
        ):
            axis = (
                1 if normal.x >= 0 else -1,
                0,
                0,
            )

        elif abs_y >= abs_z:
            axis = (
                0,
                1 if normal.y >= 0 else -1,
                0,
            )

        else:
            axis = (
                0,
                0,
                1 if normal.z >= 0 else -1,
            )

        point = (
            hit.world_point
            - Vec3(*axis) * 0.01
        )

        hit_block = (
            self._nearest_block_coordinate(
                point.x
            ),
            self._nearest_block_coordinate(
                point.y
            ),
            self._nearest_block_coordinate(
                point.z
            ),
        )

        if not outside:
            return hit_block

        return (
            hit_block[0]
            + axis[0],
            hit_block[1]
            + axis[1],
            hit_block[2]
            + axis[2],
        )
