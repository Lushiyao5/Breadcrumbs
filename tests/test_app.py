import asyncio

from textual.widgets import Static

from tlock.app import TlockApp
from tlock.mascot import PixelMascot
from tlock.timer import TimerKind, TimerStatus
from tlock.widgets import CommandBar, GoalEditor, PixelProgress


def test_app_mounts_and_starts_a_session(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("TLOCK_HOME", str(tmp_path))

    async def exercise() -> None:
        app = TlockApp()
        async with app.run_test(size=(140, 45)) as pilot:
            assert app.query_one("#clock", Static).renderable == "25:00"
            assert app.query_one("#progress", PixelProgress).value == 0
            await pilot.click("#goal-input")
            await pilot.press(
                "end", "s", "h", "i", "p", "space", "i", "t",
                "n", "c", "m", "r", "q", "1", "2", "3",
            )
            editor = app.query_one("#goal-input", GoalEditor)
            assert "ship itncmrq123" in editor.text
            assert app.timer.status is TimerStatus.READY
            await pilot.press("f2")
            assert editor.text.startswith("- [x]")
            await pilot.click("#start")
            assert app.timer.status is TimerStatus.RUNNING
            assert app.active_session_id is not None
            assert app.database.recent(1)[0]["goal"].startswith("- [x]")
            app.action_toggle()
            assert app.timer.status is TimerStatus.PAUSED
            assert "SPACE start/pause" in str(app.query_one(CommandBar).renderable)
            await pilot.press("c")
            app._tick()
            app._tick()
            assert app._home_query("#mode", Static).renderable == "FOCUS RUN"
            assert "CTRL+S save" in str(app.screen.query_one(CommandBar).renderable)
            await pilot.press("escape")
            await pilot.pause()

    asyncio.run(exercise())


def test_themes_and_random_pet_are_persisted(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("TLOCK_HOME", str(tmp_path))

    async def exercise() -> None:
        app = TlockApp()
        async with app.run_test(size=(140, 45)):
            app.settings.ui_theme = "gameboy"
            app._apply_theme()
            assert app.screen.has_class("theme-gameboy")
            original = app.settings.pet_key
            app.action_spawn_pet()
            assert app.settings.pet_key != original
            assert app.query_one("#mascot", PixelMascot).pet_key == app.settings.pet_key

    asyncio.run(exercise())


def test_completed_break_can_auto_start_focus(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("TLOCK_HOME", str(tmp_path))

    async def exercise() -> None:
        app = TlockApp()
        app.settings.sound_enabled = False
        app.settings.auto_start_focus = True
        async with app.run_test(size=(90, 30)):
            assert app.screen.has_class("compact")
            app.timer.configure(1, TimerKind.SHORT_BREAK)
            app.timer.status = TimerStatus.FINISHED
            app._complete_timer()
            assert app.timer.kind is TimerKind.FOCUS
            assert app.timer.status is TimerStatus.RUNNING

    asyncio.run(exercise())
