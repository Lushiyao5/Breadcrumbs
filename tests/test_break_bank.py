"""Deterministic tests for the break bank: skipping a due break saves its
time for a combined break after the next work stretch (issue #25)."""
import asyncio
import time

from textual.widgets import Static

from breadcrumbs.app import BreadcrumbsApp
from breadcrumbs.db import Database
from breadcrumbs.timer import TimerKind, TimerStatus


def _expire_running_timer(app) -> None:
    """Force the running block to complete on the next tick."""
    app.timer._deadline = time.monotonic() - 1
    app._tick()


async def _complete_focus_block(app, pilot) -> None:
    """Run the active focus block to timer completion, then skip the reflection."""
    _expire_running_timer(app)
    await pilot.pause()
    await pilot.press("escape")  # skip the optional reflection
    await pilot.pause()


def test_break_bank_stores_spends_and_isolates_per_named_session(tmp_path):
    db = Database(tmp_path / "bank.db")
    root_a = db.begin_session("focus", 1500, "A", "alpha-row")
    root_b = db.begin_session("focus", 1500, "B", "beta-row")
    assert db.break_bank(root_a) == 0 and db.break_bank(root_b) == 0
    assert db.bank_break(root_a, 300) == 300
    assert db.bank_break(root_a, 300) == 600  # repeated banking accumulates
    assert db.break_bank(root_b) == 0  # banks stay inside their named session
    assert db.spend_break_bank(root_a, 450) == 150
    assert db.spend_break_bank(root_a, 999) == 0  # spending never goes negative
    assert db.bank_break(None, 300) == 0  # banking needs a named session identity
    db.close()
    db = Database(tmp_path / "bank.db")
    assert db.break_bank(root_a) == 0  # the spent bank is durable
    db.close()


def test_skipping_a_due_break_banks_it_without_recording_a_session(tmp_path, monkeypatch):
    monkeypatch.setenv("BREADCRUMBS_HOME", str(tmp_path))

    async def exercise():
        app = BreadcrumbsApp(session_name="bank-run")
        app.settings.sound_enabled = False
        app.settings.browser_bridge_port = 0
        async with app.run_test(size=(110, 40)) as pilot:
            app._begin_block()
            root = app._session_root
            await _complete_focus_block(app, pilot)
            assert app.timer.kind is TimerKind.SHORT_BREAK
            assert app.timer.status is TimerStatus.READY
            short = app.settings.short_break_minutes * 60
            app.action_skip_break()
            assert app.database.break_bank(root) == short
            assert app.banked_seconds == short
            assert app.timer.kind is TimerKind.FOCUS
            assert app.timer.status is TimerStatus.READY
            hint = str(app.query_one("#break-progress", Static).renderable)
            assert "break bank" in hint
            # A skipped break is neither a completed break nor work.
            assert [row["timer_kind"] for row in app.database.export()] == ["focus"]
            assert app.database.pomodoro_progress() == 1

    asyncio.run(exercise())


def test_combined_break_is_offered_and_spends_the_bank_once(tmp_path, monkeypatch):
    monkeypatch.setenv("BREADCRUMBS_HOME", str(tmp_path))

    async def exercise():
        app = BreadcrumbsApp(session_name="bank-run")
        app.settings.sound_enabled = False
        app.settings.browser_bridge_port = 0
        async with app.run_test(size=(110, 40)) as pilot:
            app._begin_block()
            root = app._session_root
            await _complete_focus_block(app, pilot)
            short = app.settings.short_break_minutes * 60
            app.action_skip_break()  # bank the short break
            app._begin_block()  # second work stretch in the same named session
            second_id = app.active_session_id
            assert second_id != root
            await _complete_focus_block(app, pilot)
            assert app.timer.kind is TimerKind.SHORT_BREAK
            assert app.timer.duration_seconds == 2 * short  # normal break plus bank
            hint = str(app.query_one("#break-progress", Static).renderable)
            assert "Combined break" in hint and "banked" in hint
            app._begin_block()  # start the combined break
            assert app.database.break_bank(root) == 0
            row = app.database.recent(1)[0]
            assert row["timer_kind"] == "short_break"
            assert row["planned_seconds"] == 2 * short
            app.timer.pause()
            app._begin_block()  # resuming must not spend the bank again
            assert app.timer.status is TimerStatus.RUNNING
            assert app.database.break_bank(root) == 0

    asyncio.run(exercise())


def test_deferring_the_combined_break_banks_the_whole_break(tmp_path, monkeypatch):
    monkeypatch.setenv("BREADCRUMBS_HOME", str(tmp_path))

    async def exercise():
        app = BreadcrumbsApp(session_name="bank-run")
        app.settings.sound_enabled = False
        app.settings.browser_bridge_port = 0
        async with app.run_test(size=(110, 40)) as pilot:
            app._begin_block()
            root = app._session_root
            await _complete_focus_block(app, pilot)
            short = app.settings.short_break_minutes * 60
            app.action_skip_break()
            app._begin_block()
            await _complete_focus_block(app, pilot)
            assert app.timer.duration_seconds == 2 * short
            app.action_skip_break()  # defer the combined break too
            assert app.database.break_bank(root) == 3 * short
            assert app.timer.kind is TimerKind.FOCUS

    asyncio.run(exercise())


