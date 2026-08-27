from __future__ import annotations

import queue
import secrets
import threading
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from ursina import Entity, held_keys, mouse


# Change this to whatever password you want.
# This is only a local game/debug lock; because it is Python source code,
# somebody with access to the project files can still read/change it.
DEBUG_PASSWORD = "mathcraft"


def prompt_debug_password() -> bool:
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    try:
        password = simpledialog.askstring(
            "Mathcraft Debug Mode",
            "Enter debug password:",
            show="*",
            parent=root,
        )

        if password is None:
            return False

        if secrets.compare_digest(
            password,
            DEBUG_PASSWORD,
        ):
            return True

        messagebox.showerror(
            "Mathcraft Debug Mode",
            "Incorrect password.",
            parent=root,
        )
        return False

    finally:
        root.destroy()


class DebugHotkey(Entity):
    def __init__(self, game):
        super().__init__(
            eternal=True
        )

        self.game = game

    def input(self, key):
        if key != "d":
            return

        control_down = (
            held_keys["control"]
            or held_keys["left control"]
            or held_keys["right control"]
            or held_keys["ctrl"]
        )

        shift_down = (
            held_keys["shift"]
            or held_keys["left shift"]
            or held_keys["right shift"]
        )

        if not (
            control_down
            and shift_down
        ):
            return

        previous_mouse_lock = (
            mouse.locked
        )

        mouse.locked = False

        try:
            allowed = (
                prompt_debug_password()
            )
        finally:
            mouse.locked = (
                previous_mouse_lock
            )

        if allowed:
            self.game.enable_debug_mode()


