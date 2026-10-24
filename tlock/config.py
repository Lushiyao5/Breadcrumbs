from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, fields
from pathlib import Path


def data_dir() -> Path:
    root = os.environ.get("TLOCK_HOME")
    path = Path(root).expanduser() if root else Path.home() / ".tlock"
    path.mkdir(parents=True, exist_ok=True)
    return path


@dataclass(slots=True)
class Settings:
    focus_minutes: int = 25
    short_break_minutes: int = 5
    long_break_minutes: int = 15
    sessions_before_long_break: int = 4
    sound_enabled: bool = True
    sound_theme: str = "arcade"
    ui_theme: str = "midnight"
    pet_key: str = "mizan"
    pet_enabled: bool = False
    quran_enabled: bool = True
    auto_start_breaks: bool = False
    auto_start_focus: bool = False

    @property
    def path(self) -> Path:
        return data_dir() / "config.json"

    @classmethod
    def load(cls) -> "Settings":
        path = data_dir() / "config.json"
        if not path.exists():
            return cls()
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            allowed = {field.name for field in fields(cls)}
            return cls(**{key: value for key, value in payload.items() if key in allowed})
        except (OSError, ValueError, TypeError):
            return cls()

    def save(self) -> None:
        self.path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
