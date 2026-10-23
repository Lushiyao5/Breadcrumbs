from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Grid, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select, Static, Switch, TextArea

from .config import Settings
from .widgets import CommandBar


class SettingsScreen(ModalScreen[Settings | None]):
    BINDINGS = [("escape", "cancel", "Cancel"), ("ctrl+s", "save", "Save")]
    CSS = """
    SettingsScreen { align: center middle; background: #090b12e8; }
    #settings-card { width: 72; height: auto; max-height: 95%; padding: 1 2;
        border: heavy #ffd166; background: #151927; }
    #settings-grid { grid-size: 2; grid-columns: 1fr 20; grid-gutter: 1; height: auto; }
    #settings-actions { height: 3; grid-size: 2; grid-gutter: 1; margin-top: 1; }
    .setting-label { height: 3; content-align: left middle; }
    #settings-error { color: #ff6b6b; height: 1; }
    """

    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self.settings = settings

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="settings-card"):
            yield Static("◆  SYSTEM CONFIG  ◆", classes="modal-title")
            with Grid(id="settings-grid"):
                yield Label("Visual theme", classes="setting-label")
                yield Select(
                    (
                        ("MIDNIGHT ARCADE", "midnight"),
                        ("GAME BOY", "gameboy"),
                        ("SUNSET DRIVE", "sunset"),
                    ),
                    value=self.settings.ui_theme,
                    allow_blank=False,
                    id="ui-theme",
                )
                yield Label("Focus minutes", classes="setting-label")
                yield Input(str(self.settings.focus_minutes), id="focus-minutes", type="integer")
                yield Label("Short break minutes", classes="setting-label")
                yield Input(str(self.settings.short_break_minutes), id="short-minutes", type="integer")
                yield Label("Long break minutes", classes="setting-label")
                yield Input(str(self.settings.long_break_minutes), id="long-minutes", type="integer")
                yield Label("Focuses before long break", classes="setting-label")
                yield Input(str(self.settings.sessions_before_long_break), id="cycle-count", type="integer")
                yield Label("Completion melody", classes="setting-label")
                yield Switch(self.settings.sound_enabled, id="sound-enabled")
                yield Label("Sound pack", classes="setting-label")
                yield Select(
                    (("ARCADE", "arcade"), ("VICTORY", "victory"), ("GENTLE", "gentle")),
                    value=self.settings.sound_theme,
                    allow_blank=False,
                    id="sound-theme",
                )
                yield Label("Qur'an verses on breaks", classes="setting-label")
                yield Switch(self.settings.quran_enabled, id="quran-enabled")
                yield Label("Auto-start breaks", classes="setting-label")
                yield Switch(self.settings.auto_start_breaks, id="auto-break")
                yield Label("Auto-start focus", classes="setting-label")
                yield Switch(self.settings.auto_start_focus, id="auto-focus")
            yield Label("", id="settings-error")
            with Grid(id="settings-actions"):
                yield Button("SAVE", id="save-settings", variant="success")
                yield Button("CANCEL", id="cancel-settings")
        yield CommandBar("TAB move  ·  ENTER choose/toggle  ·  CTRL+S save  ·  ESC cancel")

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_save(self) -> None:
        self._save_settings()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-settings":
            self.action_cancel()
            return
        if event.button.id != "save-settings":
            return
        self._save_settings()

    def _save_settings(self) -> None:
        try:
            values = [
                int(self.query_one(selector, Input).value)
                for selector in ("#focus-minutes", "#short-minutes", "#long-minutes", "#cycle-count")
            ]
            if any(value < 1 for value in values) or any(value > 999 for value in values[:3]):
                raise ValueError
        except ValueError:
            self.query_one("#settings-error", Label).update("Use positive durations (maximum 999 minutes).")
            return
        self.dismiss(
            Settings(
                focus_minutes=values[0],
                short_break_minutes=values[1],
                long_break_minutes=values[2],
                sessions_before_long_break=values[3],
                sound_enabled=self.query_one("#sound-enabled", Switch).value,
                sound_theme=str(self.query_one("#sound-theme", Select).value),
                ui_theme=str(self.query_one("#ui-theme", Select).value),
                pet_key=self.settings.pet_key,
                quran_enabled=self.query_one("#quran-enabled", Switch).value,
                auto_start_breaks=self.query_one("#auto-break", Switch).value,
                auto_start_focus=self.query_one("#auto-focus", Switch).value,
            )
        )


class ReflectionScreen(ModalScreen[tuple[str, int | None] | None]):
    BINDINGS = [("escape", "skip", "Skip"), ("ctrl+s", "save", "Save")]
    CSS = """
    ReflectionScreen { align: center middle; background: #090b12e8; }
    #reflection-card { width: 72; height: 23; padding: 1 2;
        border: heavy #70e1c1; background: #151927; }
    #actual-work { height: 8; margin: 1 0; }
    #rating { width: 16; }
    #reflection-actions { height: 3; grid-size: 2; grid-gutter: 1; margin-top: 1; }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="reflection-card"):
            yield Static("★  QUEST COMPLETE  ★", classes="modal-title")
            yield Label("What did you actually accomplish?")
            yield TextArea(id="actual-work")
            yield Label("Focus quality (1–5, optional)")
            yield Input(placeholder="1-5", id="rating", type="integer")
            with Grid(id="reflection-actions"):
                yield Button("SAVE REFLECTION", id="save-reflection", variant="success")
                yield Button("SKIP", id="skip-reflection")
        yield CommandBar("TAB move  ·  CTRL+S save reflection  ·  ESC skip")

    def action_skip(self) -> None:
        self.dismiss(None)

    def action_save(self) -> None:
        self._save_reflection()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "skip-reflection":
            self.action_skip()
            return
        if event.button.id == "save-reflection":
            self._save_reflection()

    def _save_reflection(self) -> None:
        actual = self.query_one("#actual-work", TextArea).text
        raw_rating = self.query_one("#rating", Input).value.strip()
        rating = int(raw_rating) if raw_rating.isdigit() and 1 <= int(raw_rating) <= 5 else None
        self.dismiss((actual, rating))
