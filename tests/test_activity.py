import asyncio

from textual.widgets import Input, OptionList, Select, SelectionList, Static, Switch

from breadcrumbs.activity import Context, classify, create_source, domain_name
from breadcrumbs.app import BreadcrumbsApp
from breadcrumbs.branches import BranchesScreen, ScopeScreen, trail_prompts
from breadcrumbs.config import Settings
from breadcrumbs.db import Database


def test_scope_is_explicit_and_domains_narrow_browser_apps():
    assert classify(Context("chrome.exe", domain="youtube.com"), ["chrome"], ["docs.python.org"]) == "unclassified"
    assert classify(Context("chrome.exe", domain="docs.python.org"), [], ["python.org"]) == "planned"
    assert classify(Context("chrome.exe", domain="evilpython.org"), [], ["python.org"]) == "unclassified"
    assert classify(Context("chrome.exe", domain="youtube.com"), ["chrome"], []) == "planned"
    assert classify(Context("WindowsTerminal.exe", title="codex"), ["codex"], []) == "unclassified"
    assert classify(Context("Away", status="away"), [], []) == "away"
    assert domain_name("https://www.youtube.com/watch?v=private#token") == "youtube.com"
    assert domain_name("chrome://settings") == ""




def test_off_and_wayland_do_not_probe_desktop(monkeypatch):
    monkeypatch.setattr("breadcrumbs.activity.WindowsSource", lambda *_: (_ for _ in ()).throw(AssertionError("probe")))
    assert create_source(Settings()).sample().notice == "Tracking is off"
    monkeypatch.setattr("breadcrumbs.activity.platform.system", lambda: "Linux")
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    assert "Wayland" in create_source(Settings(activity_source="desktop")).sample().notice


def test_intervals_are_scoped_to_spans_and_gaps_remain_unknown(tmp_path):
    db = Database(tmp_path / "trace.db")
    sid = db.begin_session("focus", 1500, "Work")
    span = db.open_span(sid, 1000)
    db.save_scope(sid, {"apps": ["code"]})
    code = Context("Code.exe", "Work")
    youtube = Context("chrome.exe", domain="youtube.com")
    first = db.record_activity(sid, span, code, "planned", 1000)
    assert db.record_activity(sid, span, code, "planned", 1001) == first
    video = db.record_activity(sid, span, youtube, "unclassified", 1002)
    db.annotate_activity(video, "supporting")
    db.record_activity(sid, span, youtube, "unclassified", 1003)
    rows = db.activity_for(sid)
    assert len(rows) == 2 and rows[0]["ended_at"] == rows[1]["started_at"]
    assert rows[1]["annotation"] == "supporting"
    db.record_activity(sid, span, code, "planned", 1010)
    assert db.activity_for(sid)[2]["classification"] == "unknown"
    db.close_spans(sid, 1011)
    assert db.record_activity(sid, span, code, "planned", 1100) is None
    resumed = db.open_span(sid, 2000)
    db.save_scope(sid, {"apps": ["code", "chrome"]})
    db.record_activity(sid, resumed, code, "planned", 2000)
    assert db.activity_for(sid)[-1]["started_at"] == 2000
    assert "activity_intervals" not in db.export()[0]
    snapshots = db.export(include_activity=True)[0]["running_spans"]
    assert len(snapshots) == 2
    assert snapshots[0]["scope_snapshot"]["apps"] == ["code"]
    assert snapshots[1]["scope_snapshot"]["apps"] == ["code", "chrome"]
    db.close()


def test_crash_span_closes_at_last_observation_without_filling_offline_gap(tmp_path):
    path = tmp_path / "crash.db"
    db = Database(path)
    sid = db.begin_session("focus", 1500, "")
    span = db.open_span(sid, 1000)
    db.record_activity(sid, span, Context("Code.exe"), "planned", 1001)
    db.close()  # simulate no graceful span close
    db = Database(path)
    db.close_spans(sid)
    saved = db.connection.execute("SELECT * FROM session_spans WHERE id = ?", (span,)).fetchone()
    assert saved["ended_at"] == 1001
    resumed = db.open_span(sid, 2000)
    db.record_activity(sid, resumed, Context("Code.exe"), "planned", 2000)
    assert len(db.activity_for(sid)) == 2
    assert db.activity_for(sid)[0]["ended_at"] == 1001
    db.close()


def test_pomodoro_counts_only_full_focus_and_resets_after_full_long_break(tmp_path):
    db = Database(tmp_path / "round.db")
    older = db.begin_session("focus", 60, "")
    custom = db.begin_session("custom", 60, "")
    db.finish_session(custom, 60)
    early = db.begin_session("focus", 60, "")
    db.finish_session(early, 30, "early")
    assert db.pomodoro_progress() == 0
    full = db.begin_session("focus", 60, "")
    db.finish_session(full, 60)
    db.finish_session(full, 60)  # repeated completion is idempotent
    assert db.pomodoro_progress() == 1
    short_long_break = db.begin_session("long_break", 60, "")
    db.finish_session(short_long_break, 20, "early")
    assert db.pomodoro_progress() == 1
    rest = db.begin_session("long_break", 60, "")
    db.finish_session(rest, 60)
    assert db.pomodoro_progress() == 0
    db.finish_session(older, 60)  # resumed older ID completes after the long break
    assert db.pomodoro_progress() == 1
    db.close()
    reopened = Database(tmp_path / "round.db")
    assert reopened.pomodoro_progress() == 1
    reopened.close()


