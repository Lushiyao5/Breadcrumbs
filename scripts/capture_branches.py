"""Capture actual UI with documentation-only fixtures in a temporary database."""
import asyncio
import os
import time
from pathlib import Path
from tempfile import TemporaryDirectory

from textual.widgets import OptionList
from breadcrumbs.activity import Context
from breadcrumbs.app import BreadcrumbsApp


async def capture():
    output = Path(__file__).resolve().parents[1] / "docs" / "assets"
    old_home = os.environ.get("BREADCRUMBS_HOME")
    old_color = os.environ.pop("NO_COLOR", None)
    try:
        with TemporaryDirectory(prefix="breadcrumbs-screenshot-") as home:
            os.environ["BREADCRUMBS_HOME"] = home
            app = BreadcrumbsApp(session_name="build-the-browser-bridge")
            app.settings.reading_mode = "quotes"
            app.settings.book_animation = False
            sid = app.database.begin_session("focus", 1500, "Documentation fixture")
            start = time.time() - 480
            span = app.database.open_span(sid, start)
            visits = [
                ("Code.exe", "Build the bridge", "", "planned"),
                ("chrome.exe", "Python documentation", "docs.python.org", "planned"),
                ("chrome.exe", "A helpful tutorial", "youtube.com", "supporting"),
                ("Code.exe", "Back to the implementation", "", "planned"),
                ("Spotify.exe", "Choose a playlist", "", "unclassified"),
                ("claude-code", "Review the implementation", "", "planned"),
                ("codex", "Check the changes", "", "planned"),
            ]
            for i, (name, title, domain, label) in enumerate(visits):
                context = Context(name, title, domain, source="fixture")
                row = app.database.record_activity(sid, span, context, label, start + i * 60)
                app.database.connection.execute("UPDATE activity_intervals SET ended_at = ? WHERE id = ?", (start + (i+1)*60, row))
            app.database.close_spans(sid, start + len(visits)*60)
            app.database.finish_session(sid, len(visits)*60)
            async with app.run_test(size=(140, 42)) as pilot:
                app.action_branches()
                await pilot.pause()
                app.screen.query_one("#trail", OptionList).highlighted = 2
                await pilot.pause()
                app.save_screenshot("focus-branches.svg", str(output))
                await pilot.press("escape")
                await pilot.pause()
                app.save_screenshot("active-context.svg", str(output))
    finally:
        if old_home is None:
            os.environ.pop("BREADCRUMBS_HOME", None)
        else:
            os.environ["BREADCRUMBS_HOME"] = old_home
        if old_color is not None:
            os.environ["NO_COLOR"] = old_color


if __name__ == "__main__":
    asyncio.run(capture())