class DebugPanelBridge(Entity):
    def __init__(self, game):
        super().__init__(
            eternal=True
        )

        self.game = game
        self.commands = queue.Queue()

        self.panel_open = False
        self.thread = None

    def open_panel(self) -> None:
        if self.panel_open:
            return

        self.panel_open = True

        self.thread = threading.Thread(
            target=self._run_panel,
            daemon=True,
            name="MathcraftDebugPanel",
        )

        self.thread.start()

    def send(
        self,
        command: str,
        value=None,
    ) -> None:
        self.commands.put(
            (
                command,
                value,
            )
        )

    def update(self) -> None:
        while True:
            try:
                command, value = (
                    self.commands.get_nowait()
                )
            except queue.Empty:
                break

            self._apply_command(
                command,
                value,
            )

    def _apply_command(
        self,
        command: str,
        value,
    ) -> None:
        if command == "set_tokens":
            try:
                self.game.tokens = max(
                    0,
                    int(value),
                )
            except (
                TypeError,
                ValueError,
            ):
                return

            self.game.ui.update_hud()
            return

        if command == "add_tokens":
            try:
                amount = int(
                    value
                )
            except (
                TypeError,
                ValueError,
            ):
                return

            self.game.tokens = max(
                0,
                self.game.tokens
                + amount,
            )

            self.game.ui.update_hud()
            return

        if command == "fly":
            if self.game.player is not None:
                self.game.player.set_fly_mode(
                    bool(value)
                )
            return

        if command == "free_build":
            self.game.debug_no_token_cost = (
                bool(value)
            )
            return

        if command == "speed":
            if self.game.player is not None:
                try:
                    self.game.player.set_debug_speed(
                        float(value)
                    )
                except (
                    TypeError,
                    ValueError,
                ):
                    pass
            return

        if command == "spawn":
            if (
                self.game.player is not None
                and self.game.world is not None
            ):
                self.game.player.position = (
                    self.game.world.get_spawn_position()
                )
            return

        if command == "reset_camera":
            if self.game.player is not None:
                self.game.player.set_first_person()
                self.game.player.apply_camera_settings()
            return

    def _run_panel(self) -> None:
        root = tk.Tk()

        root.title(
            "Mathcraft Debug Panel"
        )

        root.geometry(
            "370x450"
        )

        root.resizable(
            False,
            False,
        )

        def close_panel():
            self.panel_open = False
            root.destroy()

        root.protocol(
            "WM_DELETE_WINDOW",
            close_panel,
        )

        frame = ttk.Frame(
            root,
            padding=14,
        )

        frame.pack(
            fill="both",
            expand=True,
        )

        ttk.Label(
            frame,
            text="MATHCRAFT DEBUG MODE",
            font=(
                "Segoe UI",
                14,
                "bold",
            ),
        ).pack(
            pady=(
                0,
                14,
            )
        )

        ttk.Label(
            frame,
            text="Tokens",
        ).pack(
            anchor="w"
        )

        token_row = ttk.Frame(
            frame
        )

        token_row.pack(
            fill="x",
            pady=(
                4,
                12,
            ),
        )

        token_var = tk.StringVar(
            value=str(
                self.game.tokens
            )
        )

        ttk.Entry(
            token_row,
            textvariable=token_var,
        ).pack(
            side="left",
            fill="x",
            expand=True,
        )

        ttk.Button(
            token_row,
            text="Set",
            command=lambda: self.send(
                "set_tokens",
                token_var.get(),
            ),
        ).pack(
            side="left",
            padx=(
                6,
                0,
            ),
        )

        token_buttons = ttk.Frame(
            frame
        )

        token_buttons.pack(
            fill="x",
            pady=(
                0,
                12,
            ),
        )

        ttk.Button(
            token_buttons,
            text="+10",
            command=lambda: self.send(
                "add_tokens",
                10,
            ),
        ).pack(
            side="left",
            expand=True,
            fill="x",
        )

        ttk.Button(
            token_buttons,
            text="+100",
            command=lambda: self.send(
                "add_tokens",
                100,
            ),
        ).pack(
            side="left",
            expand=True,
            fill="x",
            padx=6,
        )

        ttk.Button(
            token_buttons,
            text="9999",
            command=lambda: self.send(
                "set_tokens",
                9999,
            ),
        ).pack(
            side="left",
            expand=True,
            fill="x",
        )

        fly_var = tk.BooleanVar(
            value=False
        )

        ttk.Checkbutton(
            frame,
            text="Fly mode  (Space up / Ctrl down)",
            variable=fly_var,
            command=lambda: self.send(
                "fly",
                fly_var.get(),
            ),
        ).pack(
            anchor="w",
            pady=5,
        )

        free_build_var = (
            tk.BooleanVar(
                value=False
            )
        )

        ttk.Checkbutton(
            frame,
            text="Free building / mining",
            variable=free_build_var,
            command=lambda: self.send(
                "free_build",
                free_build_var.get(),
            ),
        ).pack(
            anchor="w",
            pady=5,
        )

        ttk.Separator(
            frame
        ).pack(
            fill="x",
            pady=14,
        )

        ttk.Label(
            frame,
            text="Movement speed",
        ).pack(
            anchor="w"
        )

        speed_var = tk.DoubleVar(
            value=5.0
        )

        ttk.Scale(
            frame,
            from_=1.0,
            to=30.0,
            variable=speed_var,
            command=lambda value: self.send(
                "speed",
                value,
            ),
        ).pack(
            fill="x",
            pady=(
                6,
                10,
            ),
        )

        ttk.Button(
            frame,
            text="Teleport to Spawn",
            command=lambda: self.send(
                "spawn"
            ),
        ).pack(
            fill="x",
            pady=4,
        )

        ttk.Button(
            frame,
            text="Reset Camera",
            command=lambda: self.send(
                "reset_camera"
            ),
        ).pack(
            fill="x",
            pady=4,
        )

        ttk.Label(
            frame,
            text=(
                "Press Ctrl + Shift + D again after closing\n"
                "the panel to reopen it."
            ),
            justify="center",
        ).pack(
            pady=(
                18,
                0,
            ),
        )

        try:
            root.mainloop()
        finally:
            self.panel_open = False
