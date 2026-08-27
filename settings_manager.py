from __future__ import annotations

import json
from dataclasses import dataclass, asdict

from config import DIFFICULTIES, SETTINGS_FILE


@dataclass
class GameSettings:
    sound: float = 0.8
    fov: int = 90
    vsync: bool = True
    difficulty: str = "easy"

    def normalise(self) -> None:
        self.sound = max(0.0, min(1.0, float(self.sound)))
        self.fov = max(60, min(120, int(self.fov)))
        self.vsync = bool(self.vsync)
        if self.difficulty not in DIFFICULTIES:
            self.difficulty = "easy"


def load_settings() -> GameSettings:
    if not SETTINGS_FILE.exists():
        settings = GameSettings()
        save_settings(settings)
        return settings

    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        settings = GameSettings(**data)
        settings.normalise()
        return settings
    except (OSError, json.JSONDecodeError, TypeError):
        return GameSettings()


def save_settings(settings: GameSettings) -> None:
    settings.normalise()
    SETTINGS_FILE.write_text(
        json.dumps(asdict(settings), indent=2),
        encoding="utf-8",
    )


def settings_as_dict(settings: GameSettings) -> dict[str, object]:
    """Return a copy suitable for a debug panel or save-game payload."""
    settings.normalise()
    return asdict(settings)


def reset_settings() -> GameSettings:
    """Restore defaults and persist them immediately."""
    settings = GameSettings()
    save_settings(settings)
    return settings


def settings_file_exists() -> bool:
    """Expose persistence state to the options menu."""
    return SETTINGS_FILE.exists()


def backup_settings() -> bool:
    """Create a readable backup before a settings migration."""
    if not SETTINGS_FILE.exists():
        return False
    backup = SETTINGS_FILE.with_suffix(".backup.json")
    try:
        backup.write_text(SETTINGS_FILE.read_text(encoding="utf-8"), encoding="utf-8")
    except OSError:
        return False
    return True


def load_settings_or_default() -> GameSettings:
    """Compatibility entry point for menus that do not need file details."""
    settings = load_settings()
    settings.normalise()
    return settings


def describe_settings(settings: GameSettings) -> list[str]:
    """Build compact text rows for diagnostics and accessibility."""
    return [
        f"Sound: {settings.sound:.0%}",
        f"FOV: {settings.fov}",
        f"VSync: {'On' if settings.vsync else 'Off'}",
        f"Difficulty: {settings.difficulty.title()}",
    ]


def merge_settings(settings: GameSettings, updates: dict[str, object]) -> GameSettings:
    """Apply known options from a partial UI or command-line update."""
    allowed = {"sound", "fov", "vsync", "difficulty"}
    for key, value in updates.items():
        if key in allowed:
            setattr(settings, key, value)
    settings.normalise()
    return settings


def export_settings_text(settings: GameSettings) -> str:
    """Create stable JSON text for backups and support tickets."""
    settings.normalise()
    return json.dumps(asdict(settings), indent=2, sort_keys=True)


def import_settings_text(raw: str) -> GameSettings:
    """Parse settings without touching the filesystem."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return GameSettings()
    if not isinstance(data, dict):
        return GameSettings()
    return merge_settings(GameSettings(), data)


def restore_backup() -> GameSettings:
    """Restore the optional backup file, falling back to defaults safely."""
    backup = SETTINGS_FILE.with_suffix(".backup.json")
    if not backup.exists():
        return GameSettings()
    try:
        settings = import_settings_text(backup.read_text(encoding="utf-8"))
    except OSError:
        settings = GameSettings()
    save_settings(settings)
    return settings


def settings_schema() -> dict[str, str]:
    """Describe option types for future config editors."""
    return {"sound": "float 0..1", "fov": "integer 60..120", "vsync": "boolean", "difficulty": "easy|medium|hard"}
