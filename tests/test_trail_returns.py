import asyncio

from textual.widgets import OptionList, Select, Static

from breadcrumbs.activity import Context, activity_label, classify
from breadcrumbs.app import BreadcrumbsApp
from breadcrumbs.branches import trail_prompts
from breadcrumbs.db import Database


def test_empty_block_clears_previous_visit_details(tmp_path, monkeypatch):
    monkeypatch.setenv("BREADCRUMBS_HOME", str(tmp_path))

    async def exercise():
        app = BreadcrumbsApp()
        async with app.run_test(size=(120, 42)) as pilot:
            sid = app.database.begin_session("focus", 60, "Recorded")
            span = app.database.open_span(sid, 1000)
            app.database.record_activity(sid, span, Context("Code.exe", title="Old visit"), "planned", 1000)
            empty = app.database.begin_session("focus", 60, "Empty")
            app.action_branches()
            await pilot.pause()
            screen = app.screen
            screen.query_one("#branch-session", Select).value = str(sid)
            await pilot.pause()
            assert "Old visit" in str(screen.query_one("#branch-info", Static).renderable)
            screen.query_one("#branch-session", Select).value = str(empty)
            await pilot.pause()
            assert screen.query_one("#trail", OptionList).option_count == 0
            assert "Old visit" not in str(screen.query_one("#branch-info", Static).renderable)
            assert str(screen.query_one("#branch-logo", Static).renderable) == ""

    asyncio.run(exercise())


def test_historical_visit_explanation_uses_its_span_scope(tmp_path, monkeypatch):
    monkeypatch.setenv("BREADCRUMBS_HOME", str(tmp_path))

    async def exercise():
        app = BreadcrumbsApp()
        async with app.run_test(size=(120, 42)) as pilot:
            sid = app.database.begin_session("focus", 60, "Scope changes")
            span = app.database.open_span(sid, 1000)
            app.database.save_scope(sid, {"domains": ["python.org"]})
            app.database.record_activity(sid, span, Context("chrome.exe", status="unknown"), "unknown", 1000)
            app.database.close_spans(sid, 1001)
            app.database.open_span(sid, 1002)
            app.database.save_scope(sid, {"apps": ["chrome"]})
            app.action_branches()
            await pilot.pause()
            app.screen.query_one("#trail", OptionList).highlighted = 0
            await pilot.pause()
            assert "selected page could not be verified" in str(app.screen.query_one("#branch-info", Static).renderable)

    asyncio.run(exercise())


def test_scope_return_rejoins_main_lane_after_deviation(tmp_path):
    db = Database(tmp_path / "return.db")
    sid = db.begin_session("focus", 60, "Build")
    span = db.open_span(sid, 1000)
    visits = [Context("Code.exe"), Context("chrome.exe", domain="youtube.com"), Context("Code.exe")]
    for offset, context in enumerate(visits):
        db.record_activity(sid, span, context, classify(context, ["code"], []), 1000 + offset)
    rows = db.activity_for(sid)
    assert [row["classification"] for row in rows] == ["planned", "unclassified", "planned"]
    prompts = [text.plain for text in trail_prompts(rows)]
    assert prompts[0].startswith("●   ") and "[In scope]" in prompts[0]
    assert prompts[1].startswith("│╲\n│ ● ") and "[Deviation]" in prompts[1]
    assert prompts[2].startswith("│╱  Back in scope\n●   ") and "[In scope]" in prompts[2]
    assert "unclassified" not in "".join(prompts)
    db.close()


def test_deviation_label_is_used_in_details_and_annotation_keys(tmp_path, monkeypatch):
    monkeypatch.setenv("BREADCRUMBS_HOME", str(tmp_path))
    async def exercise():
        app = BreadcrumbsApp()
        sid = app.database.begin_session("focus", 60, "Test fixture")
        span = app.database.open_span(sid, 1000)
        app.database.record_activity(sid, span, Context("Spotify.exe"), "unclassified", 1000)
        async with app.run_test(size=(120, 42)) as pilot:
            app.action_branches()
            await pilot.pause()
            screen = app.screen
            screen.query_one("#trail", OptionList).highlighted = 0
            await pilot.pause()
            assert "Deviation" in str(screen.query_one("#branch-info", Static).renderable)
            await pilot.press("a")
            assert "In scope" in str(screen.query_one("#branch-info", Static).renderable)
            await pilot.press("v")
            assert "Deviation" in str(screen.query_one("#branch-info", Static).renderable)
            assert "unclassified" not in str(screen.query_one("#branch-info", Static).renderable)
            await pilot.press("a", "u")
            assert "Deviation" in str(screen.query_one("#branch-info", Static).renderable)
    asyncio.run(exercise())


def test_friendly_labels_preserve_durable_classification_codes():
    assert activity_label("unclassified") == "Deviation"
    assert activity_label("planned") == "In scope"
    assert classify(Context("Spotify.exe"), ["code"], []) == "unclassified"