def test_skipping_a_long_break_keeps_the_round_due(tmp_path, monkeypatch):
    monkeypatch.setenv("BREADCRUMBS_HOME", str(tmp_path))

    async def exercise():
        app = BreadcrumbsApp(session_name="bank-run")
        app.settings.sound_enabled = False
        app.settings.browser_bridge_port = 0
        app.settings.sessions_before_long_break = 1
        async with app.run_test(size=(110, 40)) as pilot:
            app._begin_block()
            root = app._session_root
            await _complete_focus_block(app, pilot)
            assert app.timer.kind is TimerKind.LONG_BREAK
            long_seconds = app.settings.long_break_minutes * 60
            app.action_skip_break()
            assert app.database.break_bank(root) == long_seconds
            assert app.database.pomodoro_progress() == 1  # the round stays due
            app._begin_block()
            await _complete_focus_block(app, pilot)
            assert app.timer.kind is TimerKind.LONG_BREAK
            assert app.timer.duration_seconds == 2 * long_seconds
            app._begin_block()  # take the combined long break
            assert app.database.break_bank(root) == 0
            _expire_running_timer(app)
            await pilot.pause()
            row = app.database.recent(1)[0]
            assert row["timer_kind"] == "long_break" and row["status"] == "completed"
            assert app.database.pomodoro_progress() == 0  # completing it resets the round

    asyncio.run(exercise())


def test_bank_survives_quit_and_recovery_of_the_same_session(tmp_path, monkeypatch):
    monkeypatch.setenv("BREADCRUMBS_HOME", str(tmp_path))

    async def exercise():
        app = BreadcrumbsApp(session_name="bank-keep")
        app.settings.sound_enabled = False
        app.settings.browser_bridge_port = 0
        async with app.run_test(size=(110, 40)) as pilot:
            app._begin_block()
            root = app._session_root
            await _complete_focus_block(app, pilot)
            short = app.settings.short_break_minutes * 60
            app.action_skip_break()
            app._begin_block()  # second stretch, then quit with it paused
            app.timer.pause()
        assert app.resume_hint == "bank-keep"

        restored = BreadcrumbsApp(resume_name="bank-keep")
        async with restored.run_test(size=(110, 40)) as pilot:
            await pilot.pause()
            assert restored.timer.status is TimerStatus.PAUSED
            assert restored._session_root == root
            assert restored.banked_seconds == short
            restored.action_toggle()  # resume the recovered block
            await _complete_focus_block(restored, pilot)
            assert restored.timer.duration_seconds == 2 * short

    asyncio.run(exercise())


def test_explicit_new_session_starts_with_an_empty_bank(tmp_path, monkeypatch):
    monkeypatch.setenv("BREADCRUMBS_HOME", str(tmp_path))

    async def exercise():
        app = BreadcrumbsApp(session_name="bank-run")
        app.settings.sound_enabled = False
        app.settings.browser_bridge_port = 0
        async with app.run_test(size=(110, 40)) as pilot:
            app._begin_block()
            root = app._session_root
            await _complete_focus_block(app, pilot)
            short = app.settings.short_break_minutes * 60
            app.action_skip_break()
            assert app.banked_seconds == short
            app.action_new_session()  # explicit new named session
            assert app._session_root is None
            assert app.banked_seconds == 0
            assert app.database.break_bank(root) == short  # the old session keeps its bank

    asyncio.run(exercise())


def test_manually_selected_breaks_leave_the_bank_untouched(tmp_path, monkeypatch):
    monkeypatch.setenv("BREADCRUMBS_HOME", str(tmp_path))

    async def exercise():
        app = BreadcrumbsApp(session_name="bank-run")
        app.settings.sound_enabled = False
        app.settings.browser_bridge_port = 0
        async with app.run_test(size=(110, 40)) as pilot:
            app._begin_block()
            root = app._session_root
            await _complete_focus_block(app, pilot)
            short = app.settings.short_break_minutes * 60
            app.action_skip_break()
            app.action_short_break()  # manual pick: normal duration, bank preserved
            assert app.timer.duration_seconds == short
            app._begin_block()
            assert app.database.break_bank(root) == short
            app.action_skip_break()  # a started break can no longer be banked
            assert app.database.break_bank(root) == short

    asyncio.run(exercise())


def test_skip_is_ignored_outside_a_due_break(tmp_path, monkeypatch):
    monkeypatch.setenv("BREADCRUMBS_HOME", str(tmp_path))

    async def exercise():
        app = BreadcrumbsApp(session_name="bank-run")
        app.settings.sound_enabled = False
        app.settings.browser_bridge_port = 0
        async with app.run_test(size=(110, 40)):
            app.action_skip_break()  # focus is ready; there is nothing to bank
            assert app.timer.kind is TimerKind.FOCUS
            assert app.timer.status is TimerStatus.READY
            assert app.banked_seconds == 0

    asyncio.run(exercise())
