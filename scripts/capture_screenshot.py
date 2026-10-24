"""Capture the real TUI with synthetic data: python -m scripts.capture_screenshot."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from textual.widgets import Input

from breadcrumbs.app import BreadcrumbsApp
from breadcrumbs.activity import Context
from breadcrumbs.reading import QUOTES
from breadcrumbs.timer import TimerKind
from breadcrumbs.widgets import GoalEditor, ReadingCard


async def capture() -> None:
    output = Path(__file__).resolve().parents[1] / "docs" / "assets"
    output.mkdir(parents=True, exist_ok=True)
    previous = os.environ.get("BREADCRUMBS_HOME")
    previous_no_color = os.environ.pop("NO_COLOR", None)
    with TemporaryDirectory(prefix="breadcrumbs-screenshot-") as isolated_home:
        os.environ["BREADCRUMBS_HOME"] = isolated_home
        try:
            app = BreadcrumbsApp(session_name="build-focus-branches")
            app.settings.sound_enabled = False
            app.settings.reading_mode = "quotes"
            app.settings.book_animation = False
            app.settings.pet_enabled = False
            first = app.database.begin_session("focus", 1500, "Sketch the session flow", "calm-cedar")
            app.database.finish_session(first, 1500)
            app.database.add_reflection(first, "Mapped the recovery states and the next small step.", 4)
            app.completed_focuses = app.database.stats()["completed_focuses"]
            async with app.run_test(size=(132, 39)) as pilot:
                await pilot.pause()
                app._configure(TimerKind.FOCUS, 50 * 60)
                app._home_query("#session-name", Input).value = "build-focus-branches"
                app._home_query("#goal-input", GoalEditor).load_text(
                    "- [x] Map the session lifecycle\n"
                    "- [ ] Design a focus-scope picker\n"
                    "- [ ] Write down the platform limits\n\n"
                    "Keep the timer simple. Build one useful step."
                )
                await pilot.pause()
                app._tracking_settings.activity_source = "desktop"
                app._tracking_settings.activity_apps = ["code"]
                app._activity_next_poll = float("inf")
                app._begin_block()
                sid, span = app.active_session_id, app._span_id
                start = app.database.connection.execute("SELECT started_at FROM session_spans WHERE id=?", (span,)).fetchone()[0]
                for i, (context, label) in enumerate(((Context("Code.exe"), "planned"),
                        (Context("chrome.exe", domain="youtube.com"), "unclassified"), (Context("Code.exe"), "planned"))):
                    app.database.record_activity(sid, span, context, label, start+i*.01)
                app._current_context = Context("Code.exe", "Build the next step", source="fixture", notice="Documentation fixture")
                app.timer.pause()
                app.timer.remaining_seconds = 42 * 60 + 18
                app.timer.start()
                app._checkpoint()
                app._reading_mode = "quotes"
                app._reading_due = float("inf")
                app._home_query("#verse", ReadingCard).show_card(
                    QUOTES[1] + "\n\nBreadcrumbs · original reminder", animate=False
                )
                app._refresh_history()
                app._refresh_view()
                await pilot.pause()
                saved = app.save_screenshot(filename="breadcrumbs-focus.svg", path=str(output))
                print(saved)
        finally:
            if previous is None:
                os.environ.pop("BREADCRUMBS_HOME", None)
            else:
                os.environ["BREADCRUMBS_HOME"] = previous
            if previous_no_color is not None:
                os.environ["NO_COLOR"] = previous_no_color


if __name__ == "__main__":
    asyncio.run(capture())