def test_empty_branches_have_no_sample_data_or_demo_controls(tmp_path, monkeypatch):
    monkeypatch.setenv("BREADCRUMBS_HOME", str(tmp_path))
    async def exercise():
        app = BreadcrumbsApp()
        async with app.run_test(size=(120, 42)) as pilot:
            app.action_branches()
            app.action_branches()
            await pilot.pause()
            assert isinstance(app.screen, BranchesScreen)
            assert not app.screen.query("#branch-demo")
            await pilot.press("d")
            assert app.screen.query_one("#trail", OptionList).option_count == 0
            assert len(app.database.export()) == 0
            await pilot.press("escape")
            await pilot.pause()
            assert "Activity off" in str(app.query_one("#active-context", Static).renderable)
            assert "until a long break" in str(app.query_one("#break-progress", Static).renderable)
    asyncio.run(exercise())


def test_late_worker_result_after_pause_is_not_recorded(tmp_path, monkeypatch):
    monkeypatch.setenv("BREADCRUMBS_HOME", str(tmp_path))
    class Fake:
        def sample(self):
            return Context("Code.exe", "Synthetic test", source="test")
    async def exercise():
        app = BreadcrumbsApp()
        app._tracking_settings.activity_source = "desktop"
        app._collector = Fake()
        async with app.run_test(size=(110, 40)):
            app._begin_block()
            sid = app.active_session_id
            app._poll_activity()
            future = app._activity_future[0]
            future.result(timeout=2)
            app.action_toggle()  # pause closes span and invalidates pending result
            app._poll_activity()
            assert app.database.activity_for(sid) == []
            app.action_toggle()
            app._activity_next_poll = 0
            app._poll_activity()
            app._activity_future[0].result(timeout=2)
            app._activity_next_poll = float("inf")
            app._poll_activity()
            assert app.database.activity_for(sid)[0]["app"] == "Code.exe"
    asyncio.run(exercise())


def test_scope_save_and_general_settings_keep_opt_in_configuration(tmp_path, monkeypatch):
    monkeypatch.setenv("BREADCRUMBS_HOME", str(tmp_path))
    async def exercise():
        app = BreadcrumbsApp()
        async with app.run_test(size=(100, 40)) as pilot:
            app.push_screen(ScopeScreen(app.settings, ["Code.exe", "chrome.exe"]), app._scope_closed)
            await pilot.pause()
            app.screen.query_one("#scope-source", Select).value = "integrated"
            app.screen.query_one("#scope-apps", SelectionList).select("code")
            app.screen.query_one("#scope-domains", Input).value = "https://docs.python.org/start?private=1"
            app.screen.query_one("#scope-titles", Switch).value = False
            await pilot.press("ctrl+s")
            await pilot.pause()
            assert app.settings.activity_source == "integrated"
            assert app.settings.activity_apps == ["code"]
            assert app.settings.activity_domains == ["docs.python.org"]
            assert app._activity_future is None  # no capture while timer is ready
            app.action_settings()
            await pilot.pause()
            await pilot.press("ctrl+s")
            await pilot.pause()
            assert app.settings.activity_source == "integrated"
            assert app.settings.activity_titles is False
    asyncio.run(exercise())


def test_small_terminal_keeps_recorded_history_and_trace_visible(tmp_path, monkeypatch):
    monkeypatch.setenv("BREADCRUMBS_HOME", str(tmp_path))
    real = Database()
    real_id = real.begin_session("focus", 60, "Real history", "real-history")
    real.finish_session(real_id, 60)
    real.close()
    async def exercise():
        app = BreadcrumbsApp()
        async with app.run_test(size=(80, 24)) as pilot:
            app.action_branches()
            await pilot.pause()
            assert isinstance(app.screen, BranchesScreen)
            assert app.screen.has_class("short")
            assert app.screen.query_one("#trail", OptionList).region.height > 0
            assert app.screen.query_one("#trail", OptionList).option_count == 0
            assert app.database.recent(1)[0]["name"] == "real-history"
            await pilot.press("escape")
            await pilot.pause()
            from breadcrumbs.widgets import CommandBar
            assert app.query_one(CommandBar).region.height >= 1
            assert app.query_one("#active-context", Static).region.y < app.query_one(CommandBar).region.y
    asyncio.run(exercise())
    real = Database()
    assert len(real.export()) == 1 and real.export()[0]["name"] == "real-history"
    real.close()
