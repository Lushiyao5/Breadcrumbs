from __future__ import annotations

import sqlite3
import time

from textual import events
from textual.app import App, ComposeResult
from textual.containers import Grid, Horizontal, ScrollableContainer, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Input, Static, TextArea

from .config import Settings
from .db import Database
from .mascot import PixelMascot
from .screens import HistoryScreen, PresetScreen, RecoveryScreen, ReflectionScreen, SessionDecisionScreen, SettingsScreen
from .session_names import normalize_name
from .sound import play_completion
from .timer import TimerEngine, TimerKind, TimerStatus
from .reading import next_card
from .widgets import CommandBar, GoalEditor, PixelProgress, ReadingCard


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
    #session-name { height: 3; margin-bottom: 1; }
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
    Screen.theme-gameboy .session-card { background: #1c2a14; border: round #88b04b; }
    Screen.theme-sunset .session-card { background: #281438; border: round #a84f8e; }

    """
    BINDINGS = [
        ("space", "toggle", "Start/Pause"),
        ("r", "reset", "Reset"),
        ("f", "finish", "Finish early"),
        ("p", "presets", "Presets"),
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

    def __init__(self, resume_name: str | None = None, session_name: str | None = None) -> None:
        super().__init__()
        self.settings = Settings.load()
        self.database = Database()
        self._goal_text = self.database.load_draft()
        self.timer = TimerEngine(self.settings.focus_minutes * 60)
        self.active_session_id: int | None = None
        self.completed_focuses = self.database.stats()["completed_focuses"]
        self.session_name = session_name or self.database.new_session_name()
        self._start_new_requested = session_name is not None
        self.resume_name = resume_name
        self.resume_hint: str | None = None
        self._last_checkpoint = 0.0
        self._decision_open = False
        self._completion_pending = False
        self._reading_index: int | None = None
        self._reading_mode: str | None = None
        self._reading_due = 0.0
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
                yield Input(self.session_name, placeholder="Session name", id="session-name")
                yield PixelMascot(self.settings.pet_key, id="mascot")
                yield Static("Ready when you are.", id="mascot-line")
                yield GoalEditor(self.database.load_draft(), id="goal-input")
                yield Static("CTRL+B new task  ·  F2 tick/untick  ·  mouse wheel scrolls", id="goal-help")
                yield ReadingCard(id="verse")
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
        self._home_query("#session-name", Input).border_title = "Session name"
        self._home_query("#session-name", Input).tooltip = "Use your own name or keep the generated one."
        self._home_query("#start", Button).tooltip = "Space: start or pause. F: finish early."
        self._home_query("#focus", Button).tooltip = "P: choose a saved focus rhythm."
        self._offer_recovery()

    def _themed(self, screen):
        screen.add_class(f"theme-{self.settings.ui_theme}")
        return screen

    def _offer_recovery(self) -> None:
        if self.active_session_id is not None:
            return
        if self.resume_name:
            self._recover(self.resume_name)
        elif not self._start_new_requested:
            rows = self.database.recoverable()
            if rows:
                self.push_screen(self._themed(RecoveryScreen(rows)), self._recover)

    def _recover(self, name: str | None) -> None:
        if name is None:
            return
        rows = self.database.recoverable(name)
        if not rows:
            self.notify("No saved block with that name.", severity="error")
            return
        row = rows[0]
        self.timer.configure(row["planned_seconds"], TimerKind(row["timer_kind"]))
        self.timer.remaining_seconds = row["remaining_seconds"]
        self.timer.status = TimerStatus.PAUSED
        self.active_session_id = row["id"]
        self.session_name = row["name"]
        self._goal_text = row["goal"]
        self._home_query("#session-name", Input).value = self.session_name
        self._home_query("#goal-input", GoalEditor).load_text(row["goal"] or GoalEditor.DEFAULT_TEXT)
        self._checkpoint()
        self._refresh_view()
        self.notify(f"Recovered {name}. Press Space to resume.", title="Session recovered")

    def on_resize(self, event: events.Resize) -> None:
        self._apply_layout(event.size.width)

    def _apply_layout(self, width: int) -> None:
        (self._home_screen or self.screen).set_class(width < 85 or self.size.height < 28, "compact")

    def _home_query(self, selector: str, expect_type):
        """Query the timer's home screen even while a modal is active."""
        return (self._home_screen or self.screen).query_one(selector, expect_type)

    def on_unmount(self) -> None:
        if self.active_session_id is not None:
            self.timer.pause()
            self._checkpoint()
            self.resume_hint = self.session_name
        self.database.close()

    def _checkpoint(self) -> None:
        if self.active_session_id is not None:
            self.database.checkpoint(
                self.active_session_id, self.timer.remaining_seconds,
                self.timer.status.value, self._goal_text,
            )
        self._last_checkpoint = time.monotonic()

    def _duration_for(self, kind: TimerKind) -> int:
        minutes = {
            TimerKind.FOCUS: self.settings.focus_minutes,
            TimerKind.SHORT_BREAK: self.settings.short_break_minutes,
            TimerKind.LONG_BREAK: self.settings.long_break_minutes,
        }.get(kind, 1)
        return minutes * 60

    def _select(self, kind: TimerKind, seconds: int | None = None) -> None:
        if self.active_session_id is not None:
            self._request_change(lambda: self._configure(kind, seconds), "switch timers")
            return
        self._configure(kind, seconds)

    def _configure(self, kind: TimerKind, seconds: int | None = None) -> None:
        self.timer.configure(seconds or self._duration_for(kind), kind)
        typed_name = self._home_query("#session-name", Input).value.strip()
        if typed_name and not self.database.name_exists(typed_name):
            self.session_name = typed_name
        elif self.database.name_exists(self.session_name):
            self.session_name = self.database.new_session_name()
        self._home_query("#session-name", Input).value = self.session_name
        self._reading_due = 0.0
        self._refresh_view()

    def action_focus(self) -> None:
        self._select(TimerKind.FOCUS)

    def action_short_break(self) -> None:
        self._select(TimerKind.SHORT_BREAK)

    def action_long_break(self) -> None:
        self._select(TimerKind.LONG_BREAK)

    def action_toggle(self) -> None:
        if self.timer.status is TimerStatus.FINISHED and self.active_session_id is not None:
            self._completion_pending = False
            self._complete_timer()
            return
        if self.timer.status in (TimerStatus.READY, TimerStatus.PAUSED):
            if self.timer.status is TimerStatus.READY:
                goal = self._home_query("#goal-input", GoalEditor).goal_text
                self._goal_text = goal
                try:
                    raw_name = self._home_query("#session-name", Input).value.strip()
                    self.session_name = normalize_name(raw_name) if raw_name else self.database.new_session_name()
                    self.active_session_id = self.database.begin_session(
                        self.timer.kind.value, self.timer.duration_seconds, goal, self.session_name
                    )
                    self._home_query("#session-name", Input).value = self.session_name
                except ValueError as exc:
                    self.notify(str(exc), severity="error")
                    return
                except sqlite3.IntegrityError:
                    self.notify("That session name is already used. Choose another name.", severity="error")
                    return
            self.timer.start()
        elif self.timer.status is TimerStatus.RUNNING:
            self.timer.pause()
        elif self.timer.status is TimerStatus.FINISHED:
            self._configure(self.timer.kind, self.timer.duration_seconds)
        self._checkpoint()
        self._refresh_view()

    def action_reset(self) -> None:
        self._select(self.timer.kind, self.timer.duration_seconds)

    def action_finish(self) -> None:
        if self.active_session_id is not None:
            self._request_change(
                lambda: self._configure(self.timer.kind, self.timer.duration_seconds),
                "finish this block",
            )

    def _request_change(self, continuation, target: str) -> None:
        if self._decision_open:
            return
        was_running = self.timer.status is TimerStatus.RUNNING
        if self.timer.status is TimerStatus.FINISHED or (was_running and self.timer.tick()):
            self._completion_pending = False
            self._complete_timer()
            return
        self.timer.pause()
        self._checkpoint()
        self._decision_open = True
        self.push_screen(
            self._themed(SessionDecisionScreen(self.session_name, self.timer.elapsed_seconds, target)),
            lambda choice: self._change_decided(choice, continuation, was_running),
        )

    def _change_decided(self, choice: str, continuation, was_running: bool) -> None:
        self._decision_open = False
        if choice == "keep":
            if was_running:
                self.timer.start()
            self._checkpoint()
        elif choice == "end-session":
            self._abandon_active()
            continuation()
        elif choice == "finish-early":
            self._finish_block(self.timer.elapsed_seconds, "early", continuation)
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

    def action_presets(self) -> None:
        self.push_screen(self._themed(PresetScreen()), self._preset_chosen)

    def _preset_chosen(self, preset: tuple[int, int] | None) -> None:
        if preset is None:
            return

        def apply_preset() -> None:
            self.settings.focus_minutes, self.settings.short_break_minutes = preset
            self.settings.save()
            self._configure(TimerKind.FOCUS)

        if self.active_session_id is not None:
            self._request_change(apply_preset, f"switch to the {preset[0]}/{preset[1]} preset")
        else:
            apply_preset()

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
        self._reading_due = 0.0
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
        # A final timer callback can arrive after Textual removes screen children.
        if self._home_screen is None or not len(self._home_screen.query("#mode")):
            return
        if self.timer.tick():
            self._completion_pending = True
        if self._completion_pending and self.screen is self._home_screen:
            self._completion_pending = False
            self._complete_timer()
        if time.monotonic() - self._last_checkpoint >= 1:
            self._checkpoint()
            self._refresh_history()
        self._refresh_view()

    def _complete_timer(self) -> None:
        self._finish_block(self.timer.duration_seconds, "timer")

    def _finish_block(self, elapsed: int, reason: str, continuation=None) -> None:
        completed_id = self.active_session_id
        if completed_id is not None:
            self.database.finish_session(completed_id, elapsed, reason)
            self.active_session_id = None
        self.timer.status = TimerStatus.FINISHED
        self.timer._deadline = None
        if reason == "timer":
            play_completion(self.settings.sound_enabled, self.settings.sound_theme)
        focus_block = self.timer.kind in (TimerKind.FOCUS, TimerKind.CUSTOM)
        if focus_block and completed_id is not None:
            self.completed_focuses += 1
        if continuation is None and self.timer.kind is TimerKind.CUSTOM:
            seconds = self.timer.duration_seconds
            continuation = lambda: self._configure(TimerKind.CUSTOM, seconds)
        if completed_id is not None and (focus_block or continuation is not None):
            reflection = ReflectionScreen()
            reflection.add_class(f"theme-{self.settings.ui_theme}")
            self.push_screen(
                reflection,
                lambda result: self._reflection_closed(completed_id, result, continuation),
            )
        elif continuation is not None:
            continuation()
        else:
            self._select(TimerKind.FOCUS)
            if self.settings.auto_start_focus:
                self.action_toggle()
        self._refresh_history()

    def _reflection_closed(
        self, session_id: int, result: tuple[str, int | None] | None, continuation=None
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
        if continuation is not None:
            continuation()
            self._refresh_history()
            return
        self._select(next_kind)
        self._refresh_history()
        if self.settings.auto_start_breaks:
            self.action_toggle()

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        if event.text_area.id == "goal-input":
            editor = event.text_area
            self._goal_text = editor.goal_text
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
        self._home_query("#session-name", Input).disabled = self.active_session_id is not None
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
        verse_panel = self._home_query("#verse", ReadingCard)
        mode = self.settings.effective_reading_mode
        visible = mode != "off" and (self.settings.reading_scope == "all" or is_break)
        if visible:
            if mode != self._reading_mode:
                self._reading_index = None
                self._reading_due = 0.0
            if time.monotonic() >= self._reading_due:
                self._reading_index, text = next_card(mode, self._reading_index)
                verse_panel.show_card(text, self.settings.book_animation)
                self._reading_due = time.monotonic() + self.settings.reading_interval_seconds
                self._reading_mode = mode
            verse_panel.add_class("visible")
        else:
            verse_panel.remove_class("visible")

    def _refresh_history(self) -> None:
        today = self.database.today_summary()
        cycle = self.completed_focuses % self.settings.sessions_before_long_break
        self._home_query("#summary", Static).update(
            f"Today: {today['seconds'] // 60}m · {today['blocks']} blocks · cycle {cycle}/{self.settings.sessions_before_long_break}"
        )
