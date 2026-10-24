"""Actual scope/start UI screenshots with isolated, explicitly synthetic choices."""
import asyncio
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from breadcrumbs.app import BreadcrumbsApp
from breadcrumbs.branches import ScopeScreen


async def capture():
    output = Path(__file__).resolve().parents[1] / "docs" / "assets"
    old_home, old_color = os.environ.get("BREADCRUMBS_HOME"), os.environ.pop("NO_COLOR", None)
    try:
        with TemporaryDirectory(prefix="breadcrumbs-scope-capture-") as home:
            os.environ["BREADCRUMBS_HOME"] = home
            app = BreadcrumbsApp(session_name="build-the-browser-bridge")
            app.settings.browser_bridge_port = 0
            async with app.run_test(size=(120, 42)) as pilot:
                await pilot.click("#start")
                await pilot.pause()
                app.save_screenshot("start-scope.svg", str(output))
                # Synthetic inventory only; no desktop or real process queries.
                app.screen.dismiss(None)
                await pilot.pause()
                bridge = app._ensure_bridge()
                from dataclasses import replace
                settings = replace(app.settings, activity_source="integrated", activity_apps=["code"],
                                   activity_domains=["docs.python.org"])
                app.push_screen(ScopeScreen(settings, ["code", "chrome", "WindowsTerminal"], bridge=bridge, starting=True))
                await pilot.pause()
                app.save_screenshot("select-scope.svg", str(output))
                await pilot.press("escape")
                app.action_settings()
                await pilot.pause()
                app.save_screenshot("config-browser.svg", str(output))
    finally:
        if old_home is None:
            os.environ.pop("BREADCRUMBS_HOME", None)
        else:
            os.environ["BREADCRUMBS_HOME"] = old_home
        if old_color is not None:
            os.environ["NO_COLOR"] = old_color


if __name__ == "__main__":
    asyncio.run(capture())
