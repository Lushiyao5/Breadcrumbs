import asyncio

from textual.widgets import OptionList, Static

from breadcrumbs.activity import Context
from breadcrumbs.app import BreadcrumbsApp
from breadcrumbs.branches import ActivityDetailScreen, BranchesScreen
from breadcrumbs.timer import TimerKind, TimerStatus
from breadcrumbs.db import Database


def test_break_timeline_excludes_paused_and_offline_gaps(tmp_path):
    db = Database(tmp_path / "breaks.db")
    root = db.begin_session("focus", 60, "", "steady-session")
    db.finish_session(root, 60)
    rest = db.begin_session("long_break", 60, "", session_root=root)
    db.open_span(rest, 1000)
    db.close_spans(rest, 1002)
    db.open_span(rest, 2000)
    db.close_spans(rest, 2003)
    rows = db.session_trail(root)
    assert [row["ended_at"] - row["started_at"] for row in rows] == [2, 3]
    assert all(row["classification"] == "break" for row in rows)
    assert db.activity_for(rest) == []
    assert db.recoverable("steady-session")[0]["id"] == rest
    assert db.recoverable(db.recent(1)[0]["name"])[0]["name"] == "steady-session"
    db.close()


def test_explicit_new_from_recovery_preserves_old_saved_block(tmp_path, monkeypatch):
    monkeypatch.setenv("BREADCRUMBS_HOME", str(tmp_path))

    async def exercise():
        original = BreadcrumbsApp(session_name="keep-old-save")
        original.settings.browser_bridge_port = 0
        async with original.run_test():
            original._begin_block()
            old = original.active_session_id
        app = BreadcrumbsApp()
        app.settings.browser_bridge_port = 0
        async with app.run_test() as pilot:
            await pilot.press("escape")
            assert app._session_root is None
            assert app.session_name != "keep-old-save"
            assert app.database.recoverable("keep-old-save")[0]["id"] == old
            app._begin_block()
            assert app._session_root != old

    asyncio.run(exercise())


def test_terminal_hint_updates_the_live_logo_without_changing_recorded_scope(tmp_path, monkeypatch):
    monkeypatch.setenv("BREADCRUMBS_HOME", str(tmp_path))

    async def exercise():
        app = BreadcrumbsApp(session_name="terminal-hint")
        app.settings.browser_bridge_port = 0
        app._tracking_settings.activity_source = "desktop"
        app._tracking_settings.activity_apps = ["windowsterminal"]
        app._activity_next_poll = float("inf")
        async with app.run_test():
            app._begin_block()
            context = Context("WindowsTerminal.exe", title="Codex — review")
            app._current_context = context
            app._refresh_activity_bar()
            display = app.query_one("#active-context", Static).renderable.plain
            assert "Codex (title hint)" in display and "In scope" in display
            assert app._classify(context) == "planned"
            assert context.app == "WindowsTerminal.exe" and not context.agent_id

    asyncio.run(exercise())


