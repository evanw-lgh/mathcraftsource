from __future__ import annotations

from dataclasses import asdict

from panda3d.core import WindowProperties

from ursina import (
    AmbientLight,
    Audio,
    DirectionalLight,
    Entity,
    Sky,
    Ursina,
    Vec3,
    application,
    camera,
    color,
    destroy,
    held_keys,
    mouse,
    scene,
    window,
)

from config import ASSET_DIR
from day_night import DayNightCycle
from dimensions import DimensionManager
from debug_panel import DebugHotkey, DebugPanelBridge
from inventory import Inventory
from player import MathcraftPlayer
from quests import StarterQuest
from settings_manager import load_settings, save_settings
from ui import GameUI
from world import World, apply_world_settings
from world_saves import (
    WorldSettings,
    load_world_save,
    load_world_state,
    save_world_state,
    write_world_metadata,
)
from hostile_mobs import (
    HostileMobManager,
    apply_hostile_mob_settings,
)
from peaceful_mobs import (
    PeacefulMobManager,
    apply_peaceful_mob_settings,
)


class FullscreenHotkey(Entity):
    def __init__(self, game):
        super().__init__(
            eternal=True,
        )

        self.game = game

    def input(self, key):
        if key == "f11":
            self.game.toggle_fullscreen()
            return

        if (
            key == "enter"
            and (
                held_keys["alt"]
                or held_keys["left alt"]
                or held_keys["right alt"]
            )
        ):
            self.game.toggle_fullscreen()


