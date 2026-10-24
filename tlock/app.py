from __future__ import annotations

from textual import events
from textual.app import App, ComposeResult
from textual.containers import Grid, Horizontal, ScrollableContainer, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Input, Static, TextArea

from .config import Settings
from .db import Database
from .mascot import PixelMascot
from .screens import HistoryScreen, ReflectionScreen, SettingsScreen
from .sound import play_completion
from .timer import TimerEngine, TimerKind, TimerStatus
from .verses import Verse, random_verse
from .widgets import CommandBar, GoalEditor, PixelProgress


class TlockApp(App[None]):
    TITLE = "Tlock"
    CSS = """
    $bg: #090b12;
    $panel: #131827;
    $gold: #ffd166;
    $mint: #70e1c1;
    $pink: #ff6b9d;
    $dim: #78869f;

    Screen { background: $bg; color: #edf2f7; }
    #brand { height: 3; padding: 0 3; background: transparent; }
    #brand-name { width: 1fr; content-align: left middle; text-style: bold; color: $mint; }
    #summary { width: 1fr; content-align: right middle; color: $dim; }
    #body { height: 1fr; padding: 0 2 1 2; layout: horizontal; }
    .panel { background: $panel; border: round #303a55; padding: 1 2; margin: 0 1; }
    #timer-panel { width: 40%; min-width: 37; }
    #companion-panel { width: 1fr; min-width: 30; }
    #mode { color: $mint; text-style: bold; text-align: center; margin-top: 1; }
    #clock { color: $gold; text-style: bold; text-align: center; height: 7;
        content-align: center middle; }
    #progress { margin: 0 1 1 1; color: $mint; height: 1; text-align: center; }
    #mode-buttons { grid-size: 3; grid-gutter: 1; height: 3; }
    #control-buttons { grid-size: 3; grid-gutter: 1; height: 3; margin-top: 1; }
    Button { background: #242b40; color: #dce5f5; border: none; text-style: bold; }
    Button:hover { background: #3b465d; color: $gold; }
    #start { background: #237561; }
    #reset { color: $pink; }
    #custom-row { height: 3; margin-top: 1; }
    #custom-minutes { width: 1fr; }
    #custom { width: 13; margin-left: 1; }
    #mascot { height: 5; color: $mint; text-align: center; content-align: center middle; }
    #mascot-line { text-align: center; color: #aab4c8; height: 1; margin-bottom: 1; }
    .pet-hidden #mascot, .pet-hidden #mascot-line { display: none; }
    #goal-input { height: 1fr; min-height: 9; background: #0d111d; border: tall #303a55; }
    #goal-input:focus { border: tall $mint; }
    #goal-help { height: 2; color: $dim; text-align: center; }
    #verse { display: none; height: auto; min-height: 7; margin-top: 1; padding: 1;
        border: heavy #53617a; color: #d8e2f0; text-align: center; background: #0d111d; }
    #verse.visible { display: block; }
    .modal-title { color: $gold; text-style: bold; text-align: center; height: 2; }
    .status-ready { color: #aab4c8; }
    .status-running { color: $mint; }
    .status-paused { color: #ffad5a; }
    .status-finished { color: $gold; }

    Screen.theme-gameboy { background: #11180d; color: #d8f3a6; }
    Screen.theme-gameboy .panel { background: #1c2a14; border: round #668c3c; }
    Screen.theme-gameboy #clock { color: #c7f464; }
    Screen.theme-gameboy #progress, Screen.theme-gameboy #mascot,
    Screen.theme-gameboy #mode { color: #8fd14f; }

    Screen.theme-sunset { background: #170d24; color: #ffe6d6; }
    Screen.theme-sunset .panel { background: #281438; border: round #7d477e; }
    Screen.theme-sunset #clock { color: #ffb45e; }
    Screen.theme-sunset #progress, Screen.theme-sunset #mascot,
    Screen.theme-sunset #mode { color: #ff75a8; }

    Screen.compact #body { layout: vertical; overflow-y: scroll; overflow-x: hidden; }
    Screen.compact #timer-panel, Screen.compact #companion-panel {
        width: 100%; min-width: 0; height: auto; margin-bottom: 1; }
    Screen.compact #timer-panel { min-height: 23; }
    Screen.compact #companion-panel { min-height: 17; }
    Screen.compact #goal-input { height: 10; }

    Screen.theme-gameboy #settings-card, Screen.theme-gameboy #reflection-card,
    Screen.theme-gameboy #history-card { background: #1c2a14; border: round #88b04b; }
    Screen.theme-sunset #settings-card, Screen.theme-sunset #reflection-card,
    Screen.theme-sunset #history-card { background: #281438; border: round #a84f8e; }

    """
    BINDINGS = [
        ("space", "toggle", "Start/Pause"),
        ("r", "reset", "Reset"),
        ("m", "pet", "Pet"),
        ("n", "spawn_pet", "New pet"),
        ("c", "settings", "Config"),
        ("h", "history", "History"),
        ("e", "edit_goals", "Edit intentions"),
        ("escape", "leave_editor", "Back to timer"),
        ("1", "focus", "Focus"),
        ("2", "short_break", "Short break"),
        ("3", "long_break", "Long break"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.settings = Settings.load()
        self.database = Database()
        self.timer = TimerEngine(self.settings.focus_minutes * 60)
        self.active_session_id: int | None = None
        self.completed_focuses = self.database.stats()["completed_focuses"]
        self.current_verse: Verse | None = None
        self._home_screen: Screen | None = None

    def compose(self) -> ComposeResult:
        with Horizontal(id="brand"):
            yield Static("TLOCK", id="brand-name")
            yield Static("", id="summary")
        with ScrollableContainer(id="body"):
            with Vertical(classes="panel", id="timer-panel"):
                yield Static("FOCUS RUN", id="mode")
                yield Static(self.timer.display, id="clock")
                yield PixelProgress(id="progress")
                with Grid(id="mode-buttons"):
                    yield Button("[1] FOCUS", id="focus")
                    yield Button("[2] SHORT", id="short-break")
                    yield Button("[3] LONG", id="long-break")
                with Horizontal(id="custom-row"):
                    yield Input(placeholder="custom minutes", id="custom-minutes", type="integer")
                    yield Button("SET TIMER", id="custom")
                with Grid(id="control-buttons"):
                    yield Button("▶ START", id="start")
                    yield Button("■ RESET", id="reset")
                    yield Button("◆ CONFIG", id="settings")
            with VerticalScroll(classes="panel", id="companion-panel"):
                yield PixelMascot(self.settings.pet_key, id="mascot")
                yield Static("Ready when you are.", id="mascot-line")
                yield GoalEditor(self.database.load_draft(), id="goal-input")
                yield Static("CTRL+B new task  ·  F2 tick/untick  ·  mouse wheel scrolls", id="goal-help")
                yield Static("", id="verse")
        yield CommandBar(
            "SPACE start/pause · E intentions · H history · C config · R reset · Q quit"
        )

    def on_mount(self) -> None:
        self._home_screen = self.screen
        self._apply_theme()
        self._apply_layout(self.size.width)
        self.set_interval(0.2, self._tick)
        self._refresh_view()
        self._refresh_history()
        self._home_query("#companion-panel", VerticalScroll).border_title = "Intentions"
        self._home_query("#timer-panel", Vertical).border_title = "Timer"
        self._home_query("#start", Button).focus()

    def on_resize(self, event: events.Resize) -> None:
        self._apply_layout(event.size.width)

    def _apply_layout(self, width: int) -> None:
        (self._home_screen or self.screen).set_class(width < 85 or self.size.height < 28, "compact")

    def _home_query(self, selector: str, expect_type):
        """Query the timer's home screen even while a modal is active."""
        return (self._home_screen or self.screen).query_one(selector, expect_type)

    def on_unmount(self) -> None:
        self._abandon_active()
        self.database.close()

    def _duration_for(self, kind: TimerKind) -> int:
        minutes = {
            TimerKind.FOCUS: self.settings.focus_minutes,
            TimerKind.SHORT_BREAK: self.settings.short_break_minutes,
            TimerKind.LONG_BREAK: self.settings.long_break_minutes,
        }.get(kind, 1)
        return minutes * 60

    def _select(self, kind: TimerKind, seconds: int | None = None) -> None:
        if self.timer.status in (TimerStatus.RUNNING, TimerStatus.PAUSED):
            self._abandon_active()
        self.timer.configure(seconds or self._duration_for(kind), kind)
        if kind in (TimerKind.SHORT_BREAK, TimerKind.LONG_BREAK):
            self.current_verse = random_verse(self.current_verse)
        self._refresh_view()

    def action_focus(self) -> None:
        self._select(TimerKind.FOCUS)

    def action_short_break(self) -> None:
        self._select(TimerKind.SHORT_BREAK)

    def action_long_break(self) -> None:
        self._select(TimerKind.LONG_BREAK)

    def action_toggle(self) -> None:
        if self.timer.status in (TimerStatus.READY, TimerStatus.PAUSED):
            if self.timer.status is TimerStatus.READY:
                goal = self._home_query("#goal-input", GoalEditor).goal_text
                self.active_session_id = self.database.begin_session(
                    self.timer.kind.value, self.timer.duration_seconds, goal
                )
            self.timer.start()
        elif self.timer.status is TimerStatus.RUNNING:
            self.timer.pause()
        elif self.timer.status is TimerStatus.FINISHED:
            self.timer.reset()
        self._refresh_view()

    def action_reset(self) -> None:
        self._abandon_active()
        self.timer.reset()
        self._refresh_view()
        self._refresh_history()

    def action_pet(self) -> None:
        mascot = self._home_query("#mascot", PixelMascot)
        mascot.pet()
        name = mascot.pet_name
        line = {
            TimerStatus.RUNNING: f"{name} believes in this block!",
            TimerStatus.PAUSED: "A tiny pause. A steady return.",
            TimerStatus.FINISHED: "We did it! High five!",
        }.get(self.timer.status, f"{name} is now extremely motivated.")
        self._home_query("#mascot-line", Static).update(line)

    def action_spawn_pet(self) -> None:
        mascot = self._home_query("#mascot", PixelMascot)
        pet_key, name = mascot.spawn()
        self.settings.pet_key = pet_key
        self.settings.save()
        self._home_query("#mascot-line", Static).update(f"A wild {name} appeared!")
        self.notify(f"{name} joined your focus party", title="NEW COMPANION")

    def action_settings(self) -> None:
        screen = SettingsScreen(self.settings)
        screen.add_class(f"theme-{self.settings.ui_theme}")
        self.push_screen(screen, self._settings_closed)

    def action_history(self) -> None:
        screen = HistoryScreen(self.database.recent(50))
        screen.add_class(f"theme-{self.settings.ui_theme}")
        self.push_screen(screen)

    def action_edit_goals(self) -> None:
        self._home_query("#goal-input", GoalEditor).focus()

    def action_leave_editor(self) -> None:
        self._home_query("#start", Button).focus()

    def _settings_closed(self, settings: Settings | None) -> None:
        if settings is None:
            return
        self.settings = settings
        settings.save()
        self._apply_theme()
        if self.timer.status is TimerStatus.READY and self.timer.kind is not TimerKind.CUSTOM:
            self._select(self.timer.kind)
        self.notify("Configuration saved", title="TLOCK")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        actions = {
            "focus": self.action_focus,
            "short-break": self.action_short_break,
            "long-break": self.action_long_break,
            "start": self.action_toggle,
            "reset": self.action_reset,
            "settings": self.action_settings,
            "pet": self.action_pet,
            "spawn-pet": self.action_spawn_pet,
        }
        if button_id in actions:
            actions[button_id]()
        elif button_id == "custom":
            raw = self._home_query("#custom-minutes", Input).value.strip()
            if not raw.isdigit() or not 1 <= int(raw) <= 999:
                self.notify("Enter 1–999 minutes", severity="error")
            else:
                self._select(TimerKind.CUSTOM, int(raw) * 60)

    def _tick(self) -> None:
        if self.timer.tick():
            self._complete_timer()
        self._refresh_view()

    def _complete_timer(self) -> None:
        completed_id = self.active_session_id
        if completed_id is not None:
            self.database.finish_session(completed_id, self.timer.duration_seconds)
            self.active_session_id = None
        play_completion(self.settings.sound_enabled, self.settings.sound_theme)
        if self.timer.kind in (TimerKind.FOCUS, TimerKind.CUSTOM):
            self.completed_focuses += 1
            if completed_id is not None:
                reflection = ReflectionScreen()
                reflection.add_class(f"theme-{self.settings.ui_theme}")
                self.push_screen(
                    reflection,
                    lambda result: self._reflection_closed(completed_id, result),
                )
        else:
            self._select(TimerKind.FOCUS)
            if self.settings.auto_start_focus:
                self.action_toggle()
        self._refresh_history()

    def _reflection_closed(
        self, session_id: int, result: tuple[str, int | None] | None
    ) -> None:
        if result is not None:
            self.database.add_reflection(session_id, result[0], result[1])
        next_kind = (
            TimerKind.LONG_BREAK
            if self.completed_focuses % self.settings.sessions_before_long_break == 0
            else TimerKind.SHORT_BREAK
        )
        self._home_query("#goal-input", GoalEditor).carry_remaining()
        self.database.save_draft(self._home_query("#goal-input", GoalEditor).text)
        self._select(next_kind)
        self._refresh_history()
        if self.settings.auto_start_breaks:
            self.action_toggle()

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        if event.text_area.id == "goal-input":
            editor = self._home_query("#goal-input", GoalEditor)
            self.database.save_draft(editor.text)
            if self.active_session_id is not None:
                self.database.update_goal(self.active_session_id, editor.goal_text)

    def _apply_theme(self) -> None:
        for theme in ("midnight", "gameboy", "sunset"):
            (self._home_screen or self.screen).remove_class(f"theme-{theme}")
        (self._home_screen or self.screen).add_class(f"theme-{self.settings.ui_theme}")
        (self._home_screen or self.screen).set_class(not self.settings.pet_enabled, "pet-hidden")

    def _abandon_active(self) -> None:
        if self.active_session_id is not None:
            self.database.abandon_session(self.active_session_id, self.timer.elapsed_seconds)
            self.active_session_id = None

    def _refresh_view(self) -> None:
        is_break = self.timer.kind in (TimerKind.SHORT_BREAK, TimerKind.LONG_BREAK)
        names = {
            TimerKind.FOCUS: "FOCUS RUN",
            TimerKind.SHORT_BREAK: "SHORT BREAK",
            TimerKind.LONG_BREAK: "LONG BREAK",
            TimerKind.CUSTOM: "CUSTOM TIMER",
        }
        self._home_query("#mode", Static).update(names[self.timer.kind])
        clock = self._home_query("#clock", Static)
        clock.update(self.timer.display)
        clock.set_classes(f"status-{self.timer.status.value}")
        self._home_query("#progress", PixelProgress).set_progress(self.timer.progress)
        self._home_query("#mascot", PixelMascot).set_state(self.timer.status, is_break)
        labels = {
            TimerStatus.READY: "Ready when you are.",
            TimerStatus.RUNNING: "Breathe. One task. Keep going." if not is_break else "Stretch, hydrate, and look far away.",
            TimerStatus.PAUSED: "Paused. Your place is safe.",
            TimerStatus.FINISHED: "Block complete. Nicely done!",
        }
        self._home_query("#mascot-line", Static).update(labels[self.timer.status])
        self._home_query("#start", Button).label = {
            TimerStatus.READY: "▶ START",
            TimerStatus.RUNNING: "Ⅱ PAUSE",
            TimerStatus.PAUSED: "▶ RESUME",
            TimerStatus.FINISHED: "↺ AGAIN",
        }[self.timer.status]
        verse_panel = self._home_query("#verse", Static)
        if is_break and self.settings.quran_enabled and self.current_verse:
            verse_panel.update(
                f"{self.current_verse.arabic}\n\n{self.current_verse.translation}\n— {self.current_verse.reference}"
            )
            verse_panel.add_class("visible")
        else:
            verse_panel.remove_class("visible")

    def _refresh_history(self) -> None:
        stats = self.database.stats()
        cycle = self.completed_focuses % self.settings.sessions_before_long_break
        self._home_query("#summary", Static).update(
            f"{stats['completed_focuses']} focus blocks · cycle {cycle}/{self.settings.sessions_before_long_break}"
        )
