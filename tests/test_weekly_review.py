from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from breadcrumbs.__main__ import main
from breadcrumbs.db import Database


def add_block(
    database: Database,
    timer_kind: str,
    goal: str,
    started_at: datetime,
    elapsed_seconds: int = 1500,
    status: str = "completed",
    reason: str = "timer",
    name: str | None = None,
    session_root: int | None = None,
) -> int:
    session_id = database.begin_session(
        timer_kind, max(elapsed_seconds, 1), goal, name, session_root=session_root
    )
    if status == "completed":
        database.finish_session(session_id, elapsed_seconds, reason)
    elif status == "abandoned":
        database.abandon_session(session_id, elapsed_seconds)
    start_utc = started_at.astimezone(timezone.utc).isoformat(timespec="seconds")
    end_utc = (started_at + timedelta(seconds=elapsed_seconds)).astimezone(timezone.utc).isoformat(timespec="seconds")
    database.connection.execute(
        "UPDATE sessions SET started_at = ?, ended_at = ? WHERE id = ?",
        (start_utc, end_utc, session_id),
    )
    database.connection.commit()
    return session_id


def test_week_bounds_start_on_local_monday_midnight(tmp_path: Path) -> None:
    database = Database(tmp_path / "week.db")
    start, end = database.week_bounds(date(2026, 10, 21))  # a Wednesday
    database.close()

    assert start.weekday() == 0
    assert start.date() == date(2026, 10, 19)
    assert (start.hour, start.minute, start.second, start.microsecond) == (0, 0, 0, 0)
    assert end.date() == date(2026, 10, 26)
    assert start.utcoffset() == datetime.combine(date(2026, 10, 19), datetime.min.time()).astimezone().utcoffset()


def test_week_bounds_span_seven_local_days_across_dst(tmp_path: Path) -> None:
    """A local week is seven local days, which is not always seven times 24 UTC hours."""
    database = Database(tmp_path / "dst.db")
    # US DST ends 2026-11-01, so the week of 2026-10-26 contains the change.
    start, end = database.week_bounds(date(2026, 10, 28))
    database.close()

    assert start.date() == date(2026, 10, 26)
    assert end.date() == date(2026, 11, 2)
    assert start.weekday() == 0 and end.weekday() == 0
    assert (start.hour, start.minute, start.second) == (0, 0, 0)
    assert (end.hour, end.minute, end.second) == (0, 0, 0)
    # Boundaries are built from local calendar dates, so the span is seven local
    # days even when the UTC length shifts by an hour at a DST transition.
    assert 6 <= (end - start).total_seconds() / 86400 <= 8


def test_weekly_review_excludes_breaks_and_keeps_early_work(tmp_path: Path) -> None:
    database = Database(tmp_path / "review.db")
    monday = datetime(2026, 10, 19, 9, 0, tzinfo=timezone.utc)
    add_block(database, "focus", "deep work", monday, 1500)
    add_block(database, "short_break", "coffee", monday + timedelta(minutes=30), 300)
    add_block(database, "focus", "half done", monday + timedelta(hours=1), 900, reason="early")
    add_block(database, "long_break", "lunch", monday + timedelta(hours=3), 900)
    add_block(database, "custom", "abandoned try", monday + timedelta(hours=5), 120, status="abandoned")

    summary = database.weekly_review(date(2026, 10, 21))
    database.close()

    assert summary["seconds"] == 1500 + 900
    assert summary["blocks"] == 3
    assert summary["completed"] == 2
    assert summary["early_finished"] == 1
    assert summary["abandoned"] == 1


def test_weekly_review_is_empty_for_empty_database(tmp_path: Path) -> None:
    database = Database(tmp_path / "empty.db")
    summary = database.weekly_review(date(2026, 10, 21))
    database.close()

    assert summary["seconds"] == 0
    assert summary["blocks"] == 0
    assert summary["completed"] == 0
    assert summary["sessions"] == []


def test_weekly_review_assigns_midnight_spanning_sessions_to_their_start_week(tmp_path: Path) -> None:
    database = Database(tmp_path / "midnight.db")
    # A block that starts 23:50 local Sunday and runs into Monday belongs to the
    # week that was still open when it started, not to the new week.
    sunday_late = datetime(2026, 10, 18, 23, 50).astimezone()
    monday_early = datetime(2026, 10, 19, 0, 5).astimezone()
    add_block(database, "focus", "late night", sunday_late, 1500)
    add_block(database, "focus", "monday start", monday_early, 1500)

    this_week = database.weekly_review(date(2026, 10, 21))
    last_week = database.weekly_review(date(2026, 10, 14))
    database.close()

    assert this_week["completed"] == 1
    assert this_week["seconds"] == 1500
    assert last_week["completed"] == 1
    assert last_week["seconds"] == 1500


def test_weekly_review_groups_repeated_blocks_in_one_named_session(tmp_path: Path) -> None:
    database = Database(tmp_path / "named.db")
    monday = datetime(2026, 10, 19, 9, 0, tzinfo=timezone.utc)
    root = add_block(database, "focus", "part one", monday, 1500, name="bright-otter")
    add_block(database, "focus", "part two", monday + timedelta(minutes=30), 900, reason="early", session_root=root)
    add_block(database, "focus", "unrelated", monday + timedelta(hours=2), 600, name="quiet-heron")

    summary = database.weekly_review(date(2026, 10, 21))
    database.close()

    names = {session["name"]: session for session in summary["sessions"]}
    assert names["bright-otter"]["blocks"] == 2
    assert names["bright-otter"]["completed"] == 2
    assert names["bright-otter"]["seconds"] == 2400
    assert names["quiet-heron"]["seconds"] == 600


def test_review_command_prints_week_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    home = tmp_path / "home"
    home.mkdir()
    database = Database(home / "breadcrumbs.db")
    add_block(database, "focus", "deep work", datetime(2026, 10, 19, 9, 0, tzinfo=timezone.utc), 1500, name="bright-otter")
    database.close()
    monkeypatch.setenv("BREADCRUMBS_HOME", str(home))
    monkeypatch.setattr("sys.argv", ["breadcrumbs", "review", "--week", "2026-10-21"])

    main()

    output = capsys.readouterr().out
    assert "Week of 2026-10-19" in output
    assert "25m across 1 completed blocks" in output
    assert "bright-otter" in output


def test_review_command_reports_empty_week(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    home = tmp_path / "home"
    home.mkdir()
    Database(home / "breadcrumbs.db").close()
    monkeypatch.setenv("BREADCRUMBS_HOME", str(home))
    monkeypatch.setattr("sys.argv", ["breadcrumbs", "review", "--week", "2026-10-21"])

    main()

    assert "No completed work this week." in capsys.readouterr().out


def test_review_command_rejects_bad_date(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("BREADCRUMBS_HOME", str(tmp_path / "home"))
    monkeypatch.setattr("sys.argv", ["breadcrumbs", "review", "--week", "21-10-2026"])

    with pytest.raises(SystemExit) as error:
        main()

    assert error.value.code == 2
    assert "--week expects a date" in capsys.readouterr().err