class MathcraftGame:
    def __init__(self):
        self.app = Ursina(
            title="Mathcraft",
            borderless=False,
            editor_ui_enabled=False,
        )

        window.color = color.rgb32(115, 180, 235)

        # Make the native Windows window genuinely resizable/maximizable.
        self._make_window_resizable()

        # Mathcraft owns F5 for camera switching rather than hot reload.
        hot_reloader = getattr(application, "hot_reloader", None)
        if hot_reloader is not None:
            hot_reloader.hotkeys.pop("f5", None)
            hot_reloader.enabled = False

        window.fps_counter.enabled = False
        window.entity_counter.enabled = False
        window.collider_counter.enabled = False
        window.cog_button.enabled = False
        window.cog_menu.enabled = False
        window.exit_button.visible = False

        self.settings = load_settings()
        self.world_settings = WorldSettings()

        self.tokens = self.world_settings.starting_tokens
        self.inventory = Inventory()
        self.world = None
        self.player = None
        self.sky = None
        self.in_game = False
        self.current_save_id = None
        self.current_world_name = None

        self.quest = StarterQuest(self.world_settings)

        self.debug_mode = False
        self.debug_no_token_cost = False
        self.debug_panel = None
        self.debug_hotkey = DebugHotkey(self)
        self.fullscreen_hotkey = FullscreenHotkey(self)

        self.sounds = self._load_sounds()
        self.ui = GameUI(self)

        self.hostile_mob_manager = (
            HostileMobManager(
                self
            )
        )

        self.peaceful_mob_manager = (
            PeacefulMobManager(
                self
            )
        )

        # Compatibility alias for older code/debug helpers.
        self.zombie_manager = (
            self.hostile_mob_manager
        )

        self.day_night = DayNightCycle(self)

        self.current_dimension = (
            "overworld"
        )

        self.dimension_manager = (
            DimensionManager(
                self
            )
        )

        self._setup_lighting()
        self.apply_settings()

    # =========================================================
    # DEBUG
    # =========================================================

    def _make_window_resizable(self) -> None:
        try:
            if (
                application.base is None
                or application.base.win is None
            ):
                return

            properties = WindowProperties()
            properties.setFixedSize(False)

            application.base.win.requestProperties(
                properties
            )
        except Exception as error:
            print(
                "Could not enable native resizing:",
                error,
            )

    def toggle_fullscreen(self) -> None:
        try:
            window.fullscreen = (
                not bool(
                    window.fullscreen
                )
            )

            # Re-apply resizability after leaving fullscreen so the
            # Windows maximise button continues to work.
            if not window.fullscreen:
                self._make_window_resizable()

        except Exception as error:
            print(
                "Could not toggle fullscreen:",
                error,
            )

    def enable_debug_mode(self) -> None:
        self.debug_mode = True

        if self.debug_panel is None:
            self.debug_panel = DebugPanelBridge(self)

        self.debug_panel.open_panel()

    # =========================================================
    # APP / AUDIO / DISPLAY
    # =========================================================

    def _setup_lighting(self) -> None:
        self.ambient_light = AmbientLight(
            parent=scene,
            color=color.rgba32(180, 180, 180, 255),
        )

        self.sunlight = DirectionalLight(
            parent=scene,
            shadows=False,
        )
        self.sunlight.look_at(Vec3(1, -1, -1))

    def _load_sounds(self):
        audio_dir = ASSET_DIR / "audio"
        result = {}

        for name in ("correct", "wrong", "block"):
            path = audio_dir / f"{name}.wav"
            if not path.exists():
                continue

            result[name] = Audio(
                f"assets/audio/{name}.wav",
                autoplay=False,
            )

        return result

    def play_sound(self, name: str) -> None:
        sound = self.sounds.get(name)

        if sound is None or self.settings.sound <= 0:
            return

        sound.volume = self.settings.sound
        sound.stop()
        sound.play()

    def apply_settings(self) -> None:
        camera.orthographic = False
        camera.fov = float(self.settings.fov)
        window.vsync = self.settings.vsync

        if self.player is not None:
            self.player.apply_camera_settings()

    def _apply_world_display_settings(self) -> None:
        self.settings.sound = self.world_settings.sound
        self.settings.fov = self.world_settings.fov
        self.settings.vsync = self.world_settings.vsync
        self.settings.difficulty = self.world_settings.difficulty
        self.settings.normalise()
        save_settings(self.settings)

    def _sync_world_display_settings(self) -> None:
        self.world_settings.sound = self.settings.sound
        self.world_settings.fov = self.settings.fov
        self.world_settings.vsync = self.settings.vsync
        self.world_settings.difficulty = self.settings.difficulty
        self.world_settings.normalise()

    # =========================================================
    # SAVED WORLDS
    # =========================================================

    def start_game(self) -> None:
        # The PLAY button now opens the world list rather than instantly
        # constructing a world.
        self.ui.show_world_select()

    def _unload_current_world(self) -> None:
        self.in_game = False

        self.hostile_mob_manager.clear()
        self.peaceful_mob_manager.clear()

        self.dimension_manager.clear_runtime_effects()

        if self.player is not None:
            destroy(self.player)
            self.player = None

        if self.world is not None:
            self.world.destroy()
            self.world = None

        if self.sky is not None:
            destroy(self.sky)
            self.sky = None

    def load_saved_world(self, save_id: str) -> None:
        if self.current_save_id is not None and self.world is not None:
            self.save_current_world()

        self._unload_current_world()

        metadata = load_world_save(save_id)
        self.world_settings = WorldSettings.from_dict(metadata.get("settings"))
        self.world_settings.normalise()

        apply_world_settings(
            self.world_settings
        )

        apply_hostile_mob_settings(
            self.world_settings
        )

        apply_peaceful_mob_settings(
            self.world_settings
        )

        self._apply_world_display_settings()

        progress = metadata.get("progress", {})
        self.tokens = int(progress.get("tokens", self.world_settings.starting_tokens))

        self.inventory = Inventory()
        self.inventory.restore(
            progress.get(
                "inventory"
            )
        )

        self.quest = StarterQuest(self.world_settings)
        self.quest.restore_state(progress.get("quest"))

        self.ui.math_streak = int(progress.get("math_streak", 0))
        self.ui.reset_streak_visual_only()

        raw_state = load_world_state(
            save_id
        )

        (
            state,
            dimension,
        ) = (
            self.dimension_manager
            .load_save_state(
                raw_state
            )
        )

        self.current_dimension = (
            dimension
        )

        self.world = World(
            initial_state=state,
            dimension=dimension,
        )

        self.sky = Sky()

        self.day_night.configure(
            self.world_settings,
            progress.get(
                "world_time_minutes"
            ),
        )

        spawn_position = self.world.get_spawn_position()
        player_position = progress.get("player_position")

        if (
            isinstance(player_position, list)
            and len(player_position) == 3
        ):
            try:
                spawn_position = Vec3(
                    float(player_position[0]),
                    float(player_position[1]),
                    float(player_position[2]),
                )
            except (TypeError, ValueError):
                spawn_position = self.world.get_spawn_position()

        self.player = MathcraftPlayer(
            self,
            self.world,
            position=spawn_position,
        )

        self.player.restore_survival(
            progress.get(
                "health",
                self.world_settings.max_health,
            ),
            progress.get(
                "oxygen",
                self.world_settings.max_oxygen,
            ),
        )

        self.current_save_id = save_id
        self.current_world_name = metadata.get("name", save_id)
        self.in_game = True

        self.player.enabled = True
        self.player.set_first_person()

        self.dimension_manager._rebuild_runtime_effects()

        self.ui.show_game_hud()
        self.apply_settings()

        self.day_night.apply_visuals()

        mouse.locked = True

        metadata["last_played"] = __import__("datetime").datetime.now().astimezone().isoformat(timespec="seconds")
        write_world_metadata(save_id, metadata)

    def save_current_world(self) -> None:
        if self.current_save_id is None or self.world is None:
            return

        self._sync_world_display_settings()

        try:
            metadata = load_world_save(self.current_save_id)
        except FileNotFoundError:
            return

        progress = metadata.setdefault("progress", {})
        progress["tokens"] = int(self.tokens)
        progress["math_streak"] = int(self.ui.math_streak)
        progress["quest"] = self.quest.serialize_state()
        progress["inventory"] = self.inventory.serialize()

        progress["world_time_minutes"] = float(
            self.day_night.world_minutes
        )

        if self.player is not None:
            progress["health"] = float(
                self.player.health
            )
            progress["oxygen"] = int(
                self.player.oxygen
            )
            progress["player_position"] = [
                float(self.player.x),
                float(self.player.y),
                float(self.player.z),
            ]

        metadata["settings"] = asdict(self.world_settings)
        metadata["last_played"] = __import__("datetime").datetime.now().astimezone().isoformat(timespec="seconds")

        write_world_metadata(self.current_save_id, metadata)
        save_world_state(
            self.current_save_id,
            self.dimension_manager.serialize_save_state(),
        )

    def return_to_menu(self) -> None:
        self.save_current_world()
        self.in_game = False

        if self.player is not None:
            self.player.enabled = False

        self.ui.show_main_menu()

    # =========================================================
    # GAMEPLAY
    # =========================================================

    def spend_token(self, action_name: str) -> bool:
        if self.debug_mode and self.debug_no_token_cost:
            return True

        if self.tokens <= 0:
            self.ui.set_message(
                f"You need a token to {action_name}. Answer a maths question!"
            )
            self.ui.open_math_question()
            return False

        self.tokens -= 1
        self.ui.update_hud()
        return True

    def check_quest_completion(self) -> None:
        reward = self.quest.claim_if_ready()

        if reward:
            self.tokens += reward
            self.ui.set_message(f"Quest complete! +{reward} tokens")
            self.ui.update_hud()

    def quit_game(self) -> None:
        self.save_current_world()
        application.quit()

    def run(self) -> None:
        self.app.run()


if __name__ == "__main__":
    MathcraftGame().run()
