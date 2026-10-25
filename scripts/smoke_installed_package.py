"""Portable installed-wheel smoke check. Run outside the checkout with python -I."""
import asyncio
import os
import subprocess
import sys
import tempfile
from importlib.metadata import version
from importlib.resources import files
from pathlib import Path


async def exercise():
    from breadcrumbs.app import BreadcrumbsApp
    from breadcrumbs.timer import TimerStatus

    app = BreadcrumbsApp(session_name="ci-smoke")
    app.settings.sound_enabled = False
    app.settings.activity_source = "off"
    app.settings.browser_bridge_port = 0
    async with app.run_test(size=(110, 40)):
        assert app.timer.status is TimerStatus.READY
        app._begin_block()
        identity = app.active_session_id
        assert identity is not None
        assert app.timer.status is TimerStatus.RUNNING
        app.action_toggle()
        assert app.timer.status is TimerStatus.PAUSED
        app.action_toggle()
        assert app.timer.status is TimerStatus.RUNNING
        app.timer.pause()
    restored = BreadcrumbsApp(resume_name="ci-smoke")
    restored.settings.sound_enabled = False
    restored.settings.browser_bridge_port = 0
    async with restored.run_test(size=(110, 40)):
        assert restored.active_session_id == identity
        assert restored.timer.status is TimerStatus.PAUSED
        assert len(restored.database.export()) == 1


def main():
    with tempfile.TemporaryDirectory(prefix="breadcrumbs-smoke-") as data:
        os.environ["BREADCRUMBS_HOME"] = data
        expected = version("breadcrumbst")
        binary_dir = Path(sys.executable).parent
        suffix = ".exe" if os.name == "nt" else ""
        for command in ("breadcrumbs", "breadcrumbst", "tlock"):
            binary = binary_dir / (command + suffix)
            result = subprocess.check_output([str(binary), "--version"], text=True)
            assert result.strip().splitlines()[-1] == f"breadcrumbs {expected}", result
        subprocess.run([str(binary_dir / ("breadcrumbs" + suffix)), "--help"], check=True)
        root = files("breadcrumbs")
        assert (root / "assets/browser-extension/manifest.json").is_file()
        assert (root / "assets/branding/terminal.json").is_file()
        asyncio.run(exercise())
        print(f"Installed breadcrumbst {expected}: CLI, resources, timer and recovery passed")


if __name__ == "__main__":
    main()
