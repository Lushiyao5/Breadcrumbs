import asyncio

import pytest
from textual.widgets import Button, Static

from breadcrumbs.app import BreadcrumbsApp
from breadcrumbs.config import Settings
from breadcrumbs.onboarding import OnboardingScreen, TOUR_STEPS, TOUR_VERSION
from breadcrumbs.screens import RecoveryScreen
from breadcrumbs.timer import TimerStatus


@pytest.mark.parametrize("size", [(120, 42), (80, 24)])
def test_first_launch_tour_navigation_has_no_capture_or_timer_side_effects(tmp_path, monkeypatch, size):
    monkeypatch.setenv("BREADCRUMBS_HOME", str(tmp_path))

    async def exercise():
        app = BreadcrumbsApp(show_onboarding=True)
        async with app.run_test(size=size) as pilot:
            assert isinstance(app.screen, OnboardingScreen)
            screen = app.screen
            assert screen.query_one("#tour-back", Button).disabled
            # App-level shortcuts must not start timers, open dialogs, or change preferences.
            await pilot.press("space", "c", "b", "1", "m", "n", "e")
            assert app.screen is screen
            assert app.timer.status is TimerStatus.READY
            assert app.database.recent() == []
            assert app._bridge is None and app._activity_future is None
            assert not app.settings.pet_enabled
            await pilot.press("right", "left")
            assert screen.step == 0
            for index in range(len(TOUR_STEPS)):
                assert screen.step == index
                assert str(screen.query_one("#tour-title", Static).renderable) == TOUR_STEPS[index][0]
                assert screen.query_one("#tour-next", Button).region.bottom <= size[1]
                # Textual intentionally ignores clicks during the button's active effect.
                # Wait for its state, rather than relying on platform-dependent timing.
                button = screen.query_one("#tour-next", Button)
                for _ in range(80):
                    if not button.has_class("-active"):
                        break
                    await pilot.pause(0.025)
                assert not button.has_class("-active")
                await pilot.click("#tour-next")
                await pilot.pause()
            assert app.screen is app._home_screen
            assert Settings.load().onboarding_version == TOUR_VERSION
            assert app.database.recent() == []

        reopened = BreadcrumbsApp(show_onboarding=True)
        async with reopened.run_test(size=size) as pilot:
            assert reopened.screen is reopened._home_screen
            await pilot.press("question_mark")
            assert isinstance(reopened.screen, OnboardingScreen)
            await pilot.press("escape")
            assert reopened.screen is reopened._home_screen

    asyncio.run(exercise())


def test_skip_is_remembered_without_changing_preferences(tmp_path, monkeypatch):
    monkeypatch.setenv("BREADCRUMBS_HOME", str(tmp_path))
    Settings(ui_theme="sunset", sound_enabled=False, activity_titles=False).save()

    async def exercise():
        app = BreadcrumbsApp(show_onboarding=True)
        async with app.run_test() as pilot:
            await pilot.click("#tour-skip")
            assert app.screen is app._home_screen
            saved = Settings.load()
            assert saved.onboarding_version == TOUR_VERSION
            assert saved.ui_theme == "sunset" and not saved.sound_enabled and not saved.activity_titles

    asyncio.run(exercise())


def test_recovery_takes_priority_and_tour_replay_does_not_change_paused_block(tmp_path, monkeypatch):
    monkeypatch.setenv("BREADCRUMBS_HOME", str(tmp_path))

    async def exercise():
        original = BreadcrumbsApp(session_name="recover-before-tour")
        async with original.run_test():
            original._begin_block()
            sid = original.active_session_id
        app = BreadcrumbsApp(show_onboarding=True)
        async with app.run_test() as pilot:
            assert isinstance(app.screen, RecoveryScreen)
            await pilot.press("escape")
            app._recover("recover-before-tour")
            remaining = app.timer.remaining_seconds
            await pilot.press("question_mark")
            assert isinstance(app.screen, OnboardingScreen)
            await pilot.press("space", "r", "f", "2")
            assert app.timer.status is TimerStatus.PAUSED and app.active_session_id == sid
            assert app.timer.remaining_seconds == remaining
            await pilot.press("escape")
            app.action_toggle()
            await pilot.press("question_mark")
            assert app.screen is app._home_screen
            assert app.timer.status is TimerStatus.RUNNING

    asyncio.run(exercise())
