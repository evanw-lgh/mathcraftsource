from __future__ import annotations

import copy
import math

from ursina import (
    Entity,
    Vec3,
    color,
    destroy,
    load_texture,
    scene,
    time,
)

from blocks import BlockType
from config import ASSET_DIR


DIMENSION_SAVE_FORMAT = "mathcraft_dimensions_v1"

OVERWORLD = "overworld"
NETHER = "nether"
END = "end"

PORTAL_COLOUR = color.rgba32(
    175,
    55,
    230,
    185,
)


def _grid_key(
    value,
):
    if isinstance(
        value,
        Vec3,
    ):
        return (
            math.floor(
                value.x + 0.5
            ),
            math.floor(
                value.y + 0.5
            ),
            math.floor(
                value.z + 0.5
            ),
        )

    return tuple(
        int(component)
        for component in value
    )


def _load_effect_texture(
    filename: str,
):
    path = (
        ASSET_DIR
        / "effects"
        / filename
    )

    texture = load_texture(
        path.name,
        folder=path.parent,
    )

    if texture is not None:
        texture.filtering = (
            "nearest"
        )
        texture.repeat = False

    return texture


class FirePatch(Entity):
    def __init__(
        self,
        position,
        texture,
    ):
        super().__init__(
            parent=scene,
            position=Vec3(
                *position
            ),
        )

        # Two crossed pixel-art planes.
        Entity(
            parent=self,
            model="quad",
            texture=texture,
            scale=(
                0.88,
                0.88,
            ),
            rotation_y=45,
            color=color.white,
            double_sided=True,
        )

        Entity(
            parent=self,
            model="quad",
            texture=texture,
            scale=(
                0.88,
                0.88,
            ),
            rotation_y=-45,
            color=color.white,
            double_sided=True,
        )


class PortalCell(Entity):
    def __init__(
        self,
        position,
        axis: str,
        texture,
    ):
        super().__init__(
            parent=scene,
            model="quad",
            texture=texture,
            position=Vec3(
                *position
            ),
            scale=(
                0.98,
                0.98,
            ),
            rotation_y=(
                0
                if axis == "x"
                else 90
            ),
            color=PORTAL_COLOUR,
            double_sided=True,
        )


class EndPortalCell(Entity):
    def __init__(
        self,
        position,
        axis: str,
        texture,
    ):
        x, y, z = (
            int(position[0]),
            int(position[1]),
            int(position[2]),
        )

        rotation_x = 0
        rotation_y = 0
        world_position = Vec3(
            x,
            y,
            z,
        )

        if axis == "horizontal":
            rotation_x = 90
            world_position.y += 0.51
        elif axis == "z":
            rotation_y = 90

        super().__init__(
            parent=scene,
            model="quad",
            texture=texture,
            position=world_position,
            scale=(
                0.98,
                0.98,
            ),
            rotation_x=rotation_x,
            rotation_y=rotation_y,
            color=color.white,
            double_sided=True,
        )


