from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from blocks import BlockType


HOTBAR_SLOT_COUNT = 9
MAIN_INVENTORY_SLOT_COUNT = 27

INVENTORY_SLOT_COUNT = (
    HOTBAR_SLOT_COUNT
    + MAIN_INVENTORY_SLOT_COUNT
)

INVENTORY_STACK_LIMIT = 64
CRAFTING_SLOT_COUNT = 4


# =========================================================
# NON-BLOCK ITEMS
# =========================================================

class ItemType(str, Enum):
    WOODEN_BUCKET = "WOODEN_BUCKET"
    WATER_BUCKET = "WATER_BUCKET"
    LAVA_BUCKET = "LAVA_BUCKET"

    ROTTEN_FLESH = "ROTTEN_FLESH"
    WOOL = "WOOL"
    BED = "BED"
    LIGHTER = "LIGHTER"


ITEM_DISPLAY_NAMES = {
    ItemType.WOODEN_BUCKET:
        "Wooden Bucket",

    ItemType.WATER_BUCKET:
        "Water Bucket",

    ItemType.LAVA_BUCKET:
        "Lava Bucket",

    ItemType.ROTTEN_FLESH:
        "Rotten Flesh",

    ItemType.WOOL:
        "Wool",

    ItemType.BED:
        "Bed",

    ItemType.LIGHTER:
        "Lighter",
}


# Files are loaded from:
#
#     assets/items/
#
ITEM_TEXTURES = {
    ItemType.WOODEN_BUCKET:
        "wooden_bucket.png",

    ItemType.WATER_BUCKET:
        "wooden_bucket_water.png",

    ItemType.LAVA_BUCKET:
        "wooden_bucket_lava.png",

    ItemType.ROTTEN_FLESH:
        "rotten_flesh.png",

    ItemType.WOOL:
        "wool.png",

    # No custom bed image was supplied yet.
    # ui.py automatically shows missing.png while bed.png is absent.
    ItemType.BED:
        "bed.png",

    ItemType.LIGHTER:
        "lighter.png",
}


ITEM_STACK_LIMITS = {
    ItemType.WOODEN_BUCKET: 1,
    ItemType.WATER_BUCKET: 1,
    ItemType.LAVA_BUCKET: 1,

    ItemType.ROTTEN_FLESH: 64,
    ItemType.WOOL: 64,
    ItemType.BED: 1,
    ItemType.LIGHTER: 1,
}


InventoryValue = (
    BlockType
    | ItemType
)


def inventory_display_name(
    value: InventoryValue | None,
) -> str:
    if value is None:
        return "Empty"

    if isinstance(
        value,
        BlockType,
    ):
        from blocks import BLOCKS

        return BLOCKS[
            value
        ].display_name

    return ITEM_DISPLAY_NAMES.get(
        value,
        value.value.replace(
            "_",
            " ",
        ).title(),
    )


def inventory_stack_limit(
    value: InventoryValue,
) -> int:
    if isinstance(
        value,
        ItemType,
    ):
        return ITEM_STACK_LIMITS.get(
            value,
            1,
        )

    return INVENTORY_STACK_LIMIT


# =========================================================
# 2x2 CRAFTING RECIPES
# =========================================================
#
# Crafting slot positions:
#
#     0  1
#     2  3
#
# The wooden bucket recipe is intentionally exactly:
#
#     plank  empty
#     empty  plank
#
# as requested.
#
CRAFTING_RECIPES = (
    {
        "kind": "shapeless",

        "inputs": {
            BlockType.OAK_LOG: 1,
        },

        "output":
            BlockType.OAK_PLANKS,

        "count": 4,
    },

    {
        "kind": "pattern",

        "pattern": (
            BlockType.OAK_PLANKS,
            None,
            None,
            BlockType.OAK_PLANKS,
        ),

        "output":
            ItemType.WOODEN_BUCKET,

        "count": 1,
    },

    # Bed recipe:
    #
    #     wool   wool
    #     plank  plank
    #
    {
        "kind": "pattern",

        "pattern": (
            ItemType.WOOL,
            ItemType.WOOL,
            BlockType.OAK_PLANKS,
            BlockType.OAK_PLANKS,
        ),

        "output":
            ItemType.BED,

        "count": 1,
    },

    # Lighter recipe:
    #
    #     lava bucket   empty
    #     empty         lava bucket
    #
    {
        "kind": "pattern",

        "pattern": (
            ItemType.LAVA_BUCKET,
            None,
            None,
            ItemType.LAVA_BUCKET,
        ),

        "output":
            ItemType.LIGHTER,

        "count": 1,
    },
)


