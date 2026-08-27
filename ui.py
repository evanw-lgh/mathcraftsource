from __future__ import annotations

from pathlib import Path
import shutil

from PIL import Image

from ursina import (
    Button,
    Entity,
    InputField,
    Slider,
    Text,
    camera,
    color,
    destroy,
    held_keys,
    load_texture,
    mouse,
    time,
)

from blocks import BLOCKS, BlockType
from textures import (
    SPECIAL_BLOCK_TEXTURES,
    get_texture,
)
from config import (
    ASSET_DIR,
    DIFFICULTIES,
    PROJECT_ROOT,
)
from inventory import (
    HOTBAR_SLOT_COUNT,
    INVENTORY_SLOT_COUNT,
    ITEM_TEXTURES,
    ItemType,
    inventory_display_name,
)
from math_system import generate_question
from settings_manager import save_settings
from world_saves import (
    WORLD_SETTING_FIELDS,
    WORLD_SETTING_PAGES,
    WorldSettings,
    create_world_save,
    delete_world_save,
    list_world_saves,
)


class InventoryPlayerPreview(Entity):
    def __init__(
        self,
        **kwargs,
    ):
        super().__init__(
            **kwargs
        )

        self.rotation_y = -18

        # Blocky temporary player preview.
        self.left_leg = Entity(
            parent=self,
            model="cube",
            x=-0.17,
            y=0.48,
            scale=(
                0.25,
                0.95,
                0.27,
            ),
            color=color.rgb32(
                40,
                65,
                115,
            ),
        )

        self.right_leg = Entity(
            parent=self,
            model="cube",
            x=0.17,
            y=0.48,
            scale=(
                0.25,
                0.95,
                0.27,
            ),
            color=color.rgb32(
                40,
                65,
                115,
            ),
        )

        self.body = Entity(
            parent=self,
            model="cube",
            y=1.42,
            scale=(
                0.68,
                0.90,
                0.36,
            ),
            color=color.rgb32(
                55,
                135,
                215,
            ),
        )

        self.left_arm = Entity(
            parent=self,
            model="cube",
            x=-0.47,
            y=1.42,
            scale=(
                0.20,
                0.88,
                0.22,
            ),
            color=color.rgb32(
                220,
                175,
                130,
            ),
        )

        self.right_arm = Entity(
            parent=self,
            model="cube",
            x=0.47,
            y=1.42,
            scale=(
                0.20,
                0.88,
                0.22,
            ),
            color=color.rgb32(
                220,
                175,
                130,
            ),
        )

        self.head = Entity(
            parent=self,
            model="cube",
            y=2.18,
            scale=(
                0.58,
                0.58,
                0.58,
            ),
            color=color.rgb32(
                220,
                175,
                130,
            ),
        )

    def update(self):
        if not self.enabled:
            return

        self.rotation_y += (
            time.dt
            * 12.0
        )


class InventoryCursorFollower(Entity):
    def update(self):
        if not self.enabled:
            return

        self.position = (
            mouse.position
        )


class InventorySpreadController(Entity):
    def __init__(
        self,
        ui,
    ):
        super().__init__(
            eternal=True,
        )

        self.ui = ui

    def input(
        self,
        key,
    ):
        if not self.ui.inventory_open:
            return

        if key == "left mouse down":
            self.ui._begin_inventory_spread()
            return

        if key == "left mouse up":
            self.ui._finish_inventory_spread()

    def update(
        self,
    ):
        if (
            not self.ui.inventory_open
            or not self.ui.inventory_spreading
            or not held_keys[
                "left mouse"
            ]
        ):
            return

        self.ui._collect_inventory_spread_target()


