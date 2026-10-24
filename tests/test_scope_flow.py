import asyncio
import time
from dataclasses import replace

from textual.widgets import Input, SelectionList

from breadcrumbs.activity import Context
from breadcrumbs.app import BreadcrumbsApp
from breadcrumbs.branches import ScopeScreen, StartSessionScreen
from breadcrumbs.config import Settings
from breadcrumbs.timer import TimerStatus


def test_start_cancel_skip_and_resume_do_not_duplicate_session(tmp_path, monkeypatch):
    monkeypatch.setenv("BREADCRUMBS_HOME", str(tmp_path))
    async def exercise():
        app = BreadcrumbsApp()
        app.settings.browser_bridge_port = 0
        async with app.run_test(size=(110, 40)) as pilot:
            await pilot.click("#start")
            await pilot.pause()
            assert isinstance(app.screen, StartSessionScreen)
            assert app.database.recent() == []
            await pilot.press("escape")
            assert app.timer.status is TimerStatus.READY
            assert app.database.recent() == []
            # Reopen with the keyboard; the previous Start click may still
            # be in Textual's active effect after a fast cancellation.
            await pilot.press("space")
            await pilot.pause()
            await pilot.click("#start-untracked")
            assert app.timer.status is TimerStatus.RUNNING
            sid = app.active_session_id
            assert app._tracking_settings.activity_source == "off"
            assert app._bridge is not None and not app._bridge.state.status()["active"]
            app.action_toggle()
            assert app.timer.status is TimerStatus.PAUSED
            app.action_toggle()
            assert app.timer.status is TimerStatus.RUNNING
            assert app.active_session_id == sid and len(app.database.recent()) == 1
    asyncio.run(exercise())


def test_select_scope_then_edit_current_block_and_recover(tmp_path, monkeypatch):
    monkeypatch.setenv("BREADCRUMBS_HOME", str(tmp_path))
    monkeypatch.setattr("breadcrumbs.app.suggested_apps", lambda: ["Code.exe", "chrome.exe"])
    monkeypatch.setattr("breadcrumbs.terminal.discover_agents", lambda: [])
    from breadcrumbs.activity import UnavailableSource
    monkeypatch.setattr("breadcrumbs.app.create_source", lambda *_: UnavailableSource("Test fixture"))
    async def exercise():
        app = BreadcrumbsApp(session_name="scope-roundtrip")
        async with app.run_test(size=(120, 48)) as pilot:
            await pilot.click("#start")
            await pilot.pause()
            await pilot.click("#start-scope")
            for _ in range(20):
                await pilot.pause(0.05)
                if isinstance(app.screen, ScopeScreen): break
            assert isinstance(app.screen, ScopeScreen)
            assert app.active_session_id is None
            app.screen.query_one("#scope-apps", SelectionList).select("code")
            app.screen.query_one("#scope-domains", Input).value = "docs.python.org"
            await pilot.press("ctrl+s")
            assert app.timer.status is TimerStatus.RUNNING
            sid, first_span = app.active_session_id, app._span_id
            assert app._tracking_settings.activity_apps == ["code"]
            assert app.database.load_scope(sid)["domains"] == ["docs.python.org"]
            app._scope_closed(replace(app._tracking_settings, activity_domains=["github.com"]))
            assert app.active_session_id == sid and app._span_id != first_span
            spans = app.database.export(include_activity=True)[0]["running_spans"]
            assert spans[0]["scope_snapshot"]["domains"] == ["docs.python.org"]
            assert spans[1]["scope_snapshot"]["domains"] == ["github.com"]
            app.action_toggle()
            assert not app._bridge.state.status()["active"]
            paused_rows = app.database.activity_for(sid)
            await pilot.pause(0.3)
            assert app.database.activity_for(sid) == paused_rows
            app._scope_closed(replace(app._tracking_settings, activity_domains=["python.org"]))
            assert app.database.load_scope(sid)["domains"] == ["python.org"]
        restored = BreadcrumbsApp(resume_name="scope-roundtrip")
        async with restored.run_test(size=(110, 40)) as pilot:
            await pilot.pause()
            assert restored.timer.status is TimerStatus.PAUSED
            assert restored._tracking_settings.activity_domains == ["python.org"]
            assert restored._bridge is not None
            assert not restored._bridge.state.status()["active"]
            restored.action_toggle()
            assert restored.active_session_id == sid
            assert restored._bridge.state.status()["active"]
    asyncio.run(exercise())


def test_without_tracking_keeps_remembered_scope_and_no_capture(tmp_path, monkeypatch):
    monkeypatch.setenv("BREADCRUMBS_HOME", str(tmp_path))
    Settings(activity_source="integrated", activity_apps=["code"]).save()
    async def exercise():
        app = BreadcrumbsApp()
        async with app.run_test(size=(110, 40)) as pilot:
            await pilot.click("#start")
            assert len(app.screen.query("#start-previous")) == 1
            await pilot.pause()
            await pilot.click("#start-untracked")
            assert app._tracking_settings.activity_source == "off"
            assert app.settings.activity_source == "integrated"
            assert Settings.load().activity_apps == ["code"]
            app._poll_activity()
            assert app._activity_future is None
            assert app.database.load_scope(app.active_session_id)["source"] == "off"
    asyncio.run(exercise())


def test_database_pages_split_navigation_without_plain_urls(tmp_path):
    from breadcrumbs.db import Database
    db = Database(tmp_path / "pages.db")
    sid = db.begin_session("focus", 60, "Work")
    span = db.open_span(sid, 1000)
    first = Context("chrome", domain="youtube.com", page_key="a" * 64)
    second = replace(first, page_key="b" * 64)
    db.record_activity(sid, span, first, "planned", 1000)
    db.record_activity(sid, span, second, "unclassified", 1001)
    assert [row["page_key"] for row in db.activity_for(sid)] == ["a" * 64, "b" * 64]
    assert "http" not in db.export_json(include_activity=True)
    db.close()


def test_page_inventory_selection_saves_current_scope(tmp_path, monkeypatch):
    monkeypatch.setenv("BREADCRUMBS_HOME", str(tmp_path))
    async def exercise():
        app = BreadcrumbsApp()
        app.settings.browser_bridge_port = 0
        async with app.run_test(size=(120, 48)) as pilot:
            bridge = app._ensure_bridge()
            app.push_screen(ScopeScreen(replace(app.settings, activity_source="integrated"),
                                        ["chrome"], bridge=bridge, starting=True),
                            lambda value: app._scope_closed(value, starting=True))
            await pilot.pause()
            bridge.state.publish(False, True, inventory=True)
            tab = dict(domain="docs.python.org", title="Docs fixture", page_key="a" * 64,
                       title_key="b" * 64, tab_id=1, window_id=1)
            bridge.state.receive_browser(dict(profile_id="fixture", browser_instance_id="fixture",
                sent_at=time.time(), focused=False, tabs=[tab]))
            app.screen.refresh_pages()
            widget = app.screen.query_one("#scope-pages", SelectionList)
            widget.select("a" * 64)
            await pilot.press("ctrl+s")
            assert app.timer.status is TimerStatus.RUNNING
            scope = app.database.load_scope(app.active_session_id)
            assert scope["pages"][0]["page_key"] == "a" * 64
            assert app._classify(Context("chrome", page_key="a" * 64)) == "planned"
            assert app._classify(Context("chrome", page_key="b" * 64)) == "unclassified"
    asyncio.run(exercise())
