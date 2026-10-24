import asyncio

from textual.widgets import Static
from textual.widgets import Button, Select

from breadcrumbs.app import BreadcrumbsApp
from breadcrumbs.mascot import PixelMascot
from breadcrumbs.timer import TimerKind, TimerStatus
from breadcrumbs.widgets import CommandBar, GoalEditor, PixelProgress


def test_sound_preview_uses_unsaved_selection_even_when_muted(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("BREADCRUMBS_HOME", str(tmp_path))
    previews = []
    monkeypatch.setattr("breadcrumbs.screens.play_completion", lambda enabled, theme: previews.append((enabled, theme)))

    async def exercise():
        app = BreadcrumbsApp()
        app.settings.sound_enabled = False
        async with app.run_test(size=(110, 45)) as pilot:
            app.action_settings()
            await pilot.pause()
            app.screen.query_one("#sound-theme", Select).value = "gentle"
            preview = app.screen.query_one("#preview-sound", Button)
            preview.scroll_visible(animate=False)
            await pilot.pause()
            await pilot.click("#preview-sound")
            assert previews == [(True, "gentle")]
            assert app.settings.sound_theme == "arcade"
            assert app.settings.sound_enabled is False
            assert not (tmp_path / "config.json").exists()
            await pilot.press("escape")
            await pilot.pause()

    asyncio.run(exercise())


def test_app_mounts_and_starts_a_session(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("BREADCRUMBS_HOME", str(tmp_path))

    async def exercise() -> None:
        app = BreadcrumbsApp()
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
            await pilot.click("#start-untracked")
            assert app.timer.status is TimerStatus.RUNNING
            assert app.active_session_id is not None
            assert app.database.recent(1)[0]["goal"].startswith("- [x]")
            app._begin_block()
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
    monkeypatch.setenv("BREADCRUMBS_HOME", str(tmp_path))

    async def exercise() -> None:
        app = BreadcrumbsApp()
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
    monkeypatch.setenv("BREADCRUMBS_HOME", str(tmp_path))

    async def exercise() -> None:
        app = BreadcrumbsApp()
        app.settings.sound_enabled = False
        app.settings.auto_start_focus = True
        async with app.run_test(size=(90, 30)):
            assert not app.screen.has_class("compact")
            app.timer.configure(1, TimerKind.SHORT_BREAK)
            app.timer.status = TimerStatus.FINISHED
            app._complete_timer()
            assert app.timer.kind is TimerKind.FOCUS
            assert app.timer.status is TimerStatus.RUNNING

    asyncio.run(exercise())


def test_drafts_carry_forward_and_history_is_safe_during_timer(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("BREADCRUMBS_HOME", str(tmp_path))

    async def exercise() -> None:
        app = BreadcrumbsApp()
        app.settings.sound_enabled = False
        async with app.run_test(size=(80, 24)) as pilot:
            assert app.screen.has_class("compact")
            assert app.screen.has_class("pet-hidden")
            editor = app.query_one("#goal-input", GoalEditor)
            editor.load_text("- [x] Done\n- [ ] Next\nA note")
            await pilot.pause()
            assert app.database.load_draft() == editor.text
            app._begin_block()
            session_id = app.active_session_id
            app.database.finish_session(session_id, 60)
            app.active_session_id = None
            app.completed_focuses += 1
            app._reflection_closed(session_id, ("Made progress", 4))
            await pilot.pause()
            assert editor.text == "- [ ] Next\nA note"
            assert app.database.load_draft() == editor.text
            app.action_history()
            await pilot.pause()
            app._tick()
            assert "Recent activity" in str(app.screen.query_one(".modal-title", Static).renderable)
            await pilot.press("escape")
            await pilot.pause()
            app.action_edit_goals()
            await pilot.pause()
            assert "F2 check/uncheck" in str(app.query_one(CommandBar).renderable)
            await pilot.press("escape")
            await pilot.pause()
            assert app.focused.id == "start"
        reopened = BreadcrumbsApp()
        assert reopened.database.load_draft() == "- [ ] Next\nA note"
        reopened.database.close()

    asyncio.run(exercise())
