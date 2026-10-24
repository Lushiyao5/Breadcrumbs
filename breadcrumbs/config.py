from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path


def data_dir() -> Path:
    root = os.environ.get("BREADCRUMBS_HOME") or os.environ.get("TLOCK_HOME")
    if root:
        path = Path(root).expanduser()
    else:
        path = Path.home() / ".breadcrumbs"
        legacy = Path.home() / ".tlock"
        if legacy.exists() and not any((path / name).exists() for name in ("breadcrumbs.db", "config.json")):
            path = legacy  # Reuse history in place; never copy or move a live database.
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
    reading_mode: str | None = None
    reading_scope: str = "all"
    reading_interval_seconds: int = 120
    book_animation: bool = True
    activity_source: str = "off"
    activity_apps: list[str] = field(default_factory=list)
    activity_domains: list[str] = field(default_factory=list)
    activity_titles: bool = True
    browser_bridge_port: int = 5643
    activity_pages: list[dict] = field(default_factory=list)
    activity_agents: list[dict] = field(default_factory=list)
    onboarding_version: int = 0

    @property
    def effective_reading_mode(self) -> str:
        if self.reading_mode in ("off", "quran", "quotes"):
            return self.reading_mode
        return "quran" if self.quran_enabled else "off"

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
            if payload.get("activity_source") in ("activitywatch", "desktop"):
                payload["activity_source"] = "integrated"
            allowed = {field.name for field in fields(cls)}
            return cls(**{key: value for key, value in payload.items() if key in allowed})
        except (OSError, ValueError, TypeError):
            return cls()

    def save(self) -> None:
        self.path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
