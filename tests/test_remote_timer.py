import asyncio

import pytest

from breadcrumbs.app import BreadcrumbsApp
from breadcrumbs.bridge import BridgeState, ControlConflict
from breadcrumbs.timer import TimerStatus


def test_remote_controls_reject_stale_identity_and_do_not_change_with_countdown():
    state = BridgeState()
    snapshot = dict(status="running", session_id=1, name="one", remaining_seconds=100,
                    kind="focus", can_control=True, ui_theme="midnight")
    state.publish_timer(snapshot)
    revision = state.status()["timer"]["revision"]
    state.publish_timer(dict(snapshot, remaining_seconds=99))
    assert state.status()["timer"]["revision"] == revision
    with pytest.raises(ControlConflict):
        state.queue_control(dict(action="pause", session_id=2, revision=revision))
    with pytest.raises(ControlConflict):
        state.queue_control(dict(action="pause", session_id=1, revision=revision-1))
    state.queue_control(dict(action="pause", session_id=1, revision=revision))
    with pytest.raises(ControlConflict):
        state.queue_control(dict(action="finish", session_id=1, revision=revision))
    assert state.take_controls()[0]["action"] == "pause"


def test_start_pause_resume_finish_run_on_tui_and_preserve_elapsed(tmp_path, monkeypatch):
    monkeypatch.setenv("BREADCRUMBS_HOME", str(tmp_path))
    async def exercise():
        app = BreadcrumbsApp(session_name="extension-test")
        app.settings.browser_bridge_port = 0
        app.settings.sound_enabled = False
        async with app.run_test(size=(120, 44)) as pilot:
            bridge = app._ensure_bridge()
            app._publish_bridge()
            def send(action):
                timer = bridge.state.status()["timer"]
                bridge.state.queue_control(dict(action=action, session_id=timer["session_id"], revision=timer["revision"]))
                app._process_remote_controls()
            send("start")
            assert app.timer.status is TimerStatus.RUNNING
            sid = app.active_session_id
            assert app._tracking_settings.activity_source == "off"  # no implicit consent
            send("pause")
            assert app.timer.status is TimerStatus.PAUSED
            assert not bridge.state.status()["active"]
            send("resume")
            assert app.timer.status is TimerStatus.RUNNING and app.active_session_id == sid
            send("pause")
            app.timer.remaining_seconds = app.timer.duration_seconds - 123
            send("finish")
            await pilot.pause()
            row = app.database.recent(1)[0]
            assert row["status"] == "completed" and row["elapsed_seconds"] == 123
            assert row["completion_reason"] == "early"
            assert app.active_session_id is None
            assert not bridge.state.status()["timer"]["can_control"]  # reflection stays in TUI
    asyncio.run(exercise())


def test_dialogs_block_remote_controls_and_queued_commands_cannot_target_new_block(tmp_path, monkeypatch):
    monkeypatch.setenv("BREADCRUMBS_HOME", str(tmp_path))
    async def exercise():
        app = BreadcrumbsApp()
        app.settings.browser_bridge_port = 0
        async with app.run_test(size=(120, 44)) as pilot:
            bridge = app._ensure_bridge()
            app._publish_bridge()
            app.action_settings()
            await pilot.pause()
            app._publish_bridge()
            assert not bridge.state.status()["timer"]["can_control"]
            await pilot.press("escape")
            app._publish_bridge()
            timer = bridge.state.status()["timer"]
            bridge.state.queue_control(dict(action="start", session_id=None, revision=timer["revision"]))
            app._begin_block()  # user starts first; the pending start must not pause it
            sid = app.active_session_id
            app._process_remote_controls()
            assert app.active_session_id == sid and app.timer.status is TimerStatus.RUNNING
    asyncio.run(exercise())


def test_remote_pause_and_resume_work_while_viewing_branches(tmp_path, monkeypatch):
    from breadcrumbs.branches import BranchesScreen
    monkeypatch.setenv("BREADCRUMBS_HOME", str(tmp_path))
    async def exercise():
        app = BreadcrumbsApp()
        app.settings.browser_bridge_port = 0
        async with app.run_test(size=(120, 44)) as pilot:
            bridge = app._ensure_bridge()
            app._begin_block()
            app.action_branches()
            await pilot.pause()
            for action, expected in (("pause", TimerStatus.PAUSED), ("resume", TimerStatus.RUNNING)):
                app._publish_bridge()
                timer = bridge.state.status()["timer"]
                assert timer["can_control"]
                bridge.state.queue_control(dict(action=action, session_id=timer["session_id"], revision=timer["revision"]))
                app._process_remote_controls()
                assert app.timer.status is expected
                assert isinstance(app.screen, BranchesScreen)
    asyncio.run(exercise())