class GameUI:
    def __init__(self, game):
        self.game = game

        self.accent_color = color.azure

        self.question_open = False
        self.pause_open = False
        self.current_question = None

        self.math_streak = 0
        self.streak_digits = []

        self.inventory_icons = []
        self.inventory_counts = []
        self.inventory_selector = None

        self.inventory_open = False

        self.inventory_spreading = False
        self.inventory_spread_targets = []

        self.inventory_screen_icons = []
        self.inventory_screen_counts = []
        self.inventory_screen_buttons = []

        self.crafting_icons = []
        self.crafting_counts = []
        self.crafting_buttons = []

        self.crafting_output_icon = None
        self.crafting_output_count = None

        self.health_textures = {}
        self.oxygen_textures = {}

        self.menu_root = Entity(
            parent=camera.ui
        )

        self.settings_root = Entity(
            parent=camera.ui,
            enabled=False,
        )

        self.world_select_root = Entity(
            parent=camera.ui,
            enabled=False,
        )

        self.world_create_root = Entity(
            parent=camera.ui,
            enabled=False,
        )

        self.hud_root = Entity(
            parent=camera.ui,
            enabled=False,
        )

        self.question_root = Entity(
            parent=camera.ui,
            enabled=False,
        )

        self.pause_root = Entity(
            parent=camera.ui,
            enabled=False,
        )

        self.inventory_screen_root = Entity(
            parent=camera.ui,
            enabled=False,
        )

        self.world_list_page = 0
        self.world_row_entities = []

        self.world_create_page = 0
        self.world_create_values = WorldSettings().text_values()
        self.world_create_fields = {}
        self.world_create_dynamic = []

        self._build_menu()
        self._build_world_select()
        self._build_world_create()
        self._build_settings()
        self._build_hud()
        self._build_inventory_hud()
        self._build_inventory_screen()
        self._build_survival_hud()
        self._build_question_panel()
        self._build_streak_overlay()
        self._build_pause_panel()

        self.inventory_spread_controller = (
            InventorySpreadController(
                self
            )
        )

    # =========================================================
    # GENERIC UI HELPERS
    # =========================================================

    def _button(
        self,
        text,
        y,
        on_click,
        parent,
        scale=(0.26, 0.07),
        x=0,
    ):
        return Button(
            parent=parent,
            text=text,
            x=x,
            y=y,
            scale=scale,
            color=color.rgba32(
                30,
                40,
                55,
                235,
            ),
            highlight_color=color.rgba32(
                55,
                85,
                120,
                255,
            ),
            pressed_color=color.rgba32(
                25,
                30,
                45,
                255,
            ),
            text_color=color.white,
            on_click=on_click,
        )

    def _find_ui_asset(
        self,
        filename: str,
    ) -> Path | None:
        candidates = (
            ASSET_DIR / "ui" / filename,
            ASSET_DIR / filename,
            PROJECT_ROOT / filename,
        )

        for path in candidates:
            if path.exists():
                return path

        return None

    def _trim_transparent_image(
        self,
        source_path: Path,
    ) -> Path:
        cache_dir = (
            ASSET_DIR
            / "ui"
            / "_generated"
        )

        cache_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        target_path = (
            cache_dir
            / (
                source_path.stem
                + "_trimmed.png"
            )
        )

        if (
            target_path.exists()
            and target_path.stat().st_mtime
            >= source_path.stat().st_mtime
        ):
            return target_path

        with Image.open(
            source_path
        ) as source:
            image = source.convert(
                "RGBA"
            )

        alpha = image.getchannel(
            "A"
        )

        bbox = alpha.getbbox()

        if bbox is None:
            image.save(
                target_path
            )
            return target_path

        cropped = image.crop(
            bbox
        )

        cropped.save(
            target_path
        )

        return target_path

    def _load_ui_texture(
        self,
        filename: str,
        trim=False,
    ):
        path = self._find_ui_asset(
            filename
        )

        if path is None:
            return None

        if trim:
            path = (
                self._trim_transparent_image(
                    path
                )
            )

        texture = load_texture(
            path.name,
            folder=path.parent,
        )

        if texture is not None:
            texture.filtering = "nearest"
            texture.repeat = False

        return texture

    # =========================================================
    # MAIN MENU
    # =========================================================

    def _build_menu(self):
        Entity(
            parent=self.menu_root,
            model="quad",
            scale=(
                0.76,
                0.82,
            ),
            color=color.rgba32(
                8,
                14,
                24,
                230,
            ),
        )

        Text(
            parent=self.menu_root,
            text="MATHCRAFT",
            y=0.29,
            origin=(
                0,
                0,
            ),
            scale=2.2,
            color=color.white,
        )

        Text(
            parent=self.menu_root,
            text="Adventure + RPG + Maths",
            y=0.21,
            origin=(
                0,
                0,
            ),
            scale=0.9,
            color=color.light_gray,
        )

        self._button(
            "PLAY",
            0.08,
            self.show_world_select,
            self.menu_root,
        )

        self._button(
            "SETTINGS",
            -0.03,
            self.show_settings,
            self.menu_root,
        )

        self._button(
            "QUIT",
            -0.14,
            self.game.quit_game,
            self.menu_root,
        )

    # =========================================================
    # SAVED WORLDS
    # =========================================================

    def _build_world_select(self):
        Entity(
            parent=self.world_select_root,
            model="quad",
            scale=(0.92, 0.90),
            color=color.rgba32(8, 14, 24, 242),
        )

        Text(
            parent=self.world_select_root,
            text="SELECT WORLD",
            y=0.37,
            origin=(0, 0),
            scale=1.55,
            color=color.white,
        )

        self.world_list_container = Entity(
            parent=self.world_select_root,
        )

        self.world_page_text = Text(
            parent=self.world_select_root,
            y=-0.31,
            origin=(0, 0),
            scale=0.72,
            color=color.light_gray,
        )

        self._button(
            "PREV",
            -0.31,
            self.previous_world_list_page,
            self.world_select_root,
            scale=(0.07, 0.055),
            x=-0.16,
        )

        self._button(
            "NEXT",
            -0.31,
            self.next_world_list_page,
            self.world_select_root,
            scale=(0.07, 0.055),
            x=0.16,
        )

        self._button(
            "CREATE NEW WORLD",
            -0.39,
            self.show_world_create,
            self.world_select_root,
            scale=(0.33, 0.06),
            x=-0.18,
        )

        self._button(
            "BACK",
            -0.39,
            self.show_main_menu,
            self.world_select_root,
            scale=(0.19, 0.06),
            x=0.22,
        )

    def _clear_world_rows(self):
        for entity in self.world_row_entities:
            destroy(entity)

        self.world_row_entities.clear()

    def refresh_world_list(self):
        self._clear_world_rows()

        worlds = list_world_saves()
        per_page = 6
        page_count = max(1, (len(worlds) + per_page - 1) // per_page)
        self.world_list_page = max(0, min(page_count - 1, self.world_list_page))

        start = self.world_list_page * per_page
        visible = worlds[start:start + per_page]

        self.world_page_text.text = (
            f"Page {self.world_list_page + 1}/{page_count}"
        )

        if not visible:
            empty = Text(
                parent=self.world_list_container,
                text="No saved worlds yet.",
                y=0.10,
                origin=(0, 0),
                color=color.light_gray,
                scale=0.85,
            )
            self.world_row_entities.append(empty)
            return

        for index, world_info in enumerate(visible):
            y = 0.26 - index * 0.095
            name = str(world_info.get("name", world_info.get("id", "World")))
            last_played = str(world_info.get("last_played", ""))
            if "T" in last_played:
                last_played = last_played.replace("T", " ")[:19]

            row = Entity(
                parent=self.world_list_container,
                model="quad",
                scale=(0.78, 0.075),
                y=y,
                color=color.rgba32(24, 34, 48, 235),
            )
            self.world_row_entities.append(row)

            name_text = Text(
                parent=row,
                text=name,
                x=-0.47,
                y=0.13,
                scale=0.80,
                color=color.white,
            )
            self.world_row_entities.append(name_text)

            date_text = Text(
                parent=row,
                text=last_played,
                x=-0.47,
                y=-0.20,
                scale=0.52,
                color=color.light_gray,
            )
            self.world_row_entities.append(date_text)

            save_id = world_info["id"]

            load_button = Button(
                parent=row,
                text="PLAY",
                x=0.26,
                scale=(0.20, 0.62),
                color=color.rgba32(42, 80, 58, 255),
                highlight_color=color.rgba32(55, 105, 73, 255),
                text_color=color.white,
                on_click=lambda sid=save_id: self.game.load_saved_world(sid),
            )
            self.world_row_entities.append(load_button)

            delete_button = Button(
                parent=row,
                text="X",
                x=0.43,
                scale=(0.09, 0.62),
                color=color.rgba32(90, 38, 38, 255),
                highlight_color=color.rgba32(125, 48, 48, 255),
                text_color=color.white,
                on_click=lambda sid=save_id: self.delete_world(sid),
            )
            self.world_row_entities.append(delete_button)

    def show_world_select(self):
        self.menu_root.enabled = False
        self.settings_root.enabled = False
        self.world_create_root.enabled = False
        self.hud_root.enabled = False
        self.pause_root.enabled = False
        self.question_root.enabled = False

        self.world_select_root.enabled = True
        self.refresh_world_list()
        mouse.locked = False

    def previous_world_list_page(self):
        self.world_list_page = max(0, self.world_list_page - 1)
        self.refresh_world_list()

    def next_world_list_page(self):
        worlds = list_world_saves()
        page_count = max(1, (len(worlds) + 5) // 6)
        self.world_list_page = min(page_count - 1, self.world_list_page + 1)
        self.refresh_world_list()

    def delete_world(self, save_id):
        if self.game.current_save_id == save_id and self.game.world is not None:
            self.world_select_message.text = "Return to another world before deleting this one."
            return

        delete_world_save(save_id)
        self.refresh_world_list()

    # =========================================================
    # CREATE WORLD / VARIABLE EDITOR
    # =========================================================

    def _build_world_create(self):
        Entity(
            parent=self.world_create_root,
            model="quad",
            scale=(0.96, 0.94),
            color=color.rgba32(8, 14, 24, 246),
        )

        Text(
            parent=self.world_create_root,
            text="CREATE NEW WORLD",
            y=0.41,
            origin=(0, 0),
            scale=1.35,
            color=color.white,
        )

        Text(
            parent=self.world_create_root,
            text="World name",
            x=-0.37,
            y=0.335,
            scale=0.72,
            color=color.light_gray,
        )

        self.world_name_input = InputField(
            parent=self.world_create_root,
            x=0.09,
            y=0.335,
            scale=(0.48, 0.05),
            default_value="New World",
        )

        self.world_create_page_text = Text(
            parent=self.world_create_root,
            y=0.275,
            origin=(0, 0),
            scale=0.86,
            color=color.white,
        )

        self.world_create_fields_root = Entity(
            parent=self.world_create_root,
        )

        self.world_create_message = Text(
            parent=self.world_create_root,
            y=-0.34,
            origin=(0, 0),
            scale=0.58,
            color=color.rgb32(255, 120, 100),
        )

        self._button(
            "PREVIOUS",
            -0.40,
            self.previous_world_create_page,
            self.world_create_root,
            scale=(0.22, 0.055),
            x=-0.31,
        )

        self._button(
            "NEXT",
            -0.40,
            self.next_world_create_page,
            self.world_create_root,
            scale=(0.18, 0.055),
            x=-0.07,
        )

        self._button(
            "CREATE",
            -0.40,
            self.create_world_from_form,
            self.world_create_root,
            scale=(0.18, 0.055),
            x=0.17,
        )

        self._button(
            "CANCEL",
            -0.40,
            self.show_world_select,
            self.world_create_root,
            scale=(0.17, 0.055),
            x=0.37,
        )

        self.world_select_message = Text(
            parent=self.world_select_root,
            y=-0.345,
            origin=(0, 0),
            scale=0.55,
            color=color.rgb32(255, 130, 110),
        )

    def show_world_create(self):
        self.world_select_root.enabled = False
        self.menu_root.enabled = False
        self.world_create_root.enabled = True

        self.world_create_page = 0
        self.world_create_values = WorldSettings().text_values()
        self.world_name_input.text = "New World"
        self.world_create_message.text = ""

        self._render_world_create_page()
        mouse.locked = False

    def _save_current_create_page(self):
        for key, field in self.world_create_fields.items():
            self.world_create_values[key] = field.text

    def _clear_world_create_dynamic(self):
        for entity in self.world_create_dynamic:
            destroy(entity)

        self.world_create_dynamic.clear()
        self.world_create_fields.clear()

    def _render_world_create_page(self):
        self._clear_world_create_dynamic()

        page = WORLD_SETTING_PAGES[self.world_create_page]
        fields = [
            (key, label)
            for field_page, key, label in WORLD_SETTING_FIELDS
            if field_page == page
        ]

        self.world_create_page_text.text = (
            f"{page}   ({self.world_create_page + 1}/{len(WORLD_SETTING_PAGES)})"
        )

        row_start = 0.205
        row_gap = 0.061

        for index, (key, label) in enumerate(fields):
            y = row_start - index * row_gap

            label_entity = Text(
                parent=self.world_create_fields_root,
                text=label,
                x=-0.39,
                y=y,
                scale=0.63,
                color=color.white,
            )

            field = InputField(
                parent=self.world_create_fields_root,
                x=0.20,
                y=y,
                scale=(0.34, 0.043),
                default_value=self.world_create_values.get(key, ""),
            )

            self.world_create_dynamic.extend((label_entity, field))
            self.world_create_fields[key] = field

    def previous_world_create_page(self):
        self._save_current_create_page()
        self.world_create_page = (
            self.world_create_page - 1
        ) % len(WORLD_SETTING_PAGES)
        self._render_world_create_page()

    def next_world_create_page(self):
        self._save_current_create_page()
        self.world_create_page = (
            self.world_create_page + 1
        ) % len(WORLD_SETTING_PAGES)
        self._render_world_create_page()

    def create_world_from_form(self):
        self._save_current_create_page()
        self.world_create_message.text = ""

        name = self.world_name_input.text.strip()
        if not name:
            self.world_create_message.text = "Enter a world name."
            return

        try:
            settings = WorldSettings.from_text_values(
                self.world_create_values
            )
        except ValueError as exc:
            self.world_create_message.text = str(exc)
            return

        save_id = create_world_save(name, settings)
        self.game.load_saved_world(save_id)

    # =========================================================
    # SETTINGS
    # =========================================================

    def _build_settings(self):
        Entity(
            parent=self.settings_root,
            model="quad",
            scale=(
                0.86,
                0.90,
            ),
            color=color.rgba32(
                8,
                14,
                24,
                240,
            ),
        )

        Text(
            parent=self.settings_root,
            text="SETTINGS",
            y=0.34,
            origin=(
                0,
                0,
            ),
            scale=1.6,
            color=color.white,
        )

        Text(
            parent=self.settings_root,
            text="Sound",
            x=-0.30,
            y=0.20,
            color=color.white,
        )

        self.sound_slider = Slider(
            parent=self.settings_root,
            min=0,
            max=100,
            default=(
                self.game.settings.sound
                * 100
            ),
            x=-0.03,
            y=0.20,
            scale=0.45,
        )

        Text(
            parent=self.settings_root,
            text="FOV",
            x=-0.30,
            y=0.08,
            color=color.white,
        )

        self.fov_slider = Slider(
            parent=self.settings_root,
            min=60,
            max=120,
            default=self.game.settings.fov,
            x=-0.03,
            y=0.08,
            scale=0.45,
        )

        self.vsync_button = (
            self._button(
                "",
                -0.04,
                self.toggle_vsync,
                self.settings_root,
                scale=(
                    0.30,
                    0.06,
                ),
            )
        )

        self.difficulty_button = (
            self._button(
                "",
                -0.14,
                self.cycle_difficulty,
                self.settings_root,
                scale=(
                    0.34,
                    0.06,
                ),
            )
        )

        self._button(
            "SAVE & BACK",
            -0.29,
            self.save_and_back,
            self.settings_root,
            scale=(
                0.34,
                0.07,
            ),
        )

        self.refresh_settings_labels()

    def show_settings(self):
        self.menu_root.enabled = False
        self.settings_root.enabled = True

        self.sound_slider.value = (
            self.game.settings.sound
            * 100
        )

        self.fov_slider.value = (
            self.game.settings.fov
        )

        self.refresh_settings_labels()

    def toggle_vsync(self):
        self.game.settings.vsync = (
            not self.game.settings.vsync
        )

        self.refresh_settings_labels()

    def cycle_difficulty(self):
        current = DIFFICULTIES.index(
            self.game.settings.difficulty
        )

        self.game.settings.difficulty = (
            DIFFICULTIES[
                (
                    current
                    + 1
                )
                % len(
                    DIFFICULTIES
                )
            ]
        )

        self.refresh_settings_labels()

    def refresh_settings_labels(self):
        self.vsync_button.text = (
            "VSync: "
            + (
                "ON"
                if self.game.settings.vsync
                else "OFF"
            )
        )

        self.difficulty_button.text = (
            "Difficulty: "
            + self.game.settings.difficulty.upper()
        )

    def save_and_back(self):
        self.game.settings.sound = (
            self.sound_slider.value
            / 100
        )

        self.game.settings.fov = int(
            self.fov_slider.value
        )

        save_settings(
            self.game.settings
        )

        self.game.apply_settings()

        self.settings_root.enabled = False
        self.menu_root.enabled = True

    # =========================================================
    # HUD
    # =========================================================

    def _build_hud(self):
        self.time_text = Text(
            parent=self.hud_root,
            text="08:00",
            x=-0.76,
            y=0.47,
            scale=1.00,
            color=color.white,
        )

        self.tokens_text = Text(
            parent=self.hud_root,
            x=-0.76,
            y=0.42,
            scale=1.10,
            color=color.white,
        )

        self.block_text = Text(
            parent=self.hud_root,
            x=-0.76,
            y=0.37,
            scale=0.88,
            color=color.white,
        )

        self.difficulty_text = Text(
            parent=self.hud_root,
            x=-0.76,
            y=0.32,
            scale=0.88,
            color=color.white,
        )

        self.quest_text = Text(
            parent=self.hud_root,
            x=-0.76,
            y=0.26,
            scale=0.70,
            color=color.white,
        )

        self.help_text = Text(
            parent=self.hud_root,
            text=(
                "WASD move | Shift sprint | Space jump | "
                "F5 camera | LMB mine | RMB place | "
                "Wheel/1-7 block | Q maths | Esc menu"
            ),
            x=-0.76,
            y=-0.46,
            scale=0.58,
            color=color.white,
        )

        self.message_text = Text(
            parent=self.hud_root,
            y=0.36,
            origin=(
                0,
                0,
            ),
            scale=1.0,
            color=color.white,
        )

    def show_game_hud(self):
        self.menu_root.enabled = False
        self.settings_root.enabled = False
        self.world_select_root.enabled = False
        self.world_create_root.enabled = False
        self.pause_root.enabled = False
        self.question_root.enabled = False
        self.inventory_screen_root.enabled = False

        self.question_open = False
        self.pause_open = False
        self.inventory_open = False

        self.hud_root.enabled = True

        self.update_hud()

    def show_main_menu(self):
        self.hud_root.enabled = False
        self.settings_root.enabled = False
        self.world_select_root.enabled = False
        self.world_create_root.enabled = False
        self.question_root.enabled = False
        self.pause_root.enabled = False
        self.inventory_screen_root.enabled = False

        self.menu_root.enabled = True

        self.question_open = False
        self.pause_open = False
        self.inventory_open = False
        self.current_question = None

        mouse.locked = False

    def set_world_time(
        self,
        time_text: str,
    ) -> None:
        self.time_text.text = str(
            time_text
        )

    def update_hud(self):
        self.tokens_text.text = (
            f"Tokens: {self.game.tokens}"
        )

        self.difficulty_text.text = (
            "Maths: "
            + self.game.settings.difficulty.upper()
        )

        self.quest_text.text = (
            self.game.quest.progress_text()
        )

        if self.game.player is not None:
            selected_slot = (
                self.game.inventory.selected_slot
            )

            selected_value = (
                self.game.inventory.selected_value
            )

            self.block_text.text = (
                "Selected: "
                + inventory_display_name(
                    selected_value
                )
                + " | Count: "
                + str(
                    selected_slot.count
                    if not selected_slot.empty()
                    else 0
                )
            )

            self.update_inventory_ui()
            self.update_survival_ui()

        else:
            self.block_text.text = ""

    def set_message(
        self,
        text: str,
    ):
        self.message_text.color = (
            color.white
        )

        self.message_text.text = (
            text
        )

        self.message_text.fade_out(
            duration=2.2
        )

    # =========================================================
    # INVENTORY HOTBAR
    # =========================================================

    def _build_inventory_hud(
        self,
    ) -> None:
        inventory_texture = (
            self._load_ui_texture(
                "inventory.png"
            )
        )

        self.inventory_root = Entity(
            parent=self.hud_root,
            y=-0.43,
        )

        self.inventory_background = Entity(
            parent=self.inventory_root,
            model="quad",
            texture=inventory_texture,
            scale=(
                0.44,
                0.050,
            ),
            color=color.white,
        )

        slot_step = (
            0.44 / 9.0
        )

        slot_start = (
            -0.44 / 2.0
            + slot_step / 2.0
        )

        for index in range(9):
            x = (
                slot_start
                + index
                * slot_step
            )

            icon = Entity(
                parent=self.inventory_root,
                model="quad",
                enabled=False,
                x=x,
                y=0.001,
                scale=(
                    0.034,
                    0.034,
                ),
                color=color.white,
            )

            count = Text(
                parent=self.inventory_root,
                text="",
                x=x + 0.013,
                y=-0.012,
                origin=(
                    0,
                    0,
                ),
                scale=0.63,
                color=color.white,
            )

            self.inventory_icons.append(
                icon
            )
            self.inventory_counts.append(
                count
            )

        # Simple four-line selected-slot outline.
        self.inventory_selector = Entity(
            parent=self.inventory_root,
            x=slot_start,
        )

        thickness = 0.0048
        size_x = slot_step * 0.92
        size_y = 0.047

        Entity(
            parent=self.inventory_selector,
            model="quad",
            y=size_y / 2,
            scale=(size_x, thickness),
            color=color.white,
        )
        Entity(
            parent=self.inventory_selector,
            model="quad",
            y=-size_y / 2,
            scale=(size_x, thickness),
            color=color.white,
        )
        Entity(
            parent=self.inventory_selector,
            model="quad",
            x=-size_x / 2,
            scale=(thickness, size_y),
            color=color.white,
        )
        Entity(
            parent=self.inventory_selector,
            model="quad",
            x=size_x / 2,
            scale=(thickness, size_y),
            color=color.white,
        )

        self.inventory_slot_step = (
            slot_step
        )
        self.inventory_slot_start = (
            slot_start
        )

    def _inventory_icon_texture(
        self,
        inventory_value,
    ):
        if isinstance(
            inventory_value,
            ItemType,
        ):
            filename = (
                ITEM_TEXTURES[
                    inventory_value
                ]
            )

            path = (
                ASSET_DIR
                / "items"
                / filename
            )

            if not path.exists():
                return get_texture(
                    "missing.png"
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

        block_type = (
            inventory_value
        )

        filenames = {
            BlockType.OAK_LOG:
                "oak_log_side.png",
            BlockType.OAK_LEAVES:
                "leaves.png",
            BlockType.GRASS_BLOCK:
                "grass_block_top.png",
            BlockType.DIRT:
                "dirt.png",
            BlockType.OBSIDIAN:
                SPECIAL_BLOCK_TEXTURES[
                    "OBSIDIAN"
                ],
            BlockType.OAK_PLANKS:
                "oak_planks.png",
            BlockType.GLASS:
                "glass.png",
            BlockType.OAK_STAIRS:
                "oak_planks.png",
        }

        filename = filenames.get(
            block_type
        )

        if filename is None:
            return get_texture(
                "missing.png"
            )

        return get_texture(
            filename
        )

    def update_inventory_ui(
        self,
    ) -> None:
        inventory = (
            self.game.inventory
        )

        for index, slot in enumerate(
            inventory.slots[
                :HOTBAR_SLOT_COUNT
            ]
        ):
            icon = (
                self.inventory_icons[
                    index
                ]
            )

            count_text = (
                self.inventory_counts[
                    index
                ]
            )

            if slot.empty():
                icon.enabled = False
                count_text.text = ""
                continue

            icon.texture = (
                self._inventory_icon_texture(
                    slot.value
                )
            )
            icon.enabled = True

            count_text.text = (
                str(slot.count)
                if slot.count > 1
                else ""
            )

        self.inventory_selector.x = (
            self.inventory_slot_start
            + inventory.selected_index
            * self.inventory_slot_step
        )

    # =========================================================
    # FULL INVENTORY SCREEN
    # =========================================================

    def _slot_button(
        self,
        parent,
        x,
        y,
        on_click,
        scale=0.046,
        spread_type=None,
        spread_index=None,
    ):
        button = Button(
            parent=parent,
            text="",
            model="quad",
            x=x,
            y=y,
            scale=(
                scale,
                scale,
            ),
            color=color.rgba32(
                52,
                58,
                68,
                255,
            ),
            highlight_color=color.rgba32(
                78,
                88,
                105,
                255,
            ),
            pressed_color=color.rgba32(
                38,
                43,
                52,
                255,
            ),
            on_click=on_click,
        )

        Entity(
            parent=button,
            model="quad",
            scale=0.90,
            color=color.rgba32(
                20,
                24,
                30,
                255,
            ),
            z=-0.002,
        )

        button.inventory_spread_type = (
            spread_type
        )

        button.inventory_spread_index = (
            spread_index
        )

        return button

    def _make_slot_contents(
        self,
        button,
    ):
        icon = Entity(
            parent=button,
            model="quad",
            enabled=False,
            scale=0.67,
            color=color.white,
            z=-0.015,
        )

        count = Text(
            parent=button,
            text="",
            x=0.28,
            y=-0.29,
            origin=(
                0,
                0,
            ),
            scale=13.5,
            color=color.white,
            z=-0.025,
        )

        return (
            icon,
            count,
        )

    def _build_inventory_screen(
        self,
    ) -> None:
        Entity(
            parent=self.inventory_screen_root,
            model="quad",
            scale=(
                0.76,
                0.84,
            ),
            color=color.rgba32(
                10,
                14,
                20,
                248,
            ),
        )

        Text(
            parent=self.inventory_screen_root,
            text="INVENTORY",
            y=0.36,
            origin=(
                0,
                0,
            ),
            scale=1.25,
            color=color.white,
        )

        # -----------------------------------------------------
        # PLAYER PREVIEW
        # -----------------------------------------------------

        Entity(
            parent=self.inventory_screen_root,
            model="quad",
            x=-0.22,
            y=0.17,
            scale=(
                0.25,
                0.30,
            ),
            color=color.rgba32(
                25,
                30,
                38,
                255,
            ),
        )

        Text(
            parent=self.inventory_screen_root,
            text="PLAYER",
            x=-0.22,
            y=0.315,
            origin=(
                0,
                0,
            ),
            scale=0.72,
            color=color.light_gray,
        )

        self.inventory_player_preview = (
            InventoryPlayerPreview(
                parent=self.inventory_screen_root,
                x=-0.22,
                y=0.055,
                scale=0.075,
            )
        )

        # -----------------------------------------------------
        # 2x2 CRAFTING GRID
        # -----------------------------------------------------

        Text(
            parent=self.inventory_screen_root,
            text="CRAFTING 2x2",
            x=0.17,
            y=0.315,
            origin=(
                0,
                0,
            ),
            scale=0.72,
            color=color.light_gray,
        )

        crafting_positions = (
            (0.10, 0.235),
            (0.155, 0.235),
            (0.10, 0.180),
            (0.155, 0.180),
        )

        for index, (
            x,
            y,
        ) in enumerate(
            crafting_positions
        ):
            button = self._slot_button(
                self.inventory_screen_root,
                x,
                y,
                lambda i=index:
                    self._click_crafting_slot(
                        i
                    ),
                spread_type="crafting",
                spread_index=index,
            )

            icon, count = (
                self._make_slot_contents(
                    button
                )
            )

            self.crafting_buttons.append(
                button
            )
            self.crafting_icons.append(
                icon
            )
            self.crafting_counts.append(
                count
            )

        Text(
            parent=self.inventory_screen_root,
            text="=",
            x=0.225,
            y=0.205,
            origin=(
                0,
                0,
            ),
            scale=1.35,
            color=color.white,
        )

        self.crafting_output_button = (
            self._slot_button(
                self.inventory_screen_root,
                0.295,
                0.205,
                self._click_crafting_output,
                scale=0.055,
            )
        )

        (
            self.crafting_output_icon,
            self.crafting_output_count,
        ) = self._make_slot_contents(
            self.crafting_output_button
        )

        Text(
            parent=self.inventory_screen_root,
            text=(
                "Log = 4 Planks | "
                "Diagonal Planks = Wooden Bucket | "
                "2 Wool over 2 Planks = Bed | "
                "Diagonal Lava Buckets = Lighter"
            ),
            x=0.195,
            y=0.135,
            origin=(
                0,
                0,
            ),
            scale=0.55,
            color=color.gray,
        )

        # -----------------------------------------------------
        # 27 MAIN INVENTORY SLOTS
        # -----------------------------------------------------

        Text(
            parent=self.inventory_screen_root,
            text="STORAGE",
            x=-0.27,
            y=0.075,
            scale=0.64,
            color=color.light_gray,
        )

        slot_step = 0.055
        start_x = -0.22
        first_y = 0.025

        # Storage slots are indexes 9..35.
        for row in range(3):
            for column in range(9):
                index = (
                    HOTBAR_SLOT_COUNT
                    + row * 9
                    + column
                )

                x = (
                    start_x
                    + column
                    * slot_step
                )

                y = (
                    first_y
                    - row
                    * slot_step
                )

                button = self._slot_button(
                    self.inventory_screen_root,
                    x,
                    y,
                    lambda i=index:
                        self._click_inventory_slot(
                            i
                        ),
                    spread_type="inventory",
                    spread_index=index,
                )

                icon, count = (
                    self._make_slot_contents(
                        button
                    )
                )

                self.inventory_screen_buttons.append(
                    (
                        index,
                        button,
                    )
                )

                self.inventory_screen_icons.append(
                    (
                        index,
                        icon,
                    )
                )

                self.inventory_screen_counts.append(
                    (
                        index,
                        count,
                    )
                )

        # -----------------------------------------------------
        # HOTBAR ROW IN INVENTORY
        # -----------------------------------------------------

        Text(
            parent=self.inventory_screen_root,
            text="HOTBAR",
            x=-0.27,
            y=-0.175,
            scale=0.64,
            color=color.light_gray,
        )

        hotbar_y = -0.225

        for index in range(
            HOTBAR_SLOT_COUNT
        ):
            x = (
                start_x
                + index
                * slot_step
            )

            button = self._slot_button(
                self.inventory_screen_root,
                x,
                hotbar_y,
                lambda i=index:
                    self._click_inventory_slot(
                        i
                    ),
                spread_type="inventory",
                spread_index=index,
            )

            icon, count = (
                self._make_slot_contents(
                    button
                )
            )

            self.inventory_screen_buttons.append(
                (
                    index,
                    button,
                )
            )

            self.inventory_screen_icons.append(
                (
                    index,
                    icon,
                )
            )

            self.inventory_screen_counts.append(
                (
                    index,
                    count,
                )
            )

        Text(
            parent=self.inventory_screen_root,
            text=(
                "E: close  |  "
                "Click to move stacks  |  "
                "Hold left-click and drag to spread held items"
            ),
            y=-0.335,
            origin=(
                0,
                0,
            ),
            scale=0.55,
            color=color.gray,
        )

        # -----------------------------------------------------
        # ITEM STACK ATTACHED TO THE MOUSE
        # -----------------------------------------------------

        self.inventory_cursor_root = (
            InventoryCursorFollower(
                parent=camera.ui,
                enabled=False,
                z=-0.8,
            )
        )

        self.inventory_cursor_icon = Entity(
            parent=self.inventory_cursor_root,
            model="quad",
            enabled=False,
            scale=(
                0.034,
                0.034,
            ),
            color=color.white,
        )

        self.inventory_cursor_count = Text(
            parent=self.inventory_cursor_root,
            text="",
            x=0.015,
            y=-0.014,
            origin=(
                0,
                0,
            ),
            scale=0.68,
            color=color.white,
        )

    def open_inventory(
        self,
    ) -> None:
        if (
            not self.game.in_game
            or self.question_open
            or self.pause_open
        ):
            return

        self.inventory_open = True
        self.inventory_screen_root.enabled = True

        mouse.locked = False

        self.update_inventory_screen()

    def close_inventory(
        self,
    ) -> bool:
        if not self.inventory_open:
            return True

        if not (
            self.game.inventory
            .return_temporary_items()
        ):
            self.set_message(
                "Make room before closing the inventory."
            )
            return False

        self.inventory_open = False
        self.inventory_spreading = False
        self.inventory_spread_targets = []

        self.inventory_screen_root.enabled = False
        self.inventory_cursor_root.enabled = False

        self.update_hud()

        mouse.locked = (
            self.game.in_game
            and not self.pause_open
            and not self.question_open
        )

        return True

    def toggle_inventory(
        self,
    ) -> None:
        if self.inventory_open:
            self.close_inventory()
        else:
            self.open_inventory()

    def _hovered_spread_target(
        self,
    ):
        entity = (
            mouse.hovered_entity
        )

        # The mouse may be over an icon/count child rather than the
        # actual slot button, so walk up the parent chain.
        for _ in range(6):
            if entity is None:
                return None

            target_type = getattr(
                entity,
                "inventory_spread_type",
                None,
            )

            target_index = getattr(
                entity,
                "inventory_spread_index",
                None,
            )

            if (
                target_type is not None
                and target_index
                is not None
            ):
                return (
                    target_type,
                    int(
                        target_index
                    ),
                )

            entity = getattr(
                entity,
                "parent",
                None,
            )

        return None

    def _begin_inventory_spread(
        self,
    ) -> None:
        inventory = (
            self.game.inventory
        )

        # Spreading only starts while the mouse is already carrying
        # a stack. Normal left-click slot pickup still works unchanged.
        if inventory.cursor_slot.empty():
            self.inventory_spreading = False
            self.inventory_spread_targets = []
            return

        target = (
            self._hovered_spread_target()
        )

        if target is None:
            return

        self.inventory_spreading = True
        self.inventory_spread_targets = [
            target
        ]

    def _collect_inventory_spread_target(
        self,
    ) -> None:
        if not self.inventory_spreading:
            return

        target = (
            self._hovered_spread_target()
        )

        if (
            target is not None
            and target
            not in self.inventory_spread_targets
        ):
            self.inventory_spread_targets.append(
                target
            )

    def _finish_inventory_spread(
        self,
    ) -> None:
        if not self.inventory_spreading:
            return

        self._collect_inventory_spread_target()

        targets = list(
            self.inventory_spread_targets
        )

        self.inventory_spreading = False
        self.inventory_spread_targets = []

        if (
            self.game.inventory
            .spread_cursor_stack(
                targets
            )
        ):
            self.update_inventory_screen()
            self.update_hud()

    def _click_inventory_slot(
        self,
        index: int,
    ) -> None:
        self.game.inventory.click_inventory_slot(
            index
        )

        self.update_inventory_screen()
        self.update_hud()

    def _click_crafting_slot(
        self,
        index: int,
    ) -> None:
        self.game.inventory.click_crafting_slot(
            index
        )

        self.update_inventory_screen()

    def _click_crafting_output(
        self,
    ) -> None:
        if (
            self.game.inventory
            .take_crafting_result()
        ):
            self.update_inventory_screen()

    def _set_slot_visual(
        self,
        slot,
        icon,
        count_text,
    ) -> None:
        if slot.empty():
            icon.enabled = False
            count_text.text = ""
            return

        icon.texture = (
            self._inventory_icon_texture(
                slot.value
            )
        )

        icon.enabled = True

        count_text.text = (
            str(slot.count)
            if slot.count > 1
            else ""
        )

    def update_inventory_screen(
        self,
    ) -> None:
        inventory = (
            self.game.inventory
        )

        for index, icon in (
            self.inventory_screen_icons
        ):
            slot = (
                inventory.slots[
                    index
                ]
            )

            count_text = next(
                text
                for (
                    count_index,
                    text
                )
                in self.inventory_screen_counts
                if count_index == index
            )

            self._set_slot_visual(
                slot,
                icon,
                count_text,
            )

        for index, slot in enumerate(
            inventory.crafting_slots
        ):
            self._set_slot_visual(
                slot,
                self.crafting_icons[
                    index
                ],
                self.crafting_counts[
                    index
                ],
            )

        result = (
            inventory.crafting_result()
        )

        self._set_slot_visual(
            result,
            self.crafting_output_icon,
            self.crafting_output_count,
        )

        cursor = (
            inventory.cursor_slot
        )

        if cursor.empty():
            self.inventory_cursor_root.enabled = False
            self.inventory_cursor_icon.enabled = False
            self.inventory_cursor_count.text = ""
        else:
            self.inventory_cursor_root.enabled = (
                self.inventory_open
            )

            self.inventory_cursor_icon.texture = (
                self._inventory_icon_texture(
                    cursor.value
                )
            )

            self.inventory_cursor_icon.enabled = True

            self.inventory_cursor_count.text = (
                str(cursor.count)
                if cursor.count > 1
                else ""
            )

    # =========================================================
    # HEALTH + OXYGEN
    # =========================================================

    def _load_status_texture(
        self,
        folder: str,
        filename: str,
    ):
        source_path = (
            ASSET_DIR
            / "ui"
            / folder
            / filename
        )

        if not source_path.exists():
            return None

        # Ursina/Panda can cache textures by filename. Health and oxygen
        # both contain files such as "10.png", so loading them directly
        # can make oxygen accidentally reuse the already-loaded heart
        # texture. Give every status texture a unique filename first.
        cache_dir = (
            ASSET_DIR
            / "ui"
            / "_status_cache"
        )

        cache_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        unique_name = (
            f"{folder}_{filename}"
        )

        cached_path = (
            cache_dir
            / unique_name
        )

        if (
            not cached_path.exists()
            or cached_path.stat().st_mtime
            < source_path.stat().st_mtime
        ):
            shutil.copy2(
                source_path,
                cached_path,
            )

        texture = load_texture(
            cached_path.name,
            folder=cached_path.parent,
        )

        if texture is not None:
            texture.filtering = (
                "nearest"
            )
            texture.repeat = False

        return texture

    def _build_survival_hud(
        self,
    ) -> None:
        for half_units in range(
            0,
            21,
        ):
            hearts = (
                half_units / 2.0
            )

            key = f"{hearts:g}"

            texture = (
                self._load_status_texture(
                    "health",
                    f"{key}.png",
                )
            )

            if texture is not None:
                self.health_textures[
                    key
                ] = texture

        for bubbles in range(
            0,
            11,
        ):
            texture = (
                self._load_status_texture(
                    "oxygen",
                    f"{bubbles}.png",
                )
            )

            if texture is not None:
                self.oxygen_textures[
                    bubbles
                ] = texture

        self.health_image = Entity(
            parent=self.hud_root,
            model="quad",
            x=-0.57,
            y=-0.36,
            scale=(
                0.27,
                0.030,
            ),
            color=color.white,
        )

        self.oxygen_image = Entity(
            parent=self.hud_root,
            model="quad",
            x=-0.635,
            y=-0.315,
            scale=(
                0.137,
                0.030,
            ),
            color=color.white,
            enabled=False,
        )

    def update_survival_ui(
        self,
    ) -> None:
        player = (
            self.game.player
        )

        if player is None:
            return

        visible_health = max(
            0.0,
            min(
                10.0,
                round(
                    player.health
                    * 2.0
                )
                / 2.0,
            ),
        )

        health_key = (
            f"{visible_health:g}"
        )

        health_texture = (
            self.health_textures.get(
                health_key
            )
        )

        if health_texture is not None:
            self.health_image.texture = (
                health_texture
            )

        visible_oxygen = max(
            0,
            min(
                10,
                int(
                    player.oxygen
                ),
            ),
        )

        oxygen_texture = (
            self.oxygen_textures.get(
                visible_oxygen
            )
        )

        if oxygen_texture is not None:
            self.oxygen_image.texture = (
                oxygen_texture
            )

        # Minecraft-style: hide bubbles when completely recovered.
        self.oxygen_image.enabled = (
            player.oxygen
            < player.max_oxygen
        )

    # =========================================================
    # MATHS QUESTION PANEL
    # =========================================================

    def _build_question_panel(self):
        self.question_background = Entity(
            parent=self.question_root,
            model="quad",
            scale=(
                0.78,
                0.52,
            ),
            color=color.rgba32(
                10,
                18,
                30,
                245,
            ),
        )

        Text(
            parent=self.question_root,
            text="MATHS CHALLENGE",
            y=0.19,
            origin=(
                0,
                0,
            ),
            scale=1.05,
            color=color.light_gray,
        )

        self.question_text = Text(
            parent=self.question_root,
            y=0.10,
            origin=(
                0,
                0,
            ),
            scale=1.40,
            color=color.white,
        )

        self.reward_text = Text(
            parent=self.question_root,
            y=0.025,
            origin=(
                0,
                0,
            ),
            scale=0.82,
            color=color.light_gray,
        )

        self.answer_input = InputField(
            parent=self.question_root,
            y=-0.075,
            scale=(
                0.42,
                0.06,
            ),
        )

        self._button(
            "SUBMIT",
            -0.17,
            self.submit_answer,
            self.question_root,
            scale=(
                0.22,
                0.06,
            ),
            x=-0.12,
        )

        self._button(
            "CANCEL",
            -0.17,
            self.close_math_question,
            self.question_root,
            scale=(
                0.22,
                0.06,
            ),
            x=0.12,
        )

    # =========================================================
    # STREAK OVERLAY
    # =========================================================

    def _build_streak_overlay(self):
        self.streak_root = Entity(
            parent=self.question_root,
            enabled=False,
            x=0.16,
            y=0.29,
        )

        streak_texture = (
            self._load_ui_texture(
                "streak.png",
                trim=True,
            )
        )

        number_texture = (
            self._load_ui_texture(
                "numbers.png",
                trim=False,
            )
        )

        self.streak_texture = (
            streak_texture
        )

        self.number_texture = (
            number_texture
        )

        if self.streak_texture is not None:
            self.streak_image = Entity(
                parent=self.streak_root,
                model="quad",
                texture=self.streak_texture,
                scale=(
                    0.27,
                    0.14,
                ),
                color=color.white,
            )
        else:
            self.streak_image = Text(
                parent=self.streak_root,
                text="Streak",
                origin=(
                    0,
                    0,
                ),
                color=color.rgb32(
                    255,
                    60,
                    20,
                ),
                scale=1.15,
            )

        self.streak_number_root = Entity(
            parent=self.streak_root,
            x=0.20,
            y=0,
        )

    def _clear_streak_digits(self):
        for digit in (
            self.streak_digits
        ):
            destroy(
                digit
            )

        self.streak_digits.clear()

    def _set_streak_number(
        self,
        number: int,
    ):
        self._clear_streak_digits()

        if self.number_texture is None:
            return

        number = max(
            0,
            int(number),
        )

        digits = str(
            number
        )

        digit_height = 0.085
        digit_aspect = (
            96
            / 124
        )

        digit_width = (
            digit_height
            * digit_aspect
        )

        spacing = (
            digit_width
            * 0.78
        )

        total_width = (
            spacing
            * (
                len(digits)
                - 1
            )
        )

        start_x = (
            -total_width
            / 2
        )

        for index, character in (
            enumerate(
                digits
            )
        ):
            digit_value = int(
                character
            )

            digit = Entity(
                parent=self.streak_number_root,
                model="quad",
                texture=self.number_texture,
                x=(
                    start_x
                    + index
                    * spacing
                ),
                scale=(
                    digit_width,
                    digit_height,
                ),
                color=color.white,
            )

            digit.texture_scale = (
                0.1,
                1.0,
            )

            digit.texture_offset = (
                digit_value
                * 0.1,
                0.0,
            )

            self.streak_digits.append(
                digit
            )

    def update_streak_overlay(self):
        if (
            not self.question_open
            or self.math_streak <= 0
        ):
            self.streak_root.enabled = False
            return

        self.streak_root.enabled = True

        self._set_streak_number(
            self.math_streak
        )

    def increase_streak(self):
        self.math_streak += 1

        self.game.quest.record_streak(
            self.math_streak
        )

        self.update_streak_overlay()

        self.streak_root.scale = (
            1.18,
            1.18,
        )

        self.streak_root.animate_scale(
            (
                1,
                1,
            ),
            duration=0.14,
        )

    def reset_streak(self):
        self.math_streak = 0

        self.game.quest.record_streak(0)

        self._clear_streak_digits()
        self.streak_root.enabled = False

    def reset_streak_visual_only(self):
        self._clear_streak_digits()
        self.streak_root.enabled = False

    # =========================================================
    # QUESTION LOGIC
    # =========================================================

    def open_math_question(self):
        if self.question_open:
            return

        self.current_question = (
            generate_question(
                self.game.settings.difficulty,
                rewards={
                    "easy": self.game.world_settings.easy_reward,
                    "medium": self.game.world_settings.medium_reward,
                    "hard": self.game.world_settings.hard_reward,
                },
            )
        )

        self.question_text.text = (
            self.current_question.prompt
        )

        self.reward_text.color = (
            color.light_gray
        )

        self.reward_text.text = (
            "Correct answer: "
            f"+{self.current_question.reward} "
            "token(s)"
        )

        self.answer_input.text = ""

        self.question_root.enabled = True
        self.question_open = True

        self.update_streak_overlay()

        mouse.locked = False

        self.answer_input.active = True

    def submit_answer(self):
        if self.current_question is None:
            return

        if (
            self.current_question.is_correct(
                self.answer_input.text
            )
        ):
            self.increase_streak()

            reward = (
                self.current_question.reward
            )

            self.game.tokens += (
                reward
            )

            self.game.quest.record_question()

            self.game.play_sound(
                "correct"
            )

            self.game.check_quest_completion()

            # If The First Equation was completed by this answer, the
            # Hot Streak quest has just become active. Feed the current
            # streak into it immediately.
            self.game.quest.record_streak(
                self.math_streak
            )
            self.game.check_quest_completion()

            self.update_hud()

            self.close_math_question()

            self.set_message(
                f"Correct! +{reward} token(s) "
                f"| Streak: {self.math_streak}"
            )

        else:
            self.reset_streak()

            self.game.play_sound(
                "wrong"
            )

            self.reward_text.color = (
                color.rgb32(
                    255,
                    95,
                    80,
                )
            )

            self.reward_text.text = (
                "Not quite — try again."
            )

            self.answer_input.text = ""

            self.answer_input.active = True

    def close_math_question(self):
        self.question_root.enabled = False

        self.question_open = False
        self.current_question = None

        self.streak_root.enabled = False

        mouse.locked = (
            self.game.in_game
            and not self.pause_open
        )

    # =========================================================
    # PAUSE MENU
    # =========================================================

    def _build_pause_panel(self):
        Entity(
            parent=self.pause_root,
            model="quad",
            scale=(
                0.62,
                0.52,
            ),
            color=color.rgba32(
                10,
                18,
                30,
                245,
            ),
        )

        Text(
            parent=self.pause_root,
            text="PAUSED",
            y=0.15,
            origin=(
                0,
                0,
            ),
            scale=1.6,
            color=color.white,
        )

        self._button(
            "RESUME",
            0.03,
            self.toggle_pause,
            self.pause_root,
        )

        self._button(
            "MAIN MENU",
            -0.08,
            self.game.return_to_menu,
            self.pause_root,
        )

        self._button(
            "QUIT",
            -0.19,
            self.game.quit_game,
            self.pause_root,
        )

    def toggle_pause(self):
        if (
            not self.game.in_game
            or self.question_open
            or self.inventory_open
        ):
            return

        self.pause_open = (
            not self.pause_open
        )

        self.pause_root.enabled = (
            self.pause_open
        )

        mouse.locked = (
            not self.pause_open
        )
