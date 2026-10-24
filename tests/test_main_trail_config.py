import asyncio

from textual.widgets import Select

from breadcrumbs.activity import Context
from breadcrumbs.app import BreadcrumbsApp
from breadcrumbs.branches import BranchesScreen, PairBrowserScreen, ScopeScreen
from breadcrumbs.screens import SettingsScreen
from breadcrumbs.widgets import MiniTrail


def test_connection_setup_lives_in_config_and_preserves_unsaved_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("BREADCRUMBS_HOME", str(tmp_path))
    async def exercise():
        app = BreadcrumbsApp()
        app.settings.browser_bridge_port = 0
        async with app.run_test(size=(120, 44)) as pilot:
            app._begin_block()
            app.action_settings()
            await pilot.pause()
            app.screen.query_one("#ui-theme", Select).value = "gameboy"
            await pilot.click("#browser-connection")
            assert isinstance(app.screen, PairBrowserScreen)
            assert app._bridge.state.status()["timer"]["status"] == "running"
            await pilot.press("escape")
            assert isinstance(app.screen, SettingsScreen)
            assert app.screen.query_one("#ui-theme", Select).value == "gameboy"
            await pilot.press("escape")
            app.push_screen(ScopeScreen(app.settings, [], bridge=app._bridge))
            await pilot.pause()
            assert not app.screen.query("#scope-pair")
    asyncio.run(exercise())


def test_main_trail_uses_recorded_rows_without_names_and_freezes_on_pause(tmp_path, monkeypatch):
    monkeypatch.setenv("BREADCRUMBS_HOME", str(tmp_path))
    async def exercise():
        app = BreadcrumbsApp()
        app._tracking_settings.activity_source = "desktop"
        app._activity_next_poll = float("inf")
        async with app.run_test(size=(120, 44)) as pilot:
            app._begin_block()
            sid, span = app.active_session_id, app._span_id
            start = app.database.connection.execute("SELECT started_at FROM session_spans WHERE id=?", (span,)).fetchone()[0]
            for i, (context, label) in enumerate(((Context("Code.exe"), "planned"),
                    (Context("chrome.exe", domain="youtube.com"), "unclassified"), (Context("Code.exe"), "planned"))):
                app.database.record_activity(sid, span, context, label, start+i*.01)
            app._refresh_view()
            trail = app.query_one("#mini-trail", MiniTrail)
            assert "├──╮" in trail.renderable.plain and "├──╯" in trail.renderable.plain
            assert "Code" not in trail.renderable.plain and "youtube" not in trail.renderable.plain
            phase = trail.phase
            trail._advance_pulse()
            assert trail.phase != phase
            app.action_toggle()
            phase = trail.phase
            trail._advance_pulse()
            assert trail.phase == phase
            assert "Paused" in trail.renderable.plain
            await pilot.click("#mini-trail")
            assert isinstance(app.screen, BranchesScreen)
    asyncio.run(exercise())
