from __future__ import annotations

from pathlib import Path

from ursina import load_texture

from config import TEXTURE_DIR


# =========================================================
# EDITABLE SPECIAL BLOCK TEXTURES
# =========================================================
# Put these files in: assets/textures/
SPECIAL_BLOCK_TEXTURES = {
    "WATER": "water.png",
    "LAVA": "lava.png",
    "OBSIDIAN": "obsidian.png",
}


ATLAS_FILENAME = "block_atlas.png"
ATLAS_COLUMNS = 4
ATLAS_ROWS = 4

# Atlas coordinates are bottom-origin because Ursina UVs use bottom-left.
ATLAS_TILES = {
    "missing": (0, 3),
    "grass_top": (1, 3),
    "grass_side": (2, 3),
    "dirt": (3, 3),

    "stone": (0, 2),
    "water": (1, 2),
    "oak_log_top": (2, 2),
    "oak_log_side": (3, 2),

    "leaves": (0, 1),
    "oak_planks": (1, 1),
    "glass": (2, 1),
}

# Face order:
# top, north, south, east, west, bottom
BLOCK_FACE_TILES = {
    "OAK_LOG": (
        "oak_log_top",
        "oak_log_side",
        "oak_log_side",
        "oak_log_side",
        "oak_log_side",
        "oak_log_top",
    ),

    "OAK_LEAVES": (
        "leaves",
    ) * 6,

    "GRASS_BLOCK": (
        "grass_top",
        "grass_side",
        "grass_side",
        "grass_side",
        "grass_side",
        "dirt",
    ),

    "DIRT": (
        "dirt",
    ) * 6,

    "WATER": (
        "water",
    ) * 6,

    "LAVA": (
        "missing",
    ) * 6,

    "OBSIDIAN": (
        "missing",
    ) * 6,

    "OAK_PLANKS": (
        "oak_planks",
    ) * 6,

    "GLASS": (
        "glass",
    ) * 6,

    "OAK_STAIRS": (
        "oak_planks",
    ) * 6,
}

BLOCK_TEXTURES = {
    "OAK_LOG": (
        "oak_log_top.png",
        "oak_log_side.png",
        "oak_log_side.png",
        "oak_log_side.png",
        "oak_log_side.png",
        "oak_log_top.png",
    ),
    "OAK_LEAVES": ("leaves.png",) * 6,
    "GRASS_BLOCK": (
        "grass_block_top.png",
        "grass_block_side.png",
        "grass_block_side.png",
        "grass_block_side.png",
        "grass_block_side.png",
        "grass_block_bottom.png",
    ),
    "DIRT": ("dirt.png",) * 6,
    "WATER": (SPECIAL_BLOCK_TEXTURES["WATER"],) * 6,
    "LAVA": (SPECIAL_BLOCK_TEXTURES["LAVA"],) * 6,
    "OBSIDIAN": (SPECIAL_BLOCK_TEXTURES["OBSIDIAN"],) * 6,
    "OAK_PLANKS": ("oak_planks.png",) * 6,
    "GLASS": ("glass.png",) * 6,
    "OAK_STAIRS": ("oak_planks.png",) * 6,
}

MISSING_TEXTURE = "missing.png"

_texture_cache = {}
_atlas_texture = None
_face_uv_cache = {}


def _required_path(
    filename: str,
) -> Path:
    path = (
        TEXTURE_DIR
        / filename
    )

    if not path.exists():
        raise FileNotFoundError(
            f"Mathcraft texture is missing: {path}"
        )

    return path


def get_texture(
    filename: str,
):
    path = _required_path(
        filename
    )

    key = str(
        path.resolve()
    )

    if key not in _texture_cache:
        texture = load_texture(
            path.name,
            folder=path.parent,
        )

        if texture is None:
            raise RuntimeError(
                f"Ursina could not load texture: {path}"
            )

        texture.filtering = "nearest"
        texture.repeat = False

        _texture_cache[
            key
        ] = texture

    return _texture_cache[
        key
    ]


def get_atlas_texture():
    global _atlas_texture

    if _atlas_texture is None:
        _atlas_texture = get_texture(
            ATLAS_FILENAME
        )

        _atlas_texture.filtering = "nearest"
        _atlas_texture.repeat = False

    return _atlas_texture


# Local UV direction for each face.
_FACE_UV_PATTERN = (
    # top
    (
        (0.0, 0.0),
        (0.0, 1.0),
        (1.0, 1.0),
        (1.0, 0.0),
    ),
    # north
    (
        (0.0, 0.0),
        (1.0, 0.0),
        (1.0, 1.0),
        (0.0, 1.0),
    ),
    # south
    (
        (0.0, 0.0),
        (1.0, 0.0),
        (1.0, 1.0),
        (0.0, 1.0),
    ),
    # east
    (
        (0.0, 0.0),
        (1.0, 0.0),
        (1.0, 1.0),
        (0.0, 1.0),
    ),
    # west
    (
        (0.0, 0.0),
        (1.0, 0.0),
        (1.0, 1.0),
        (0.0, 1.0),
    ),
    # bottom
    (
        (0.0, 1.0),
        (0.0, 0.0),
        (1.0, 0.0),
        (1.0, 1.0),
    ),
)


def get_face_uvs(
    block_name: str,
    face_index: int,
):
    cache_key = (
        block_name,
        face_index,
    )

    cached = _face_uv_cache.get(
        cache_key
    )

    if cached is not None:
        return cached

    tile_names = BLOCK_FACE_TILES.get(
        block_name,
        ("missing",) * 6,
    )

    tile_name = tile_names[
        face_index
    ]

    column, row = ATLAS_TILES.get(
        tile_name,
        ATLAS_TILES["missing"],
    )

    tile_width = (
        1.0
        / ATLAS_COLUMNS
    )

    tile_height = (
        1.0
        / ATLAS_ROWS
    )

    u_min = (
        column
        * tile_width
    )

    v_min = (
        row
        * tile_height
    )

    u_max = (
        u_min
        + tile_width
    )

    v_max = (
        v_min
        + tile_height
    )

    # Half-pixel inward inset prevents neighbouring atlas tiles bleeding
    # into one another while preserving the full 64x64 image visually.
    atlas_pixels = 256.0
    inset = (
        0.5
        / atlas_pixels
    )

    u_min += inset
    v_min += inset
    u_max -= inset
    v_max -= inset

    result = []

    for local_u, local_v in (
        _FACE_UV_PATTERN[
            face_index
        ]
    ):
        result.append(
            (
                u_min
                + (
                    u_max
                    - u_min
                )
                * local_u,

                v_min
                + (
                    v_max
                    - v_min
                )
                * local_v,
            )
        )

    result = tuple(
        result
    )

    _face_uv_cache[
        cache_key
    ] = result

    return result


def get_block_texture(
    block_name: str,
):
    filenames = BLOCK_TEXTURES.get(
        block_name,
        (MISSING_TEXTURE,) * 6,
    )

    return get_texture(
        filenames[0]
    )


def get_face_texture_name(
    block_name: str,
    face_index: int,
) -> str:
    filenames = BLOCK_TEXTURES.get(
        block_name,
        (MISSING_TEXTURE,) * 6,
    )

    return filenames[
        face_index
    ]
