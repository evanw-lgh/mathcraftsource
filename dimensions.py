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
        }

        self.portals = {
            OVERWORLD: [],
            NETHER: [],
        }

        self.fire_positions = {
            OVERWORLD: set(),
            NETHER: set(),
        }

        self.fire_entities = []
        self.portal_entities = []

        self.portal_latched = False
        self.switch_cooldown = 0.0

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
        }

        self.portals = {
            OVERWORLD: [],
            NETHER: [],
        }

        self.fire_positions = {
            OVERWORLD: set(),
            NETHER: set(),
        }

        self.portal_latched = False
        self.switch_cooldown = 0.0

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

            requested_dimension = str(
                raw_state.get(
                    "current_dimension",
                    OVERWORLD,
                )
            ).lower()

            if requested_dimension not in (
                OVERWORLD,
                NETHER,
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

            state = self.dimension_states.get(
                requested_dimension
            )

            if state is None:
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
            },
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

    def clear_runtime_effects(
        self,
    ) -> None:
        self._destroy_fire_entities()
        self._destroy_portal_entities()

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

        inside = (
            self._player_inside_portal()
        )

        if not inside:
            self.portal_latched = False
            return

        if (
            self.portal_latched
            or self.switch_cooldown > 0
        ):
            return

        self.switch_dimension()
