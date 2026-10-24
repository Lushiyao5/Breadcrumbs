from __future__ import annotations

from dataclasses import replace
from textual.app import ComposeResult
from textual.containers import Grid, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select, Static, Switch, TextArea

from .config import Settings
from .sound import play_completion
from .widgets import CommandBar


class SettingsScreen(ModalScreen[Settings | None]):
    BINDINGS = [("escape", "cancel", "Cancel"), ("ctrl+s", "save", "Save")]
    CSS = """
    SettingsScreen { align: center middle; background: #090b12e8; }
    #settings-card { width: 90%; max-width: 72; height: auto; max-height: 90%; padding: 1 2;
        border: heavy #ffd166; background: #151927; }
    #settings-grid { grid-size: 2; grid-columns: 1fr 20; grid-gutter: 1; height: auto; }
    #settings-actions { height: 3; grid-size: 2; grid-gutter: 1; margin-top: 1; }
    .setting-label { height: 3; content-align: left middle; }
    #settings-error { color: #ff6b6b; height: 1; }
    #sound-pack-label { height: 3; }
    #sound-pack-label Label { width: 1fr; }
    #preview-sound { width: 11; min-width: 11; padding: 0; }
    #browser-connection { width: 100%; height: 3; }
    #browser-connection-status { height: auto; color: #78869f; margin-bottom: 1; }
    """

    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self.settings = settings

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="settings-card"):
            yield Static("Settings", classes="modal-title")
            yield Button("Browser connection", id="browser-connection", variant="success")
            yield Static("", id="browser-connection-status", markup=False)
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
                yield Label("Show companion", classes="setting-label")
                yield Switch(self.settings.pet_enabled, id="pet-enabled")
                yield Label("Focus minutes", classes="setting-label")
                yield Input(str(self.settings.focus_minutes), id="focus-minutes", type="integer")
                yield Label("Short break minutes", classes="setting-label")
                yield Input(str(self.settings.short_break_minutes), id="short-minutes", type="integer")
                yield Label("Long break minutes", classes="setting-label")
                yield Input(str(self.settings.long_break_minutes), id="long-minutes", type="integer")
                yield Label("Full focus blocks per long break", classes="setting-label")
                yield Input(str(self.settings.sessions_before_long_break), id="cycle-count", type="integer")
                yield Label("Completion melody", classes="setting-label")
                yield Switch(self.settings.sound_enabled, id="sound-enabled")
                with Horizontal(id="sound-pack-label"):
                    yield Label("Sound pack", classes="setting-label")
                    yield Button(
                        "Preview", id="preview-sound",
                        tooltip="Hear the selected pack, even when completion sounds are off. Does not save changes.",
                    )
                yield Select(
                    (("ARCADE", "arcade"), ("VICTORY", "victory"), ("GENTLE", "gentle")),
                    value=self.settings.sound_theme,
                    allow_blank=False,
                    id="sound-theme",
                )
                yield Label("Reading cards", classes="setting-label")
                yield Select(
                    (("Off", "off"), ("Qur'an", "quran"), ("Quotes", "quotes")),
                    value=self.settings.effective_reading_mode, allow_blank=False, id="reading-mode",
                )
                yield Label("Show reading cards", classes="setting-label")
                yield Select(
                    (("Every block", "all"), ("Breaks only", "breaks")),
                    value=self.settings.reading_scope, allow_blank=False, id="reading-scope",
                )
                yield Label("Change card every (minutes)", classes="setting-label")
                yield Input(str(max(1, self.settings.reading_interval_seconds // 60)), type="integer", id="reading-minutes")
                yield Label("Book animation", classes="setting-label")
                yield Switch(self.settings.book_animation, id="book-animation")
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
        if event.button.id == "browser-connection":
            event.stop()
            self.app.action_browser_connection()
            return
        if event.button.id == "preview-sound":
            event.stop()
            button = event.button
            button.disabled = True
            play_completion(True, str(self.query_one("#sound-theme", Select).value))
            self.set_timer(1.0, lambda: setattr(button, "disabled", False))
            return
        if event.button.id == "cancel-settings":
            self.action_cancel()
            return
        if event.button.id != "save-settings":
            return
        self._save_settings()

    def on_mount(self):
        self.refresh_connection()
        self.set_interval(1.0, self.refresh_connection)

    def refresh_connection(self):
        bridge = getattr(self.app, "_bridge", None)
        connected = bridge is not None and bridge.state.client_connected()
        from . import __version__
        versions = bridge.state.status().get("browser_diagnostics", {}).get("versions", []) if bridge else []
        outdated = connected and any(version != __version__ for version in versions)
        self.query_one("#browser-connection-status", Static).update(
            "Old extension detected · reload it in chrome://extensions / edge://extensions" if outdated else
            "Browser connected · session sync active" if connected else
            "Open Browser connection to pair or reconnect the extension"
        )

    def _save_settings(self) -> None:
        try:
            values = [
                int(self.query_one(selector, Input).value)
                for selector in ("#focus-minutes", "#short-minutes", "#long-minutes", "#cycle-count")
            ]
            if any(value < 1 for value in values) or any(value > 999 for value in values[:3]):
                raise ValueError
            reading_minutes = int(self.query_one("#reading-minutes", Input).value)
            if not 1 <= reading_minutes <= 60:
                raise ValueError
        except ValueError:
            self.query_one("#settings-error", Label).update("Durations: 1–999 min. Reading interval: 1–60 min.")
            return
        self.dismiss(
            replace(self.settings,
                focus_minutes=values[0],
                short_break_minutes=values[1],
                long_break_minutes=values[2],
                sessions_before_long_break=values[3],
                sound_enabled=self.query_one("#sound-enabled", Switch).value,
                sound_theme=str(self.query_one("#sound-theme", Select).value),
                ui_theme=str(self.query_one("#ui-theme", Select).value),
                pet_key=self.settings.pet_key,
                pet_enabled=self.query_one("#pet-enabled", Switch).value,
                quran_enabled=self.query_one("#reading-mode", Select).value == "quran",
                reading_mode=str(self.query_one("#reading-mode", Select).value),
                reading_scope=str(self.query_one("#reading-scope", Select).value),
                reading_interval_seconds=reading_minutes * 60,
                book_animation=self.query_one("#book-animation", Switch).value,
                auto_start_breaks=self.query_one("#auto-break", Switch).value,
                auto_start_focus=self.query_one("#auto-focus", Switch).value,
            )
        )


class ReflectionScreen(ModalScreen[tuple[str, int | None] | None]):
    BINDINGS = [("escape", "skip", "Skip"), ("ctrl+s", "save", "Save")]
    CSS = """
    ReflectionScreen { align: center middle; background: #090b12e8; }
    #reflection-card { width: 90%; max-width: 72; height: 23; max-height: 90%; overflow-y: auto; padding: 1 2;
        border: heavy #70e1c1; background: #151927; }
    #actual-work { height: 8; margin: 1 0; }
    #rating { width: 16; }
    #reflection-actions { height: 3; grid-size: 2; grid-gutter: 1; margin-top: 1; }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="reflection-card"):
            yield Static("Block complete", classes="modal-title")
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


class SessionDecisionScreen(ModalScreen[str]):
    BINDINGS = [("escape", "cancel", "Keep working")]
    CSS = """
    SessionDecisionScreen, RecoveryScreen, PresetScreen { align: center middle; background: #090b12e8; }
    .session-card { width: 90%; max-width: 76; height: auto; max-height: 90%;
        padding: 1 2; border: round #70e1c1; background: #151927; }
    .session-card Static { height: auto; margin-bottom: 1; }
    .session-card Button { width: 100%; margin-top: 1; }
    .session-card Select { margin-bottom: 1; }
    """

    def __init__(self, name: str, elapsed: int, target: str) -> None:
        super().__init__()
        self.session_name = name
        self.elapsed = elapsed
        self.target = target

    def compose(self) -> ComposeResult:
        with VerticalScroll(classes="session-card"):
            yield Static("What should happen to this block?", classes="modal-title")
            yield Static(
                f"{self.session_name} · {self.elapsed // 60}m {self.elapsed % 60}s worked\n\n"
                f"Before you {self.target}:\n"
                "Finish early saves your work as completed and opens a reflection.\n"
                "End session records the partial time without marking it completed.",
                markup=False,
            )
            yield Button("Keep working", id="keep", variant="success")
            yield Button("Finish early", id="finish-early")
            yield Button("End session", id="end-session")
        yield CommandBar("TAB choose · ENTER confirm · ESC keep working")

    def action_cancel(self) -> None:
        self.dismiss("keep")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.id in ("keep", "finish-early", "end-session"):
            self.dismiss(event.button.id)


class RecoveryScreen(ModalScreen[str | None]):
    BINDINGS = [("escape", "new", "Start new")]
    CSS = SessionDecisionScreen.CSS

    def __init__(self, rows: list[dict]) -> None:
        super().__init__()
        self.rows = rows

    def compose(self) -> ComposeResult:
        with VerticalScroll(classes="session-card"):
            yield Static("Pick up where you left off?", classes="modal-title")
            yield Static(
                "Saved blocks reopen paused at their last checkpoint.\n"
                "Time away from Breadcrumbs is not counted. Starting a new block keeps these saves."
            )
            yield Select(
                [(f"{r['name']} · {int(r['remaining_seconds']) // 60} min left", r["name"]) for r in self.rows],
                value=self.rows[0]["name"], allow_blank=False, id="recover-name",
            )
            yield Button("Resume saved block", id="recover", variant="success")
            yield Button("Start a new block", id="new-block")
            yield Static("Later: breadcrumbs --resume NAME\nList saved blocks: breadcrumbs sessions")
        yield CommandBar("TAB choose · ENTER confirm · ESC start new")

    def action_new(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.id == "recover":
            self.dismiss(str(self.query_one("#recover-name", Select).value))
        elif event.button.id == "new-block":
            self.action_new()


class PresetScreen(ModalScreen[tuple[int, int] | None]):
    BINDINGS = [("escape", "cancel", "Cancel")]
    CSS = SessionDecisionScreen.CSS

    def compose(self) -> ComposeResult:
        with VerticalScroll(classes="session-card"):
            yield Static("Choose a focus rhythm", classes="modal-title")
            yield Static("Focus / short break. Long-break settings stay as configured.")
            yield Button("Pomodoro · 25 / 5 minutes", id="preset-25")
            yield Button("Extended · 50 / 10 minutes", id="preset-50")
            yield Button("Deep work · 60 / 10 minutes", id="preset-60")
            yield Button("Cancel", id="cancel-preset")
        yield CommandBar("TAB choose · ENTER select · ESC cancel")

    def action_cancel(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        choices = {"preset-25": (25, 5), "preset-50": (50, 10), "preset-60": (60, 10)}
        self.dismiss(choices.get(event.button.id))


class HistoryScreen(ModalScreen[None]):
    """Recent activity kept away from the working surface."""

    BINDINGS = [("escape", "close", "Close")]
    CSS = """
    HistoryScreen { align: center middle; background: #090b12e8; }
    #history-card { width: 90%; max-width: 90; height: 85%; padding: 1 2;
        border: round #303a55; background: #151927; }
    .history-entry { height: auto; padding: 1 0; border-bottom: solid #303a55; }
    """

    def __init__(self, rows: list[dict]) -> None:
        super().__init__()
        self.rows = rows

    def compose(self) -> ComposeResult:
        from datetime import datetime

        with VerticalScroll(id="history-card"):
            yield Static("Recent activity", classes="modal-title")
            if not self.rows:
                yield Static("No sessions yet. Your completed blocks will appear here.")
            for row in self.rows:
                timestamp = datetime.fromisoformat(row["started_at"]).astimezone().strftime("%b %d, %H:%M")
                minutes = row["elapsed_seconds"] // 60
                status = {"abandoned": "ended", "running": "in progress"}.get(row["status"], row["status"])
                text = f"{timestamp} · {row['timer_kind'].replace('_', ' ')} · {minutes} min · {status}"
                if row.get("name"):
                    text = f"{row.get('session_name') or row['name']}\n{text}"
                if row.get("completion_reason") == "early":
                    text += " · finished early"
                if row["goal"]:
                    text += f"\n\n{row['goal']}"
                if row["actual"]:
                    text += f"\n\nReflection: {row['actual']}"
                if row["rating"] is not None:
                    text += f"\nFocus quality: {row['rating']}/5"
                yield Static(text, classes="history-entry", markup=False)
            yield Button("Close", id="close-history")
        yield CommandBar("UP/DOWN or mouse wheel scroll · ESC close")

    def action_close(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close-history":
            self.action_close()