def test_session_survives_focus_break_focus_restart_and_explicit_new(tmp_path, monkeypatch):
    monkeypatch.setenv("BREADCRUMBS_HOME", str(tmp_path))

    async def exercise():
        app = BreadcrumbsApp(session_name="one-work-session")
        app.settings.sound_enabled = False
        app._activity_next_poll = float("inf")
        async with app.run_test(size=(120, 42)) as pilot:
            app._begin_block()
            first, root = app.active_session_id, app._session_root
            app.timer.status = TimerStatus.FINISHED
            app._complete_timer()
            await pilot.press("escape")
            await pilot.pause()
            assert app.timer.kind is TimerKind.SHORT_BREAK
            assert app.session_name == "one-work-session"
            app._begin_block()
            rest = app.active_session_id
            assert rest != first and app._session_root == root
            assert not app._capture_wanted()
            app.action_toggle()
            assert app.timer.status is TimerStatus.PAUSED
            app.action_toggle()
            app.timer.status = TimerStatus.FINISHED
            app._complete_timer()
            assert app.timer.kind is TimerKind.FOCUS
            assert app.session_name == "one-work-session"
            app._begin_block()
            assert app._session_root == root
            assert {row["session_root"] for row in app.database.export()} == {root}
            assert {row["session_name"] for row in app.database.export()} == {"one-work-session"}
            trail = app.database.session_trail(root)
            assert sum(row["classification"] == "break" for row in trail) == 2
            assert not app.database.activity_for(rest)

        restored = BreadcrumbsApp(resume_name="one-work-session")
        async with restored.run_test(size=(120, 42)) as pilot:
            assert restored._session_root == root
            assert restored.session_name == "one-work-session"
            assert restored.timer.status is TimerStatus.PAUSED
            restored._finish_block(restored.timer.elapsed_seconds, "early", lambda: restored._configure(TimerKind.FOCUS))
            await pilot.press("escape")
            await pilot.pause()
        reopened = BreadcrumbsApp()
        async with reopened.run_test(size=(120, 42)) as pilot:
            assert reopened._session_root == root
            assert reopened.session_name == "one-work-session"
            await pilot.press("ctrl+n")
            assert reopened._session_root is None
            assert reopened.session_name != "one-work-session"
            reopened._begin_block()
            assert reopened._session_root != root
            assert len(reopened.database.named_sessions()) == 2

    asyncio.run(exercise())


def test_latest_follow_preserves_older_selection_and_opens_details_on_small_terminal(tmp_path, monkeypatch):
    monkeypatch.setenv("BREADCRUMBS_HOME", str(tmp_path))

    async def exercise():
        app = BreadcrumbsApp()
        async with app.run_test(size=(80, 24)) as pilot:
            sid = app.database.begin_session("focus", 1500, "Timeline")
            span = app.database.open_span(sid, 1000)
            for i in range(60):
                app.database.record_activity(sid, span, Context(f"app-{i}"), "planned" if i % 2 else "unclassified", 1000 + i)
            app.push_screen(BranchesScreen(app.database, sid))
            await pilot.pause()
            screen = app.screen
            trail = screen.query_one("#trail", OptionList)
            assert trail.highlighted == trail.option_count - 1
            assert trail.scroll_y == trail.max_scroll_y and trail.max_scroll_y > 0
            last_id = screen._rows[-1]["id"]
            app.database.record_activity(sid, span, Context("app-59"), "planned", 1060)
            screen._refresh_trail()
            await pilot.pause()
            assert screen._rows[-1]["id"] == last_id
            assert trail.highlighted == trail.option_count - 1
            assert trail.scroll_y == trail.max_scroll_y
            trail.highlighted = 10
            await pilot.pause()
            selected = screen._rows[10]["id"]
            app.database.record_activity(sid, span, Context("new-app"), "unclassified", 1061)
            screen._refresh_trail()
            await pilot.pause()
            assert screen._rows[trail.highlighted]["id"] == selected
            await pilot.press("enter")
            await pilot.pause()
            assert app.screen is screen and screen.has_class("expanded")
            assert screen.query_one("#branch-detail").region.x > trail.region.x
            assert screen.query_one("#branch-logo", Static).renderable.plain.strip()
            assert "app-10" in str(screen.query_one("#branch-info", Static).renderable)
            await pilot.press("ctrl+enter")
            assert isinstance(app.screen, ActivityDetailScreen)
            assert app.screen.query_one("#visit-logo", Static).renderable.plain.strip()
            assert "app-10" in str(app.screen.query_one("#visit-info", Static).renderable)
            await pilot.press("s")
            assert app.database.activity_label(selected) == "supporting"
            await pilot.press("escape")
            await pilot.press("escape")  # collapse sidebar
            await pilot.press("end")
            await pilot.pause()
            assert trail.highlighted == trail.option_count - 1
            assert trail.scroll_y == trail.max_scroll_y
            # Mouse activation opens the same expanded view.
            await pilot.click("#trail", offset=(3, max(0, trail.region.height - 2)))
            await pilot.pause()
            assert app.screen is screen and screen.has_class("expanded")

    asyncio.run(exercise())
