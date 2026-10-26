from pathlib import Path

from breadcrumbs.db import Database


def test_session_lifecycle_and_export(tmp_path: Path) -> None:
    database = Database(tmp_path / "test.db")
    session_id = database.begin_session("focus", 1500, "Ship the timer")
    database.finish_session(session_id, 1500)
    database.add_reflection(session_id, "Built and tested it", 5)

    exported = database.export()
    database.close()

    assert len(exported) == 1
    assert exported[0]["goal"] == "Ship the timer"
    assert exported[0]["actual"] == "Built and tested it"
    assert exported[0]["rating"] == 5
    assert exported[0]["status"] == "completed"


def test_abandoned_session_is_kept(tmp_path: Path) -> None:
    database = Database(tmp_path / "test.db")
    session_id = database.begin_session("custom", 3600, "Deep work")
    database.abandon_session(session_id, 420)

    row = database.recent(1)[0]
    database.close()

    assert row["status"] == "abandoned"
    assert row["elapsed_seconds"] == 420


def test_stats_only_count_completed_sessions(tmp_path: Path) -> None:
    database = Database(tmp_path / "test.db")
    focus = database.begin_session("focus", 60, "Focus")
    database.finish_session(focus, 60)
    custom = database.begin_session("custom", 120, "Custom")
    database.finish_session(custom, 90)
    abandoned = database.begin_session("focus", 60, "Abandoned")
    database.abandon_session(abandoned, 10)

    assert database.stats() == {
        "completed": 2,
        "elapsed_seconds": 150,
        "completed_focuses": 2,
    }
    database.close()


def test_goal_checklist_can_be_updated_while_running(tmp_path: Path) -> None:
    database = Database(tmp_path / "test.db")
    session_id = database.begin_session("focus", 60, "- [ ] Draft")
    database.update_goal(session_id, "- [x] Draft\n- [ ] Review")

    assert database.recent(1)[0]["goal"] == "- [x] Draft\n- [ ] Review"
    database.close()


def test_export_csv_covers_session_summary_columns(tmp_path: Path) -> None:
    import csv
    import io

    database = Database(tmp_path / "test.db")
    session_id = database.begin_session("focus", 1500, "Ship the timer")
    database.finish_session(session_id, 900, "early")
    database.add_reflection(session_id, "停下来总结", 3)

    payload = database.export_csv()
    database.close()

    rows = list(csv.reader(io.StringIO(payload)))
    header = rows[0]
    assert header == list(Database.CSV_SESSION_COLUMNS)
    row = dict(zip(header, rows[1]))
    assert row["goal"] == "Ship the timer"
    assert row["actual"] == "停下来总结"
    assert row["rating"] == "3"
    assert row["status"] == "completed"
    assert row["completion_reason"] == "early"
    assert row["elapsed_seconds"] == "900"


def test_export_csv_empty_database_writes_header_only(tmp_path: Path) -> None:
    import csv
    import io

    database = Database(tmp_path / "test.db")
    payload = database.export_csv()
    database.close()

    rows = list(csv.reader(io.StringIO(payload)))
    assert rows == [list(Database.CSV_SESSION_COLUMNS)]
