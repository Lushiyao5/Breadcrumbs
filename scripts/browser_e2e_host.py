"""Real TUI + HTTP bridge test host, with an isolated database and desktop fixture."""
import asyncio
import json
import os
import queue
import sys
import tempfile
import threading
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from textual.widgets import Switch, SelectionList
from breadcrumbs.activity import Context, IntegratedSource, window_title_keys
from breadcrumbs.app import BreadcrumbsApp
from breadcrumbs.branches import ScopeScreen
from breadcrumbs.bridge import pairing_file
from breadcrumbs.timer import TimerStatus


async def exercise():
    class Desktop:
        context = Context("Unknown", status="unknown", notice="Isolated browser test")
        def sample(self): return self.context
    desktop = Desktop()
    inbox = queue.Queue()
    def read():
        for line in sys.stdin:
            inbox.put(json.loads(line))
        inbox.put({"command": "close"})
    threading.Thread(target=read, daemon=True).start()
    def emit(value):
        print(json.dumps(value), file=sys.__stdout__, flush=True)
    recovering = False
    with patch("breadcrumbs.app.suggested_apps", return_value=["chrome.exe", "Code.exe"]), \
         patch("breadcrumbs.terminal.discover_agents", return_value=[]), \
         patch("breadcrumbs.app.create_source", side_effect=lambda settings, bridge: IntegratedSource(settings, bridge, desktop)):
        while True:
            app = BreadcrumbsApp(resume_name="real-browser-test") if recovering else BreadcrumbsApp(session_name="real-browser-test")
            app.settings.browser_bridge_port = 0
            app.settings.sound_enabled = False
            restart = False
            async with app.run_test(size=(120, 48)) as pilot:
                if not recovering:
                    await pilot.click("#start")
                    await pilot.click("#start-scope")
                    while not isinstance(app.screen, ScopeScreen):
                        await pilot.pause(0.05)
                    bridge = app._bridge
                    # Keep the allocated test port across a full TUI/bridge restart.
                    pairing_file().write_text(json.dumps(dict(port=bridge.port, token=bridge.token)), encoding="utf-8")
                    emit(dict(address=bridge.address, token=bridge.token))
                else:
                    await pilot.pause()
                    bridge = app._bridge
                    emit(dict(restarted=True, timer_status=app.timer.status.value))
                while True:
                    try:
                        message = inbox.get_nowait()
                    except queue.Empty:
                        await pilot.pause(0.05)
                        continue
                    command = message["command"]
                    if command == "close":
                        emit({"closed": True})
                        break
                    if command == "restart":
                        restart = True
                        break
                    if command == "policy":
                        active = message.get("active")
                        titles = message.get("titles", app._tracking_settings.activity_titles)
                        if isinstance(app.screen, ScopeScreen) and active:
                            app.screen.refresh_pages()
                            page = next(page for page in bridge.state.browser_tabs() if page["domain"] == "docs.python.org")
                            app.screen.query_one("#scope-pages", SelectionList).select(page["page_key"])
                            app.screen.query_one("#scope-titles", Switch).value = titles
                            await pilot.press("ctrl+s")
                        elif active is False and app.timer.status is TimerStatus.RUNNING:
                            app.action_toggle()
                        elif active is True and app.timer.status is TimerStatus.PAUSED:
                            app.action_toggle()
                        if titles != app._tracking_settings.activity_titles:
                            from dataclasses import replace
                            app._scope_closed(replace(app._tracking_settings, activity_titles=titles))
                    elif command == "desktop":
                        context = message["context"]
                        if context.get("title"):
                            context["title_keys"] = window_title_keys(context["title"])
                        desktop.context = Context(**context)
                    elif command == "dismiss-reflection":
                        await pilot.press("escape")
                    await pilot.pause(0.05)
                    sid = app.active_session_id
                    emit(dict(status=bridge.state.status(), records=bridge.state.browser_records(),
                              tabs=bridge.state.browser_tabs(), rows=app.database.activity_for(sid) if sid else [],
                              timer_status=app.timer.status.value,
                              scope=app.database.load_scope(sid) if sid else None,
                              recent=app.database.recent(1),
                              span_count=app.database.connection.execute(
                                  "SELECT COUNT(*) FROM session_spans WHERE session_id = ?", (sid,)).fetchone()[0]))
            if not restart:
                return
            recovering = True


def main():
    with tempfile.TemporaryDirectory(prefix="breadcrumbs-browser-e2e-") as home:
        os.environ["BREADCRUMBS_HOME"] = home
        asyncio.run(exercise())


if __name__ == "__main__":
    main()
