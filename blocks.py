from dataclasses import dataclass
from enum import Enum


class BlockType(str, Enum):
    OAK_LOG = "OAK_LOG"
    OAK_LEAVES = "OAK_LEAVES"
    GRASS_BLOCK = "GRASS_BLOCK"
    DIRT = "DIRT"
    WATER = "WATER"
    LAVA = "LAVA"
    OBSIDIAN = "OBSIDIAN"
    END_STONE = "END_STONE"
    END_PORTAL_FRAME = "END_PORTAL_FRAME"
    END_PORTAL_FRAME_ACTIVE = "END_PORTAL_FRAME_ACTIVE"
    OAK_PLANKS = "OAK_PLANKS"
    GLASS = "GLASS"
    OAK_STAIRS = "OAK_STAIRS"


@dataclass(frozen=True)
class BlockDefinition:
    block_type: BlockType
    display_name: str
    solid: bool = True
    transparent: bool = False
    liquid: bool = False
    breakable: bool = True


BLOCKS = {
    BlockType.OAK_LOG: BlockDefinition(
        BlockType.OAK_LOG,
        "Oak Log",
    ),

    BlockType.OAK_LEAVES: BlockDefinition(
        BlockType.OAK_LEAVES,
        "Oak Leaves",
        transparent=True,
    ),

    BlockType.GRASS_BLOCK: BlockDefinition(
        BlockType.GRASS_BLOCK,
        "Grass Block",
    ),

    BlockType.DIRT: BlockDefinition(
        BlockType.DIRT,
        "Dirt",
    ),

    BlockType.WATER: BlockDefinition(
        BlockType.WATER,
        "Water",
        solid=False,
        transparent=True,
        liquid=True,
        breakable=False,
    ),

    BlockType.LAVA: BlockDefinition(
        BlockType.LAVA,
        "Lava",
        solid=False,
        transparent=True,
        liquid=True,
        breakable=False,
    ),

    BlockType.OBSIDIAN: BlockDefinition(
        BlockType.OBSIDIAN,
        "Obsidian",
        solid=True,
        transparent=False,
        liquid=False,
        breakable=True,
    ),

    BlockType.END_STONE: BlockDefinition(
        BlockType.END_STONE,
        "End Stone",
        solid=True,
        transparent=False,
        liquid=False,
        breakable=True,
    ),

    BlockType.END_PORTAL_FRAME: BlockDefinition(
        BlockType.END_PORTAL_FRAME,
        "End Portal Frame",
        solid=True,
        transparent=True,
        liquid=False,
        breakable=True,
    ),

    BlockType.END_PORTAL_FRAME_ACTIVE: BlockDefinition(
        BlockType.END_PORTAL_FRAME_ACTIVE,
        "Activated End Portal Frame",
        solid=True,
        transparent=True,
        liquid=False,
        breakable=True,
    ),

    BlockType.OAK_PLANKS: BlockDefinition(
        BlockType.OAK_PLANKS,
        "Oak Planks",
    ),

    BlockType.GLASS: BlockDefinition(
        BlockType.GLASS,
        "Glass",
        transparent=True,
    ),

    BlockType.OAK_STAIRS: BlockDefinition(
        BlockType.OAK_STAIRS,
        "Oak Stairs",
    ),
}


PLACEABLE_BLOCKS = [
    BlockType.GRASS_BLOCK,
    BlockType.DIRT,
    BlockType.OAK_LOG,
    BlockType.OAK_LEAVES,
    BlockType.OBSIDIAN,
    BlockType.END_STONE,
    BlockType.END_PORTAL_FRAME,
    BlockType.OAK_PLANKS,
    BlockType.GLASS,
    BlockType.OAK_STAIRS,
]
