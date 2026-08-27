from __future__ import annotations

import math

from ursina import (
    Vec3,
    camera,
    held_keys,
    raycast,
    time,
)
from ursina.prefabs.first_person_controller import FirstPersonController

from blocks import BLOCKS, BlockType
from inventory import ItemType
from config import (
    PLAYER_GRAVITY,
    PLAYER_HEIGHT,
    PLAYER_JUMP_HEIGHT,
    PLAYER_SPRINT_SPEED,
    PLAYER_WALK_SPEED,
    REACH_DISTANCE,
    THIRD_PERSON_DISTANCE,
)


class MathcraftPlayer(FirstPersonController):
    def __init__(self, game, world, **kwargs):
        settings = game.world_settings

        kwargs.setdefault(
            "height",
            settings.player_height,
        )
        kwargs.setdefault(
            "speed",
            settings.player_walk_speed,
        )
        kwargs.setdefault(
            "gravity",
            settings.player_gravity,
        )
        kwargs.setdefault(
            "jump_height",
            settings.player_jump_height,
        )

        super().__init__(**kwargs)

        self.game = game
        self.world = world

        self.walk_speed = float(
            settings.player_walk_speed
        )
        self.sprint_speed = float(
            settings.player_sprint_speed
        )
        self.base_gravity = float(
            settings.player_gravity
        )
        self.gravity = self.base_gravity
        self.jump_height = float(
            settings.player_jump_height
        )
        self.reach_distance = float(
            settings.reach_distance
        )

        self.fly_mode = False
        self.debug_speed = None

        self.third_person = False
        self.third_person_distance = float(
            settings.third_person_distance
        )

        # Survival.
        self.max_health = float(
            settings.max_health
        )
        self.health = self.max_health

        self.max_oxygen = int(
            settings.max_oxygen
        )
        self.oxygen = self.max_oxygen

        self.oxygen_loss_timer = 0.0
        self.oxygen_recovery_timer = 0.0
        self.drowning_timer = 0.0
        self.lava_damage_timer = 0.0
        self.dead = False

        self.cursor.color = (
            self.game.ui.accent_color
        )

        self.apply_camera_settings()
        self.set_first_person()

        self.enabled = False

    # =========================================================
    # INVENTORY
    # =========================================================

    @property
    def selected_index(self) -> int:
        return self.game.inventory.selected_index

    @selected_index.setter
    def selected_index(
        self,
        value: int,
    ) -> None:
        self.game.inventory.select(
            value
        )

    @property
    def selected_block(
        self,
    ) -> BlockType | None:
        return self.game.inventory.selected_block

    @property
    def selected_item(
        self,
    ) -> ItemType | None:
        return self.game.inventory.selected_item

    def cycle_block(
        self,
        direction: int,
    ) -> None:
        self.game.inventory.cycle(
            direction
        )
        self.game.ui.update_hud()

    # =========================================================
    # CAMERA / DEBUG MOVEMENT
    # =========================================================

    def apply_camera_settings(self) -> None:
        camera.orthographic = False
        camera.fov = float(
            self.game.settings.fov
        )

    def set_first_person(self) -> None:
        self.third_person = False

        camera.parent = self.camera_pivot
        camera.position = Vec3(
            0,
            0,
            0,
        )
        camera.rotation = Vec3(
            0,
            0,
            0,
        )

        self.apply_camera_settings()

    def set_third_person(self) -> None:
        self.third_person = True
        camera.parent = self.camera_pivot
        camera.position = Vec3(
            0,
            0.20,
            -self.third_person_distance,
        )
        camera.rotation = Vec3(
            0,
            0,
            0,
        )

        self.apply_camera_settings()

    def toggle_camera_view(self) -> None:
        if self.third_person:
            self.set_first_person()
        else:
            self.set_third_person()

    def set_fly_mode(
        self,
        enabled: bool,
    ) -> None:
        self.fly_mode = bool(
            enabled
        )

        if self.fly_mode:
            self.gravity = 0
            self.grounded = False
            self.air_time = 0
        else:
            self.gravity = self.base_gravity

    def set_debug_speed(
        self,
        speed: float,
    ) -> None:
        self.debug_speed = max(
            1.0,
            min(
                30.0,
                float(speed),
            ),
        )

    def _update_fly_vertical(
        self,
    ) -> None:
        vertical = (
            held_keys["space"]
            - held_keys["left control"]
        )

        if vertical == 0:
            return

        fly_speed = (
            self.debug_speed
            if self.debug_speed
            is not None
            else self.sprint_speed
        )

        target_position = Vec3(
            self.position
        )

        target_position.y += (
            vertical
            * fly_speed
            * time.dt
        )

        if not self.world.player_overlaps_solid(
            target_position,
            self.height,
        ):
            self.position = (
                target_position
            )

    # =========================================================
    # INPUT
    # =========================================================

    def input(self, key):
        if not self.enabled:
            return

        if key == "e":
            if not self.dead:
                self.game.ui.toggle_inventory()
            return

        if self.game.ui.inventory_open:
            if key == "escape":
                self.game.ui.close_inventory()
            return

        if (
            self.game.ui.question_open
            or self.game.ui.pause_open
            or self.dead
        ):
            return

        if key == "f5":
            self.toggle_camera_view()
            return

        if (
            self.fly_mode
            and key == "space"
        ):
            return

        if key == "scroll up":
            self.cycle_block(1)
            return

        if key == "scroll down":
            self.cycle_block(-1)
            return

        if key in "123456789":
            self.selected_index = (
                int(key) - 1
            )
            self.game.ui.update_hud()
            return

        if key == "q":
            self.game.ui.open_math_question()
            return

        if key == "escape":
            self.game.ui.toggle_pause()
            return

        if key == "left mouse down":
            if self.try_hit_mob():
                return

            self.try_break_block()
            return

        if key == "right mouse down":
            if self.try_use_selected_item():
                return

            self.try_place_block()
            return

        super().input(key)

    # =========================================================
    # ZOMBIE COMBAT
    # =========================================================

    def try_hit_mob(
        self,
    ) -> bool:
        hit = raycast(
            camera.world_position,
            camera.forward,
            distance=self.reach_distance,
            ignore=[self],
        )

        if not hit.hit:
            return False

        mob = getattr(
            hit.entity,
            "mob",
            None,
        )

        # Backward compatibility with older zombie hitboxes.
        if mob is None:
            mob = getattr(
                hit.entity,
                "zombie",
                None,
            )

        if mob is None:
            return False

        mob.take_damage(
            1,
            attacker_position=self.position,
        )

        return True

    # =========================================================
    # WOODEN BUCKET
    # =========================================================

    def try_use_selected_item(
        self,
    ) -> bool:
        item_type = (
            self.selected_item
        )

        if item_type is None:
            return False

        if (
            item_type
            == ItemType.WOODEN_BUCKET
        ):
            self._try_scoop_bucket()
            return True

        if (
            item_type
            == ItemType.WATER_BUCKET
        ):
            self._try_empty_bucket(
                BlockType.WATER
            )
            return True

        if (
            item_type
            == ItemType.LAVA_BUCKET
        ):
            self._try_empty_bucket(
                BlockType.LAVA
            )
            return True

        if (
            item_type
            == ItemType.BED
        ):
            self._try_sleep_in_bed()
            return True

        if (
            item_type
            == ItemType.LIGHTER
        ):
            self._try_use_lighter()
            return True

        return False

    def _try_use_lighter(
        self,
    ) -> None:
        _block_position, target = (
            self._target_blocks()
        )

        # If no block is within reach, still allow the lighter to place
        # fire in the air cell at the end of the reach ray.
        if target is None:
            target_position = (
                camera.world_position
                + camera.forward
                * self.reach_distance
            )

            target = (
                self.world.key_from_vec(
                    target_position
                )
            )

        if (
            self.world.get_block(
                target
            )
            is not None
        ):
            self.game.ui.set_message(
                "That space is occupied."
            )
            return

        if (
            self.game.dimension_manager
            .place_fire(
                target
            )
        ):
            self.game.play_sound(
                "block"
            )

            self.game.ui.set_message(
                "Fire lit."
            )
        else:
            self.game.ui.set_message(
                "Could not light a fire there."
            )

    def _try_sleep_in_bed(
        self,
    ) -> None:
        day_night = getattr(
            self.game,
            "day_night",
            None,
        )

        if day_night is None:
            self.game.ui.set_message(
                "World time is unavailable."
            )
            return

        if not day_night.skip_to_morning():
            self.game.ui.set_message(
                "You can only sleep at night."
            )
            return

        self.game.ui.set_message(
            "Slept until 08:00."
        )

        self.game.ui.update_hud()

    def _try_scoop_bucket(
        self,
    ) -> None:
        block_position, _ = (
            self._target_blocks()
        )

        if block_position is None:
            self.game.ui.set_message(
                "Aim at water or lava."
            )
            return

        block_type = self.world.get_block(
            block_position
        )

        if block_type not in (
            BlockType.WATER,
            BlockType.LAVA,
        ):
            self.game.ui.set_message(
                "A wooden bucket can only scoop water or lava."
            )
            return

        scooped = (
            self.world.scoop_liquid(
                block_position
            )
        )

        if scooped is None:
            self.game.ui.set_message(
                "Could not scoop that liquid."
            )
            return

        new_item = (
            ItemType.WATER_BUCKET
            if scooped
            == BlockType.WATER
            else ItemType.LAVA_BUCKET
        )

        self.game.inventory.transform_selected(
            new_item
        )

        self.game.play_sound(
            "block"
        )

        self.game.ui.set_message(
            (
                "Scooped water."
                if scooped
                == BlockType.WATER
                else "Scooped lava."
            )
        )

        self.game.ui.update_hud()

    def _try_empty_bucket(
        self,
        liquid_type: BlockType,
    ) -> None:
        _block_position, target = (
            self._target_blocks()
        )

        if target is None:
            self.game.ui.set_message(
                "Aim at a block to place the liquid."
            )
            return

        placed = self.world.add_block(
            liquid_type,
            target,
        )

        if placed is None:
            self.game.ui.set_message(
                "There is already a block there."
            )
            return

        self.game.inventory.transform_selected(
            ItemType.WOODEN_BUCKET
        )

        self.game.play_sound(
            "block"
        )

        self.game.ui.set_message(
            (
                "Placed water."
                if liquid_type
                == BlockType.WATER
                else "Placed lava."
            )
        )

        self.game.ui.update_hud()

    # =========================================================
    # BLOCK INTERACTION
    # =========================================================

    def _target_blocks(self):
        return self.world.raycast_blocks(
            camera.world_position,
            camera.forward,
            self.reach_distance,
        )

    def try_break_block(self) -> None:
        block_position, _ = (
            self._target_blocks()
        )

        if block_position is None:
            return

        block_type = self.world.get_block(
            block_position
        )

        if block_type is None:
            return

        definition = BLOCKS[
            block_type
        ]

        if not definition.breakable:
            self.game.ui.set_message(
                "That block cannot be mined."
            )
            return

        if not self.game.inventory.can_add(
            block_type,
            1,
        ):
            self.game.ui.set_message(
                "Inventory full."
            )
            return

        if not self.game.spend_token(
            "mine a block"
        ):
            return

        removed = self.world.remove_block(
            block_position
        )

        if not removed:
            self.game.tokens += 1
            self.game.ui.set_message(
                "That block cannot be mined."
            )
            self.game.ui.update_hud()
            return

        self.game.inventory.add(
            block_type,
            1,
        )

        self.game.quest.record_mined()
        self.game.play_sound("block")
        self.game.check_quest_completion()
        self.game.ui.update_hud()

    def _block_overlaps_player(
        self,
        target,
    ) -> bool:
        block_x, block_y, block_z = (
            target
        )

        block_min_x = block_x - 0.5
        block_max_x = block_x + 0.5
        block_min_y = block_y - 0.5
        block_max_y = block_y + 0.5
        block_min_z = block_z - 0.5
        block_max_z = block_z + 0.5

        player_half_width = 0.30

        player_min_x = (
            self.x - player_half_width
        )
        player_max_x = (
            self.x + player_half_width
        )
        player_min_y = self.y
        player_max_y = (
            self.y + self.height
        )
        player_min_z = (
            self.z - player_half_width
        )
        player_max_z = (
            self.z + player_half_width
        )

        return (
            block_min_x < player_max_x
            and block_max_x > player_min_x
            and block_min_y < player_max_y
            and block_max_y > player_min_y
            and block_min_z < player_max_z
            and block_max_z > player_min_z
        )

    def try_place_block(self) -> None:
        block_type = (
            self.selected_block
        )

        if block_type is None:
            self.game.ui.set_message(
                "That inventory slot is empty."
            )
            return

        _block_position, target = (
            self._target_blocks()
        )

        if target is None:
            return

        if self._block_overlaps_player(
            target
        ):
            self.game.ui.set_message(
                "You can't place a block inside yourself."
            )
            return

        if not self.game.spend_token(
            "place a block"
        ):
            return

        rotation_y = 0

        if (
            block_type
            == BlockType.OAK_STAIRS
        ):
            rotation_y = (
                round(
                    self.rotation_y / 90
                )
                * 90
            )

        placed = self.world.add_block(
            block_type,
            target,
            rotation_y=rotation_y,
        )

        if placed is None:
            self.game.tokens += 1
            self.game.ui.set_message(
                "A block is already there."
            )
            self.game.ui.update_hud()
            return

        self.game.inventory.remove_selected(
            1
        )

        self.game.quest.record_placed()
        self.game.play_sound("block")
        self.game.check_quest_completion()
        self.game.ui.update_hud()

    # =========================================================
    # HEALTH + OXYGEN
    # =========================================================

    def restore_survival(
        self,
        health=None,
        oxygen=None,
    ) -> None:
        if health is None:
            health = self.max_health

        if oxygen is None:
            oxygen = self.max_oxygen

        self.health = max(
            0.0,
            min(
                self.max_health,
                round(
                    float(health)
                    * 2.0
                )
                / 2.0,
            ),
        )

        self.oxygen = max(
            0,
            min(
                self.max_oxygen,
                int(oxygen),
            ),
        )

        self.dead = False
        self.oxygen_loss_timer = 0.0
        self.oxygen_recovery_timer = 0.0
        self.drowning_timer = 0.0
        self.lava_damage_timer = 0.0

        self.game.ui.update_survival_ui()

    def take_damage(
        self,
        hearts: float,
        source: str = "",
    ) -> None:
        if (
            self.dead
            or hearts <= 0
        ):
            return

        damage = (
            round(
                float(hearts)
                * 2.0
            )
            / 2.0
        )

        self.health = max(
            0.0,
            self.health - damage,
        )

        self.game.ui.update_survival_ui()

        if self.health <= 0:
            self._die()

    def _die(self) -> None:
        if self.dead:
            return

        self.dead = True

        self.game.ui.set_message(
            "You died! Respawning..."
        )

        # Death/item dropping is not part of this phase.
        # The inventory is kept and the player immediately respawns.
        self.position = (
            self.world.get_spawn_position()
        )

        self.health = self.max_health
        self.oxygen = self.max_oxygen

        self.oxygen_loss_timer = 0.0
        self.oxygen_recovery_timer = 0.0
        self.drowning_timer = 0.0
        self.lava_damage_timer = 0.0

        self.dead = False

        self.game.ui.update_survival_ui()

    def _body_is_in_lava(
        self,
    ) -> bool:
        half_width = 0.30

        min_x = int(
            math.floor(
                self.x
                - half_width
                + 0.5
            )
        )

        max_x = int(
            math.floor(
                self.x
                + half_width
                + 0.5
            )
        )

        min_z = int(
            math.floor(
                self.z
                - half_width
                + 0.5
            )
        )

        max_z = int(
            math.floor(
                self.z
                + half_width
                + 0.5
            )
        )

        min_y = int(
            math.floor(
                self.y + 0.5
            )
        )

        max_y = int(
            math.floor(
                self.y
                + self.height
                + 0.5
            )
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
                    if (
                        self.world.get_block(
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
        settings = (
            self.game.world_settings
        )

        if not self._body_is_in_lava():
            self.lava_damage_timer = 0.0
            return

        self.lava_damage_timer += (
            time.dt
        )

        interval = float(
            settings.lava_damage_interval
        )

        while (
            self.lava_damage_timer
            >= interval
        ):
            self.lava_damage_timer -= (
                interval
            )

            self.take_damage(
                settings.lava_damage,
                source="lava",
            )

            if self.dead:
                break

    def _head_is_underwater(
        self,
    ) -> bool:
        head = Vec3(
            self.x,
            self.y + self.height,
            self.z,
        )

        cell = (
            int(
                math.floor(
                    head.x + 0.5
                )
            ),
            int(
                math.floor(
                    head.y + 0.5
                )
            ),
            int(
                math.floor(
                    head.z + 0.5
                )
            ),
        )

        return (
            self.world.get_block(
                cell
            )
            == BlockType.WATER
        )

    def _update_oxygen(
        self,
    ) -> None:
        settings = (
            self.game.world_settings
        )

        if self._head_is_underwater():
            self.oxygen_recovery_timer = 0.0

            if self.oxygen > 0:
                self.drowning_timer = 0.0

                self.oxygen_loss_timer += (
                    time.dt
                )

                interval = float(
                    settings.oxygen_loss_interval
                )

                while (
                    self.oxygen_loss_timer
                    >= interval
                    and self.oxygen > 0
                ):
                    self.oxygen_loss_timer -= (
                        interval
                    )

                    self.oxygen -= 1
                    self.game.ui.update_survival_ui()

            else:
                self.oxygen_loss_timer = 0.0

                self.drowning_timer += (
                    time.dt
                )

                damage_interval = float(
                    settings.drowning_damage_interval
                )

                while (
                    self.drowning_timer
                    >= damage_interval
                ):
                    self.drowning_timer -= (
                        damage_interval
                    )

                    self.take_damage(
                        settings.drowning_damage,
                        source="drowning",
                    )

                    if self.dead:
                        break

        else:
            self.oxygen_loss_timer = 0.0
            self.drowning_timer = 0.0

            if self.oxygen < self.max_oxygen:
                self.oxygen_recovery_timer += (
                    time.dt
                )

                interval = float(
                    settings.oxygen_recovery_interval
                )

                while (
                    self.oxygen_recovery_timer
                    >= interval
                    and self.oxygen
                    < self.max_oxygen
                ):
                    self.oxygen_recovery_timer -= (
                        interval
                    )

                    self.oxygen += 1
                    self.game.ui.update_survival_ui()

            else:
                self.oxygen_recovery_timer = 0.0

    # =========================================================
    # FRAME UPDATE
    # =========================================================

    def jump(self) -> None:
        super().jump()

    def update(self) -> None:
        if not self.enabled:
            return

        if (
            self.game.ui.question_open
            or self.game.ui.pause_open
            or self.game.ui.inventory_open
        ):
            return

        normal_speed = (
            self.sprint_speed
            if held_keys["left shift"]
            else self.walk_speed
        )

        self.speed = (
            self.debug_speed
            if self.debug_speed
            is not None
            else normal_speed
        )

        if self.fly_mode:
            self.gravity = 0
        else:
            self.gravity = (
                self.base_gravity
            )

        super().update()

        if self.fly_mode:
            self.grounded = False
            self.air_time = 0
            self._update_fly_vertical()

        self._update_oxygen()
        self._update_lava_damage()

        if (
            int(camera.fov)
            != int(
                self.game.settings.fov
            )
        ):
            self.apply_camera_settings()

        if self.y < -20:
            self.position = (
                self.world.get_spawn_position()
            )