@dataclass
class InventorySlot:
    value: InventoryValue | None = None
    count: int = 0

    @property
    def block_type(
        self,
    ) -> BlockType | None:
        if isinstance(
            self.value,
            BlockType,
        ):
            return self.value

        return None

    @property
    def item_type(
        self,
    ) -> ItemType | None:
        if isinstance(
            self.value,
            ItemType,
        ):
            return self.value

        return None

    def empty(self) -> bool:
        return (
            self.value is None
            or self.count <= 0
        )

    def clear(self) -> None:
        self.value = None
        self.count = 0

    def copy(self) -> "InventorySlot":
        return InventorySlot(
            self.value,
            self.count,
        )


class Inventory:
    def __init__(self):
        # 0..8  = hotbar
        # 9..35 = storage
        self.slots = [
            InventorySlot()
            for _ in range(
                INVENTORY_SLOT_COUNT
            )
        ]

        self.selected_index = 0

        self.crafting_slots = [
            InventorySlot()
            for _ in range(
                CRAFTING_SLOT_COUNT
            )
        ]

        self.cursor_slot = (
            InventorySlot()
        )

    # =========================================================
    # HOTBAR
    # =========================================================

    @property
    def selected_slot(
        self,
    ) -> InventorySlot:
        return self.slots[
            self.selected_index
        ]

    @property
    def selected_value(
        self,
    ) -> InventoryValue | None:
        slot = self.selected_slot

        if slot.empty():
            return None

        return slot.value

    @property
    def selected_block(
        self,
    ) -> BlockType | None:
        return (
            self.selected_slot.block_type
        )

    @property
    def selected_item(
        self,
    ) -> ItemType | None:
        return (
            self.selected_slot.item_type
        )

    def select(
        self,
        index: int,
    ) -> None:
        self.selected_index = max(
            0,
            min(
                HOTBAR_SLOT_COUNT - 1,
                int(index),
            ),
        )

    def cycle(
        self,
        direction: int,
    ) -> None:
        self.selected_index = (
            self.selected_index
            + int(direction)
        ) % HOTBAR_SLOT_COUNT

    def transform_selected(
        self,
        value: InventoryValue,
    ) -> bool:
        slot = self.selected_slot

        if (
            slot.empty()
            or slot.count != 1
        ):
            return False

        slot.value = value
        slot.count = 1

        return True

    # =========================================================
    # STACK HELPERS
    # =========================================================

    @staticmethod
    def _move_between_slots(
        source: InventorySlot,
        target: InventorySlot,
    ) -> None:
        if source.empty():
            return

        source_limit = (
            inventory_stack_limit(
                source.value
            )
        )

        if target.empty():
            moved = min(
                source.count,
                source_limit,
            )

            target.value = (
                source.value
            )
            target.count = moved

            source.count -= moved

            if source.count <= 0:
                source.clear()

            return

        if (
            target.value
            == source.value
        ):
            target_limit = (
                inventory_stack_limit(
                    target.value
                )
            )

            free_space = (
                target_limit
                - target.count
            )

            if free_space <= 0:
                return

            moved = min(
                free_space,
                source.count,
            )

            target.count += moved
            source.count -= moved

            if source.count <= 0:
                source.clear()

            return

        source.value, target.value = (
            target.value,
            source.value,
        )

        source.count, target.count = (
            target.count,
            source.count,
        )

    # =========================================================
    # INVENTORY STORAGE
    # =========================================================

    def can_add(
        self,
        value: InventoryValue,
        count: int = 1,
    ) -> bool:
        remaining = max(
            0,
            int(count),
        )

        limit = inventory_stack_limit(
            value
        )

        for slot in self.slots:
            if (
                slot.value == value
                and slot.count < limit
            ):
                remaining -= (
                    limit
                    - slot.count
                )

                if remaining <= 0:
                    return True

        for slot in self.slots:
            if slot.empty():
                remaining -= limit

                if remaining <= 0:
                    return True

        return remaining <= 0

    def add(
        self,
        value: InventoryValue,
        count: int = 1,
    ) -> bool:
        if not self.can_add(
            value,
            count,
        ):
            return False

        remaining = max(
            0,
            int(count),
        )

        limit = inventory_stack_limit(
            value
        )

        for slot in self.slots:
            if (
                slot.value == value
                and slot.count < limit
            ):
                amount = min(
                    limit - slot.count,
                    remaining,
                )

                slot.count += amount
                remaining -= amount

                if remaining <= 0:
                    return True

        for slot in self.slots:
            if slot.empty():
                amount = min(
                    limit,
                    remaining,
                )

                slot.value = value
                slot.count = amount

                remaining -= amount

                if remaining <= 0:
                    return True

        return remaining <= 0

    def remove_selected(
        self,
        count: int = 1,
    ) -> bool:
        slot = self.selected_slot

        amount = max(
            1,
            int(count),
        )

        if (
            slot.empty()
            or slot.count < amount
        ):
            return False

        slot.count -= amount

        if slot.count <= 0:
            slot.clear()

        return True

    # =========================================================
    # INVENTORY SCREEN CLICKS
    # =========================================================

    def click_inventory_slot(
        self,
        index: int,
    ) -> None:
        if not (
            0
            <= index
            < len(self.slots)
        ):
            return

        target = self.slots[
            index
        ]

        if self.cursor_slot.empty():
            if target.empty():
                return

            self.cursor_slot.value = (
                target.value
            )

            self.cursor_slot.count = (
                target.count
            )

            target.clear()

            return

        self._move_between_slots(
            self.cursor_slot,
            target,
        )

    def click_crafting_slot(
        self,
        index: int,
    ) -> None:
        if not (
            0
            <= index
            < CRAFTING_SLOT_COUNT
        ):
            return

        target = (
            self.crafting_slots[
                index
            ]
        )

        if self.cursor_slot.empty():
            if target.empty():
                return

            self.cursor_slot.value = (
                target.value
            )

            self.cursor_slot.count = (
                target.count
            )

            target.clear()

            return

        self._move_between_slots(
            self.cursor_slot,
            target,
        )

    # =========================================================
    # 2x2 CRAFTING
    # =========================================================

    def _matches_pattern(
        self,
        pattern,
    ) -> bool:
        for index, required in enumerate(
            pattern
        ):
            slot = (
                self.crafting_slots[
                    index
                ]
            )

            if required is None:
                if not slot.empty():
                    return False

                continue

            if (
                slot.empty()
                or slot.value != required
                or slot.count < 1
            ):
                return False

        return True

    def _matches_shapeless(
        self,
        inputs,
    ) -> bool:
        totals = {}

        for slot in (
            self.crafting_slots
        ):
            if slot.empty():
                continue

            if slot.value not in inputs:
                return False

            totals[
                slot.value
            ] = (
                totals.get(
                    slot.value,
                    0,
                )
                + slot.count
            )

        for value, required in (
            inputs.items()
        ):
            if totals.get(
                value,
                0,
            ) < required:
                return False

        return bool(
            inputs
        )

    def matching_recipe(
        self,
    ):
        for recipe in (
            CRAFTING_RECIPES
        ):
            kind = recipe.get(
                "kind",
                "shapeless",
            )

            if kind == "pattern":
                if self._matches_pattern(
                    recipe["pattern"]
                ):
                    return recipe

            elif self._matches_shapeless(
                recipe["inputs"]
            ):
                return recipe

        return None

    def crafting_result(
        self,
    ) -> InventorySlot:
        recipe = (
            self.matching_recipe()
        )

        if recipe is None:
            return InventorySlot()

        return InventorySlot(
            recipe["output"],
            int(
                recipe["count"]
            ),
        )

    def _cursor_can_take(
        self,
        result: InventorySlot,
    ) -> bool:
        if result.empty():
            return False

        result_limit = (
            inventory_stack_limit(
                result.value
            )
        )

        if self.cursor_slot.empty():
            return (
                result.count
                <= result_limit
            )

        if (
            self.cursor_slot.value
            != result.value
        ):
            return False

        return (
            self.cursor_slot.count
            + result.count
            <= result_limit
        )

    def _consume_recipe_inputs(
        self,
        recipe,
    ) -> None:
        if recipe.get(
            "kind"
        ) == "pattern":
            pattern = recipe[
                "pattern"
            ]

            for index, required in (
                enumerate(
                    pattern
                )
            ):
                if required is None:
                    continue

                slot = (
                    self.crafting_slots[
                        index
                    ]
                )

                slot.count -= 1

                if slot.count <= 0:
                    slot.clear()

            return

        remaining = dict(
            recipe["inputs"]
        )

        for slot in (
            self.crafting_slots
        ):
            if slot.empty():
                continue

            needed = remaining.get(
                slot.value,
                0,
            )

            if needed <= 0:
                continue

            consumed = min(
                needed,
                slot.count,
            )

            slot.count -= consumed

            remaining[
                slot.value
            ] -= consumed

            if slot.count <= 0:
                slot.clear()

    def take_crafting_result(
        self,
    ) -> bool:
        recipe = (
            self.matching_recipe()
        )

        if recipe is None:
            return False

        result = InventorySlot(
            recipe["output"],
            int(
                recipe["count"]
            ),
        )

        if not self._cursor_can_take(
            result
        ):
            return False

        self._consume_recipe_inputs(
            recipe
        )

        if self.cursor_slot.empty():
            self.cursor_slot.value = (
                result.value
            )

            self.cursor_slot.count = (
                result.count
            )

        else:
            self.cursor_slot.count += (
                result.count
            )

        return True

    # =========================================================
    # LEFT-CLICK DRAG SPREAD
    # =========================================================

    def _spread_target_slot(
        self,
        target_type: str,
        index: int,
    ) -> InventorySlot | None:
        if target_type == "inventory":
            if (
                0
                <= index
                < len(self.slots)
            ):
                return self.slots[
                    index
                ]

            return None

        if target_type == "crafting":
            if (
                0
                <= index
                < len(
                    self.crafting_slots
                )
            ):
                return self.crafting_slots[
                    index
                ]

            return None

        return None

    def spread_cursor_stack(
        self,
        targets,
    ) -> bool:
        """
        Minecraft-style left-click drag spreading.

        While holding an item stack on the cursor, drag across several
        inventory/crafting slots. On release the held stack is distributed
        as evenly as possible across all compatible visited slots.
        """
        if self.cursor_slot.empty():
            return False

        value = self.cursor_slot.value

        stack_limit = (
            inventory_stack_limit(
                value
            )
        )

        unique_targets = []
        seen = set()

        for target_type, index in targets:
            key = (
                str(target_type),
                int(index),
            )

            if key in seen:
                continue

            slot = self._spread_target_slot(
                target_type,
                index,
            )

            if slot is None:
                continue

            # You may spread into an empty slot or onto the same item.
            if (
                not slot.empty()
                and slot.value != value
            ):
                continue

            if (
                not slot.empty()
                and slot.count
                >= stack_limit
            ):
                continue

            seen.add(
                key
            )

            unique_targets.append(
                slot
            )

        if not unique_targets:
            return False

        remaining = (
            self.cursor_slot.count
        )

        # Keep making rounds so the stack is distributed evenly:
        # one item into each visited slot per round.
        changed = False

        while remaining > 0:
            placed_this_round = False

            for slot in unique_targets:
                if remaining <= 0:
                    break

                if slot.empty():
                    slot.value = value
                    slot.count = 0

                if slot.count >= stack_limit:
                    continue

                slot.count += 1
                remaining -= 1

                placed_this_round = True
                changed = True

            if not placed_this_round:
                break

        self.cursor_slot.count = (
            remaining
        )

        if self.cursor_slot.count <= 0:
            self.cursor_slot.clear()

        return changed

    # =========================================================
    # CLOSING INVENTORY
    # =========================================================

    def _return_slot_to_inventory(
        self,
        slot: InventorySlot,
    ) -> bool:
        if slot.empty():
            return True

        if not self.can_add(
            slot.value,
            slot.count,
        ):
            return False

        self.add(
            slot.value,
            slot.count,
        )

        slot.clear()

        return True

    def return_temporary_items(
        self,
    ) -> bool:
        if not self._return_slot_to_inventory(
            self.cursor_slot
        ):
            return False

        for slot in (
            self.crafting_slots
        ):
            if not self._return_slot_to_inventory(
                slot
            ):
                return False

        return True

    # =========================================================
    # SAVE / LOAD
    # =========================================================

    @staticmethod
    def _slot_to_dict(
        slot: InventorySlot,
    ) -> dict:
        if slot.value is None:
            return {
                "kind": None,
                "value": None,
                "count": 0,
            }

        kind = (
            "block"
            if isinstance(
                slot.value,
                BlockType,
            )
            else "item"
        )

        return {
            "kind": kind,
            "value": slot.value.value,
            "count": int(
                slot.count
            ),
        }

    @staticmethod
    def _slot_from_dict(
        raw,
    ) -> InventorySlot:
        if not isinstance(
            raw,
            dict,
        ):
            return InventorySlot()

        count = max(
            0,
            int(
                raw.get(
                    "count",
                    0,
                )
            ),
        )

        if count <= 0:
            return InventorySlot()

        # New format.
        kind = raw.get(
            "kind"
        )

        raw_value = raw.get(
            "value"
        )

        value = None

        try:
            if kind == "item":
                value = ItemType(
                    raw_value
                )

            elif kind == "block":
                value = BlockType(
                    raw_value
                )

            # Backward compatibility with old saves:
            # {"block": "OAK_LOG", "count": 3}
            elif raw.get(
                "block"
            ) is not None:
                value = BlockType(
                    raw.get(
                        "block"
                    )
                )

            elif raw_value is not None:
                try:
                    value = BlockType(
                        raw_value
                    )
                except ValueError:
                    value = ItemType(
                        raw_value
                    )

        except (
            ValueError,
            TypeError,
        ):
            return InventorySlot()

        if value is None:
            return InventorySlot()

        count = min(
            count,
            inventory_stack_limit(
                value
            ),
        )

        return InventorySlot(
            value,
            count,
        )

    def serialize(
        self,
    ) -> dict:
        return {
            "selected_index": (
                self.selected_index
            ),

            "slots": [
                self._slot_to_dict(
                    slot
                )
                for slot in self.slots
            ],

            "crafting": [
                self._slot_to_dict(
                    slot
                )
                for slot
                in self.crafting_slots
            ],

            "cursor": (
                self._slot_to_dict(
                    self.cursor_slot
                )
            ),
        }

    def restore(
        self,
        state,
    ) -> None:
        self.slots = [
            InventorySlot()
            for _ in range(
                INVENTORY_SLOT_COUNT
            )
        ]

        self.crafting_slots = [
            InventorySlot()
            for _ in range(
                CRAFTING_SLOT_COUNT
            )
        ]

        self.cursor_slot = (
            InventorySlot()
        )

        if not isinstance(
            state,
            dict,
        ):
            self.selected_index = 0
            return

        self.select(
            state.get(
                "selected_index",
                0,
            )
        )

        data = state.get(
            "slots",
            [],
        )

        if isinstance(
            data,
            list,
        ):
            for index, raw in enumerate(
                data[
                    :INVENTORY_SLOT_COUNT
                ]
            ):
                self.slots[
                    index
                ] = self._slot_from_dict(
                    raw
                )

        crafting = state.get(
            "crafting",
            [],
        )

        if isinstance(
            crafting,
            list,
        ):
            for index, raw in enumerate(
                crafting[
                    :CRAFTING_SLOT_COUNT
                ]
            ):
                self.crafting_slots[
                    index
                ] = self._slot_from_dict(
                    raw
                )

        self.cursor_slot = (
            self._slot_from_dict(
                state.get(
                    "cursor"
                )
            )
        )