class DimensionManager(Entity):
    """
    Handles:
      - fire placed by the lighter
      - obsidian-frame portal activation
      - Overworld <-> Nether travel
      - cloned Nether world state
      - portal save/load data

    The first time the Nether is entered, the current Overworld block state
    is copied exactly. The Nether then renders that cloned world using the
    Nether texture override in world.py.
    """

    def __init__(
        self,
        game,
    ):
        super().__init__(
            eternal=True,
        )

        self.game = game

        self.current_dimension = (
            OVERWORLD
        )

        self.dimension_states = {
            OVERWORLD: None,
            NETHER: None,
            END: None,
        }

        # Nether portals (obsidian + lighter).
        self.portals = {
            OVERWORLD: [],
            NETHER: [],
            END: [],
        }

        # End portals (12 activated End Portal Frames).
        self.end_portals = {
            OVERWORLD: [],
            NETHER: [],
            END: [],
        }

        self.fire_positions = {
            OVERWORLD: set(),
            NETHER: set(),
            END: set(),
        }

        self.fire_entities = []
        self.portal_entities = []
        self.end_portal_entities = []

        self.portal_latched = False
        self.switch_cooldown = 0.0

        self.end_return_dimension = OVERWORLD
        self.end_return_position = None

        self.fire_texture = (
            _load_effect_texture(
                "fire.png"
            )
        )

        self.portal_texture = (
            _load_effect_texture(
                "portal.png"
            )
        )

        self.end_portal_texture = (
            _load_effect_texture(
                "end_portal.png"
            )
        )

    # =========================================================
    # SAVE / LOAD
    # =========================================================

    def reset(
        self,
    ) -> None:
        self.clear_runtime_effects()

        self.current_dimension = (
            OVERWORLD
        )

        self.dimension_states = {
            OVERWORLD: None,
            NETHER: None,
            END: None,
        }

        self.portals = {
            OVERWORLD: [],
            NETHER: [],
            END: [],
        }

        self.end_portals = {
            OVERWORLD: [],
            NETHER: [],
            END: [],
        }

        self.fire_positions = {
            OVERWORLD: set(),
            NETHER: set(),
            END: set(),
        }

        self.portal_latched = False
        self.switch_cooldown = 0.0

        self.end_return_dimension = OVERWORLD
        self.end_return_position = None

        self.game.current_dimension = (
            OVERWORLD
        )

    def load_save_state(
        self,
        raw_state,
    ):
        self.reset()

        if (
            isinstance(
                raw_state,
                dict,
            )
            and raw_state.get(
                "format"
            )
            == DIMENSION_SAVE_FORMAT
        ):
            dimensions = raw_state.get(
                "dimensions",
                {},
            )

            self.dimension_states[
                OVERWORLD
            ] = dimensions.get(
                OVERWORLD
            )

            self.dimension_states[
                NETHER
            ] = dimensions.get(
                NETHER
            )

            self.dimension_states[
                END
            ] = dimensions.get(
                END
            )

            requested_dimension = str(
                raw_state.get(
                    "current_dimension",
                    OVERWORLD,
                )
            ).lower()

            if requested_dimension not in (
                OVERWORLD,
                NETHER,
                END,
            ):
                requested_dimension = (
                    OVERWORLD
                )

            self.current_dimension = (
                requested_dimension
            )

            self.game.current_dimension = (
                requested_dimension
            )

            portal_data = raw_state.get(
                "portals",
                {},
            )

            for dimension in (
                OVERWORLD,
                NETHER,
                END,
            ):
                records = portal_data.get(
                    dimension,
                    [],
                )

                if isinstance(
                    records,
                    list,
                ):
                    self.portals[
                        dimension
                    ] = [
                        record
                        for record in records
                        if isinstance(
                            record,
                            dict,
                        )
                    ]

            end_portal_data = raw_state.get(
                "end_portals",
                {},
            )

            for dimension in (
                OVERWORLD,
                NETHER,
                END,
            ):
                records = end_portal_data.get(
                    dimension,
                    [],
                )

                if isinstance(
                    records,
                    list,
                ):
                    self.end_portals[
                        dimension
                    ] = [
                        record
                        for record in records
                        if isinstance(
                            record,
                            dict,
                        )
                    ]

            return_dimension = str(
                raw_state.get(
                    "end_return_dimension",
                    OVERWORLD,
                )
            ).lower()

            if return_dimension not in (
                OVERWORLD,
                NETHER,
            ):
                return_dimension = OVERWORLD

            self.end_return_dimension = (
                return_dimension
            )

            raw_return_position = raw_state.get(
                "end_return_position"
            )

            if (
                isinstance(
                    raw_return_position,
                    (list, tuple),
                )
                and len(
                    raw_return_position
                ) == 3
            ):
                try:
                    self.end_return_position = [
                        float(value)
                        for value in raw_return_position
                    ]
                except (
                    TypeError,
                    ValueError,
                ):
                    self.end_return_position = None

            state = self.dimension_states.get(
                requested_dimension
            )

            if (
                state is None
                and requested_dimension
                != END
            ):
                state = self.dimension_states.get(
                    OVERWORLD
                )

            if state is None:
                state = {}

            return (
                state,
                requested_dimension,
            )

        # Backward-compatible old saves are simply Overworld saves.
        self.dimension_states[
            OVERWORLD
        ] = raw_state

        self.current_dimension = (
            OVERWORLD
        )

        self.game.current_dimension = (
            OVERWORLD
        )

        return (
            raw_state,
            OVERWORLD,
        )

    def serialize_save_state(
        self,
    ) -> dict:
        if self.game.world is not None:
            self.dimension_states[
                self.current_dimension
            ] = (
                self.game.world
                .serialize_state()
            )

        return {
            "format":
                DIMENSION_SAVE_FORMAT,

            "current_dimension":
                self.current_dimension,

            "dimensions": {
                OVERWORLD:
                    self.dimension_states[
                        OVERWORLD
                    ],

                NETHER:
                    self.dimension_states[
                        NETHER
                    ],

                END:
                    self.dimension_states[
                        END
                    ],
            },

            "portals": {
                OVERWORLD:
                    copy.deepcopy(
                        self.portals[
                            OVERWORLD
                        ]
                    ),

                NETHER:
                    copy.deepcopy(
                        self.portals[
                            NETHER
                        ]
                    ),

                END:
                    copy.deepcopy(
                        self.portals[
                            END
                        ]
                    ),
            },

            "end_portals": {
                OVERWORLD:
                    copy.deepcopy(
                        self.end_portals[
                            OVERWORLD
                        ]
                    ),

                NETHER:
                    copy.deepcopy(
                        self.end_portals[
                            NETHER
                        ]
                    ),

                END:
                    copy.deepcopy(
                        self.end_portals[
                            END
                        ]
                    ),
            },

            "end_return_dimension":
                self.end_return_dimension,

            "end_return_position":
                copy.deepcopy(
                    self.end_return_position
                ),
        }

    # =========================================================
    # FIRE
    # =========================================================

    def _destroy_fire_entities(
        self,
    ) -> None:
        for entity in (
            self.fire_entities
        ):
            destroy(
                entity
            )

        self.fire_entities.clear()

    def _destroy_portal_entities(
        self,
    ) -> None:
        for entity in (
            self.portal_entities
        ):
            destroy(
                entity
            )

        self.portal_entities.clear()

    def _destroy_end_portal_entities(
        self,
    ) -> None:
        for entity in (
            self.end_portal_entities
        ):
            destroy(
                entity
            )

        self.end_portal_entities.clear()

    def clear_runtime_effects(
        self,
    ) -> None:
        self._destroy_fire_entities()
        self._destroy_portal_entities()
        self._destroy_end_portal_entities()

    def _rebuild_runtime_effects(
        self,
    ) -> None:
        self.clear_runtime_effects()

        for position in (
            self.fire_positions[
                self.current_dimension
            ]
        ):
            self.fire_entities.append(
                FirePatch(
                    position,
                    self.fire_texture,
                )
            )

        for portal in (
            self.portals[
                self.current_dimension
            ]
        ):
            axis = str(
                portal.get(
                    "axis",
                    "x",
                )
            )

            for raw_cell in (
                portal.get(
                    "cells",
                    [],
                )
            ):
                if (
                    not isinstance(
                        raw_cell,
                        (
                            list,
                            tuple,
                        ),
                    )
                    or len(
                        raw_cell
                    )
                    != 3
                ):
                    continue

                self.portal_entities.append(
                    PortalCell(
                        raw_cell,
                        axis,
                        self.portal_texture,
                    )
                )

        for portal in (
            self.end_portals[
                self.current_dimension
            ]
        ):
            axis = str(
                portal.get(
                    "axis",
                    "horizontal",
                )
            )

            for raw_cell in (
                portal.get(
                    "cells",
                    [],
                )
            ):
                if (
                    not isinstance(
                        raw_cell,
                        (list, tuple),
                    )
                    or len(
                        raw_cell
                    ) != 3
                ):
                    continue

                self.end_portal_entities.append(
                    EndPortalCell(
                        raw_cell,
                        axis,
                        self.end_portal_texture,
                    )
                )

    def place_fire(
        self,
        position,
    ) -> bool:
        if self.game.world is None:
            return False

        key = _grid_key(
            position
        )

        # Fire occupies air. It does not become a solid block.
        if (
            self.game.world.get_block(
                key
            )
            is not None
        ):
            return False

        if key not in (
            self.fire_positions[
                self.current_dimension
            ]
        ):
            self.fire_positions[
                self.current_dimension
            ].add(
                key
            )

            self.fire_entities.append(
                FirePatch(
                    key,
                    self.fire_texture,
                )
            )

        if self.current_dimension in (
            OVERWORLD,
            NETHER,
        ):
            portal = (
                self._find_portal_frame(
                    key
                )
            )

            if portal is not None:
                self.activate_portal(
                    portal
                )

        return True

    def _remove_fire_in_cells(
        self,
        cells,
    ) -> None:
        cell_set = {
            tuple(
                cell
            )
            for cell in cells
        }

        positions = (
            self.fire_positions[
                self.current_dimension
            ]
        )

        if not (
            positions
            & cell_set
        ):
            return

        positions.difference_update(
            cell_set
        )

        self._rebuild_runtime_effects()

    # =========================================================
    # PORTAL FRAME DETECTION
    # =========================================================

    @staticmethod
    def _portal_position(
        axis,
        fixed,
        horizontal,
        vertical,
    ):
        if axis == "x":
            return (
                horizontal,
                vertical,
                fixed,
            )

        return (
            fixed,
            vertical,
            horizontal,
        )

    def _check_frame_candidate(
        self,
        target,
        axis: str,
        fixed: int,
        left: int,
        bottom: int,
        width: int,
        height: int,
    ):
        world = (
            self.game.world
        )

        interior = []

        for horizontal_offset in range(
            width
        ):
            for vertical_offset in range(
                height
            ):
                position = (
                    self._portal_position(
                        axis,
                        fixed,
                        left
                        + horizontal_offset,
                        bottom
                        + vertical_offset,
                    )
                )

                border = (
                    horizontal_offset == 0
                    or horizontal_offset
                    == width - 1
                    or vertical_offset == 0
                    or vertical_offset
                    == height - 1
                )

                if border:
                    if (
                        world.get_block(
                            position
                        )
                        != BlockType.OBSIDIAN
                    ):
                        return None

                    continue

                # Portal interior must be open space.
                if (
                    world.get_block(
                        position
                    )
                    is not None
                ):
                    return None

                interior.append(
                    position
                )

        if target not in interior:
            return None

        return {
            "axis":
                axis,

            "cells": [
                list(
                    position
                )
                for position
                in interior
            ],
        }

    def _find_portal_frame(
        self,
        target,
    ):
        """
        Supports the user's five-wide portal frame as well as a
        four-wide Minecraft-style frame.

        Supported outer sizes:
          width: 4 or 5
          height: 3 through 6
        """
        target = _grid_key(
            target
        )

        target_x, target_y, target_z = (
            target
        )

        for axis in (
            "x",
            "z",
        ):
            fixed = (
                target_z
                if axis == "x"
                else target_x
            )

            target_horizontal = (
                target_x
                if axis == "x"
                else target_z
            )

            for width in (
                5,
                4,
            ):
                for height in (
                    5,
                    4,
                    6,
                    3,
                ):
                    # Try every possible interior location of the fire
                    # within this candidate rectangle.
                    for local_x in range(
                        1,
                        width - 1,
                    ):
                        for local_y in range(
                            1,
                            height - 1,
                        ):
                            left = (
                                target_horizontal
                                - local_x
                            )

                            bottom = (
                                target_y
                                - local_y
                            )

                            result = (
                                self._check_frame_candidate(
                                    target,
                                    axis,
                                    fixed,
                                    left,
                                    bottom,
                                    width,
                                    height,
                                )
                            )

                            if result is not None:
                                return result

        return None

    def activate_portal(
        self,
        portal,
    ) -> None:
        cells = portal.get(
            "cells",
            [],
        )

        if not cells:
            return

        current = (
            self.portals[
                self.current_dimension
            ]
        )

        cell_key = {
            tuple(
                cell
            )
            for cell in cells
        }

        for existing in current:
            existing_key = {
                tuple(
                    cell
                )
                for cell
                in existing.get(
                    "cells",
                    [],
                )
            }

            if existing_key == cell_key:
                return

        current.append(
            copy.deepcopy(
                portal
            )
        )

        self._remove_fire_in_cells(
            cells
        )

        # Make the matching portal active in the cloned target dimension.
        target_dimension = (
            NETHER
            if self.current_dimension
            == OVERWORLD
            else OVERWORLD
        )

        target_portals = (
            self.portals[
                target_dimension
            ]
        )

        if not any(
            {
                tuple(
                    cell
                )
                for cell in existing.get(
                    "cells",
                    [],
                )
            }
            == cell_key
            for existing
            in target_portals
        ):
            target_portals.append(
                copy.deepcopy(
                    portal
                )
            )

        self._rebuild_runtime_effects()

        self.game.ui.set_message(
            "Nether portal activated."
        )

    # =========================================================
    # END PORTAL FRAMES
    # =========================================================

    @staticmethod
    def _end_vertical_position(
        axis: str,
        fixed: int,
        horizontal: int,
        vertical: int,
    ):
        if axis == "x":
            return (
                horizontal,
                vertical,
                fixed,
            )

        return (
            fixed,
            vertical,
            horizontal,
        )

    def _check_vertical_end_frame(
        self,
        target,
        axis: str,
        fixed: int,
        left: int,
        bottom: int,
    ):
        world = self.game.world

        if world is None:
            return None

        frame_cells = []
        interior = []

        # 4x4 outer square = exactly 12 border frames and a 2x2 centre.
        for horizontal_offset in range(4):
            for vertical_offset in range(4):
                position = self._end_vertical_position(
                    axis,
                    fixed,
                    left + horizontal_offset,
                    bottom + vertical_offset,
                )

                border = (
                    horizontal_offset in (0, 3)
                    or vertical_offset in (0, 3)
                )

                if border:
                    if (
                        world.get_block(position)
                        != BlockType.END_PORTAL_FRAME_ACTIVE
                    ):
                        return None

                    frame_cells.append(position)
                    continue

                if world.get_block(position) is not None:
                    return None

                interior.append(position)

        if target not in frame_cells:
            return None

        return {
            "axis": axis,
            "cells": [list(cell) for cell in interior],
            "frame_cells": [list(cell) for cell in frame_cells],
            "return_portal": False,
        }

    def _check_horizontal_square_end_frame(
        self,
        target,
        left: int,
        y: int,
        front: int,
    ):
        world = self.game.world

        if world is None:
            return None

        frame_cells = []
        interior = []

        # Same 4x4 / twelve-frame outline, but lying flat.
        for x_offset in range(4):
            for z_offset in range(4):
                position = (
                    left + x_offset,
                    y,
                    front + z_offset,
                )

                border = (
                    x_offset in (0, 3)
                    or z_offset in (0, 3)
                )

                if border:
                    if (
                        world.get_block(position)
                        != BlockType.END_PORTAL_FRAME_ACTIVE
                    ):
                        return None

                    frame_cells.append(position)
                    continue

                if world.get_block(position) is not None:
                    return None

                interior.append(position)

        if target not in frame_cells:
            return None

        return {
            "axis": "horizontal",
            "cells": [list(cell) for cell in interior],
            "frame_cells": [list(cell) for cell in frame_cells],
            "return_portal": False,
        }

    def _check_classic_horizontal_end_frame(
        self,
        target,
        center_x: int,
        y: int,
        center_z: int,
    ):
        world = self.game.world

        if world is None:
            return None

        frame_cells = []

        # Minecraft-style ring: three frames on each side, corners omitted.
        for offset in (-1, 0, 1):
            frame_cells.extend(
                (
                    (center_x + offset, y, center_z - 2),
                    (center_x + offset, y, center_z + 2),
                    (center_x - 2, y, center_z + offset),
                    (center_x + 2, y, center_z + offset),
                )
            )

        # Remove duplicates defensively; there should be exactly twelve.
        frame_cells = list(dict.fromkeys(frame_cells))

        if len(frame_cells) != 12:
            return None

        if target not in frame_cells:
            return None

        for position in frame_cells:
            if (
                world.get_block(position)
                != BlockType.END_PORTAL_FRAME_ACTIVE
            ):
                return None

        interior = []

        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                position = (
                    center_x + dx,
                    y,
                    center_z + dz,
                )

                if world.get_block(position) is not None:
                    return None

                interior.append(position)

        return {
            "axis": "horizontal",
            "cells": [list(cell) for cell in interior],
            "frame_cells": [list(cell) for cell in frame_cells],
            "return_portal": False,
        }

    def _find_complete_end_portal(
        self,
        target,
    ):
        target = _grid_key(target)
        target_x, target_y, target_z = target

        # The user's upright 4x4 outline.
        for axis in ("x", "z"):
            fixed = (
                target_z
                if axis == "x"
                else target_x
            )

            target_horizontal = (
                target_x
                if axis == "x"
                else target_z
            )

            for local_horizontal in range(4):
                for local_vertical in range(4):
                    if not (
                        local_horizontal in (0, 3)
                        or local_vertical in (0, 3)
                    ):
                        continue

                    result = self._check_vertical_end_frame(
                        target,
                        axis,
                        fixed,
                        target_horizontal - local_horizontal,
                        target_y - local_vertical,
                    )

                    if result is not None:
                        return result

        # A flat 4x4 square with the same twelve-frame count.
        for local_x in range(4):
            for local_z in range(4):
                if not (
                    local_x in (0, 3)
                    or local_z in (0, 3)
                ):
                    continue

                result = self._check_horizontal_square_end_frame(
                    target,
                    target_x - local_x,
                    target_y,
                    target_z - local_z,
                )

                if result is not None:
                    return result

        # Also support the familiar horizontal 5x5 ring with missing corners.
        for center_x in range(target_x - 2, target_x + 3):
            for center_z in range(target_z - 2, target_z + 3):
                result = self._check_classic_horizontal_end_frame(
                    target,
                    center_x,
                    target_y,
                    center_z,
                )

                if result is not None:
                    return result

        return None

    def _end_portal_key(
        self,
        portal,
    ):
        return frozenset(
            tuple(cell)
            for cell in portal.get(
                "cells",
                [],
            )
        )

    def activate_end_portal(
        self,
        portal,
        show_message: bool = True,
    ) -> bool:
        cells = portal.get(
            "cells",
            [],
        )

        if not cells:
            return False

        current = self.end_portals[
            self.current_dimension
        ]

        portal_key = self._end_portal_key(
            portal
        )

        if any(
            self._end_portal_key(existing)
            == portal_key
            for existing in current
        ):
            return False

        current.append(
            copy.deepcopy(portal)
        )

        self._rebuild_runtime_effects()

        if show_message:
            self.game.ui.set_message(
                "The End portal opened."
            )

        return True

    def activate_end_portal_frame(
        self,
        position,
    ) -> bool:
        if self.game.world is None:
            return False

        key = _grid_key(position)
        block_type = self.game.world.get_block(
            key
        )

        if block_type == BlockType.END_PORTAL_FRAME_ACTIVE:
            self.game.ui.set_message(
                "That End Portal Frame is already activated."
            )
            return True

        if block_type != BlockType.END_PORTAL_FRAME:
            return False

        if not self.game.world.activate_end_portal_frame(
            key
        ):
            return False

        self.game.play_sound(
            "block"
        )

        portal = self._find_complete_end_portal(
            key
        )

        if portal is not None:
            self.activate_end_portal(
                portal,
                show_message=True,
            )
        else:
            self.game.ui.set_message(
                "End Portal Frame activated."
            )

        self.game.ui.update_hud()
        return True

    def is_protected_end_return_frame(
        self,
        position,
    ) -> bool:
        if self.current_dimension != END:
            return False

        key = _grid_key(
            position
        )

        for portal in self.end_portals[END]:
            if not portal.get(
                "return_portal",
                False,
            ):
                continue

            frame_cells = {
                tuple(cell)
                for cell in portal.get(
                    "frame_cells",
                    [],
                )
            }

            if key in frame_cells:
                return True

        return False

    def handle_end_frame_removed(
        self,
        position,
    ) -> None:
        key = _grid_key(position)

        portals = self.end_portals[
            self.current_dimension
        ]

        filtered = []
        changed = False

        for portal in portals:
            frame_cells = {
                tuple(cell)
                for cell in portal.get(
                    "frame_cells",
                    [],
                )
            }

            if key in frame_cells:
                changed = True
                continue

            filtered.append(portal)

        if changed:
            self.end_portals[
                self.current_dimension
            ] = filtered

            self._rebuild_runtime_effects()

    def _build_end_return_portal(
        self,
        world,
    ):
        if world is None:
            return None

        center_x = 8
        center_z = 0

        surface_heights = []

        for x in range(center_x - 2, center_x + 3):
            for z in range(center_z - 2, center_z + 3):
                height = world.end_surface_height(
                    x,
                    z,
                )

                if height is not None:
                    surface_heights.append(height)

        if not surface_heights:
            return None

        frame_y = max(surface_heights)

        # Flatten and clear a 5x5 return area on the End island.
        for x in range(center_x - 2, center_x + 3):
            for z in range(center_z - 2, center_z + 3):
                local_surface = world.end_surface_height(
                    x,
                    z,
                )

                if local_surface is None:
                    local_surface = frame_y - 1

                for y in range(local_surface + 1, frame_y + 1):
                    if (x, y, z) not in world.blocks:
                        world._store_block(
                            (x, y, z),
                            BlockType.END_STONE,
                        )

                for y in range(frame_y + 1, frame_y + 6):
                    if (x, y, z) in world.blocks:
                        world._erase_block(
                            (x, y, z)
                        )

        frame_cells = []

        for offset in (-1, 0, 1):
            frame_cells.extend(
                (
                    (center_x + offset, frame_y, center_z - 2),
                    (center_x + offset, frame_y, center_z + 2),
                    (center_x - 2, frame_y, center_z + offset),
                    (center_x + 2, frame_y, center_z + offset),
                )
            )

        frame_cells = list(dict.fromkeys(frame_cells))

        for position in frame_cells:
            if position in world.blocks:
                world._replace_block_type(
                    position,
                    BlockType.END_PORTAL_FRAME_ACTIVE,
                )
            else:
                world._store_block(
                    position,
                    BlockType.END_PORTAL_FRAME_ACTIVE,
                )

        interior = []

        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                position = (
                    center_x + dx,
                    frame_y,
                    center_z + dz,
                )

                if position in world.blocks:
                    world._erase_block(
                        position
                    )

                interior.append(position)

        world.rebuild_all_chunks()

        portal = {
            "axis": "horizontal",
            "cells": [list(cell) for cell in interior],
            "frame_cells": [list(cell) for cell in frame_cells],
            "return_portal": True,
        }

        self.end_portals[END] = [
            portal
        ]

        return portal

    # =========================================================
    # DIMENSION TRAVEL
    # =========================================================

    def _player_portal_cells(
        self,
    ):
        player = (
            self.game.player
        )

        if player is None:
            return set()

        x = math.floor(
            player.x + 0.5
        )

        z = math.floor(
            player.z + 0.5
        )

        cells = set()

        for y_offset in (
            0.0,
            0.65,
            1.25,
        ):
            y = math.floor(
                player.y
                + y_offset
                + 0.5
            )

            cells.add(
                (
                    x,
                    y,
                    z,
                )
            )

        return cells

    def _active_portal_cells(
        self,
    ):
        result = set()

        for portal in (
            self.portals[
                self.current_dimension
            ]
        ):
            for cell in portal.get(
                "cells",
                [],
            ):
                if (
                    isinstance(
                        cell,
                        (
                            list,
                            tuple,
                        ),
                    )
                    and len(
                        cell
                    )
                    == 3
                ):
                    result.add(
                        tuple(
                            int(value)
                            for value in cell
                        )
                    )

        return result

    def _player_inside_portal(
        self,
    ) -> bool:
        return bool(
            self._player_portal_cells()
            & self._active_portal_cells()
        )

    def _player_inside_end_portal(
        self,
    ) -> bool:
        player = self.game.player

        if player is None:
            return False

        player_cells = self._player_portal_cells()
        player_x = math.floor(
            player.x + 0.5
        )
        player_z = math.floor(
            player.z + 0.5
        )

        for portal in self.end_portals[
            self.current_dimension
        ]:
            axis = str(
                portal.get(
                    "axis",
                    "horizontal",
                )
            )

            cells = [
                tuple(
                    int(value)
                    for value in cell
                )
                for cell in portal.get(
                    "cells",
                    [],
                )
                if isinstance(
                    cell,
                    (list, tuple),
                )
                and len(cell) == 3
            ]

            if axis != "horizontal":
                if player_cells & set(cells):
                    return True

                continue

            for cell_x, cell_y, cell_z in cells:
                if (
                    player_x == cell_x
                    and player_z == cell_z
                    and (
                        cell_y - 1.5
                        <= player.y
                        <= cell_y + 1.6
                    )
                ):
                    return True

        return False

    def switch_dimension(
        self,
    ) -> None:
        if (
            self.game.world is None
            or self.game.player
            is None
        ):
            return

        from world import World

        old_dimension = (
            self.current_dimension
        )

        if old_dimension == END:
            return

        target_dimension = (
            NETHER
            if old_dimension
            == OVERWORLD
            else OVERWORLD
        )

        # Save the dimension exactly as it exists at the moment the player
        # enters the portal.
        current_state = (
            self.game.world
            .serialize_state()
        )

        self.dimension_states[
            old_dimension
        ] = current_state

        # The first Nether visit is a direct clone of the current Overworld.
        if (
            self.dimension_states[
                target_dimension
            ]
            is None
        ):
            self.dimension_states[
                target_dimension
            ] = copy.deepcopy(
                current_state
            )

        target_state = copy.deepcopy(
            self.dimension_states[
                target_dimension
            ]
        )

        player = (
            self.game.player
        )

        old_position = Vec3(
            player.position
        )

        self.game.hostile_mob_manager.clear()
        self.game.peaceful_mob_manager.clear()

        self.clear_runtime_effects()

        self.game.world.destroy()

        self.game.world = World(
            initial_state=target_state,
            dimension=target_dimension,
        )

        player.world = (
            self.game.world
        )

        player.position = (
            old_position
        )

        self.current_dimension = (
            target_dimension
        )

        self.game.current_dimension = (
            target_dimension
        )

        self._rebuild_runtime_effects()

        self.switch_cooldown = 0.8
        self.portal_latched = True

        if (
            getattr(
                self.game,
                "day_night",
                None,
            )
            is not None
        ):
            self.game.day_night.apply_visuals()

        self.game.ui.set_message(
            (
                "Entered the Nether."
                if target_dimension
                == NETHER
                else "Returned to the Overworld."
            )
        )

    def switch_end_dimension(
        self,
    ) -> None:
        if (
            self.game.world is None
            or self.game.player is None
        ):
            return

        from world import World

        old_dimension = self.current_dimension
        player = self.game.player
        old_position = Vec3(
            player.position
        )

        # Preserve the world we are leaving exactly as it is now.
        self.dimension_states[
            old_dimension
        ] = (
            self.game.world
            .serialize_state()
        )

        if old_dimension == END:
            target_dimension = self.end_return_dimension

            if target_dimension not in (
                OVERWORLD,
                NETHER,
            ):
                target_dimension = OVERWORLD

            target_state = copy.deepcopy(
                self.dimension_states.get(
                    target_dimension
                )
            )

            if target_state is None:
                target_state = copy.deepcopy(
                    self.dimension_states.get(
                        OVERWORLD
                    )
                )

            return_position = self.end_return_position

        else:
            target_dimension = END

            self.end_return_dimension = old_dimension
            self.end_return_position = [
                float(old_position.x),
                float(old_position.y),
                float(old_position.z),
            ]

            target_state = copy.deepcopy(
                self.dimension_states.get(
                    END
                )
            )

            return_position = None

        self.game.hostile_mob_manager.clear()
        self.game.peaceful_mob_manager.clear()

        self.clear_runtime_effects()

        self.game.world.destroy()

        # Passing None creates the End island the first time it is entered.
        self.game.world = World(
            initial_state=target_state,
            dimension=target_dimension,
        )

        player.world = self.game.world

        self.current_dimension = target_dimension
        self.game.current_dimension = target_dimension

        if target_dimension == END:
            if not self.end_portals[END]:
                self._build_end_return_portal(
                    self.game.world
                )

            player.position = (
                self.game.world
                .get_spawn_position()
            )

            # Save the generated End + its automatic return portal immediately.
            self.dimension_states[END] = (
                self.game.world
                .serialize_state()
            )

        else:
            if (
                isinstance(
                    return_position,
                    (list, tuple),
                )
                and len(return_position) == 3
            ):
                player.position = Vec3(
                    float(return_position[0]),
                    float(return_position[1]),
                    float(return_position[2]),
                )
            else:
                player.position = (
                    self.game.world
                    .get_spawn_position()
                )

        self._rebuild_runtime_effects()

        self.switch_cooldown = 0.9
        self.portal_latched = True

        if (
            getattr(
                self.game,
                "day_night",
                None,
            ) is not None
        ):
            self.game.day_night.apply_visuals()

        self.game.ui.set_message(
            (
                "Entered The End."
                if target_dimension == END
                else "Returned from The End."
            )
        )

    def update(
        self,
    ) -> None:
        if self.switch_cooldown > 0:
            self.switch_cooldown = max(
                0.0,
                self.switch_cooldown
                - time.dt,
            )

        if (
            not self.game.in_game
            or self.game.player
            is None
            or self.game.world
            is None
        ):
            return

        inside_end = (
            self._player_inside_end_portal()
        )

        inside_nether = (
            self._player_inside_portal()
        )

        if not (
            inside_end
            or inside_nether
        ):
            self.portal_latched = False
            return

        if (
            self.portal_latched
            or self.switch_cooldown > 0
        ):
            return

        if inside_end:
            self.switch_end_dimension()
            return

        self.switch_dimension()
