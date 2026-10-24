"""Capture the actual first-launch tour without accessing the user's data."""
import asyncio
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from breadcrumbs.app import BreadcrumbsApp


async def capture():
    previous = os.environ.get("BREADCRUMBS_HOME")
    no_color = os.environ.pop("NO_COLOR", None)
    output = Path(__file__).resolve().parents[1] / "docs" / "assets"
    with TemporaryDirectory(prefix="breadcrumbs-tour-") as home:
        os.environ["BREADCRUMBS_HOME"] = home
        try:
            app = BreadcrumbsApp(show_onboarding=True)
            async with app.run_test(size=(100, 34)) as pilot:
                await pilot.pause()
                print(app.save_screenshot(filename="onboarding.svg", path=str(output)))
                await pilot.resize_terminal(80, 24)
                app.screen.step = 7
                app.screen._refresh_step()
                await pilot.pause()
                print(app.save_screenshot(filename="onboarding-small.svg", path=str(output)))
        finally:
            if previous is None:
                os.environ.pop("BREADCRUMBS_HOME", None)
            else:
                os.environ["BREADCRUMBS_HOME"] = previous
            if no_color is not None:
                os.environ["NO_COLOR"] = no_color


if __name__ == "__main__":
    asyncio.run(capture())
