import csv
import io
from pathlib import Path

import pytest

from breadcrumbs.__main__ import main
from breadcrumbs.db import Database


def prepare_session(home: Path, goal: str, actual: str = "", rating: int | None = None) -> None:
    home.mkdir(exist_ok=True)
    database = Database(home / "breadcrumbs.db")
    session_id = database.begin_session("focus", 60, goal)
    database.finish_session(session_id, 60)
    if actual or rating is not None:
        database.add_reflection(session_id, actual, rating)
    database.close()


def parse_csv(text: str) -> tuple[list[str], list[dict[str, str]]]:
    rows = list(csv.reader(io.StringIO(text)))
    header = rows[0]
    return header, [dict(zip(header, row)) for row in rows[1:]]


EXPECTED_HEADER = [
    "id",
    "session_name",
    "timer_kind",
    "planned_seconds",
    "elapsed_seconds",
    "status",
    "completion_reason",
    "started_at",
    "ended_at",
    "goal",
    "actual",
    "rating",
]


def test_csv_stdout_round_trips_special_values(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    home = tmp_path / "home"
    home.mkdir()
    database = Database(home / "breadcrumbs.db")
    session_id = database.begin_session("focus", 1500, 'Ship, "the" timer\nin two lines')
    database.finish_session(session_id, 1500, "early")
    database.add_reflection(session_id, "总结——多行\n第二行", 4)
    database.close()
    monkeypatch.setenv("BREADCRUMBS_HOME", str(home))
    monkeypatch.setattr("sys.argv", ["breadcrumbs", "export", "--format", "csv"])

    main()

    output = capsys.readouterr().out
    header, rows = parse_csv(output)
    assert header == EXPECTED_HEADER
    assert len(rows) == 1
    assert rows[0]["goal"] == 'Ship, "the" timer\nin two lines'
    assert rows[0]["actual"] == "总结——多行\n第二行"
    assert rows[0]["rating"] == "4"
    assert rows[0]["status"] == "completed"
    assert rows[0]["completion_reason"] == "early"


def test_csv_empty_export_has_header_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    home = tmp_path / "home"
    home.mkdir()
    database = Database(home / "breadcrumbs.db")
    database.close()
    monkeypatch.setenv("BREADCRUMBS_HOME", str(home))
    monkeypatch.setattr("sys.argv", ["breadcrumbs", "export", "--format", "csv"])

    main()

    header, rows = parse_csv(capsys.readouterr().out)
    assert header == EXPECTED_HEADER
    assert rows == []


def test_csv_respects_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    home = tmp_path / "home"
    home.mkdir()
    database = Database(home / "breadcrumbs.db")
    for index in range(3):
        session_id = database.begin_session("focus", 60, f"goal {index}")
        database.finish_session(session_id, 60)
        database.connection.execute(
            "UPDATE sessions SET started_at = ? WHERE id = ?",
            (f"2026-01-0{index + 1}T00:00:00+00:00", session_id),
        )
        database.connection.commit()
    database.close()
    monkeypatch.setenv("BREADCRUMBS_HOME", str(home))
    monkeypatch.setattr("sys.argv", ["breadcrumbs", "export", "--format", "csv", "--limit", "2"])

    main()

    _, rows = parse_csv(capsys.readouterr().out)
    assert len(rows) == 2
    assert [row["goal"] for row in rows] == ["goal 2", "goal 1"]


def test_csv_output_file_matches_stdout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    home = tmp_path / "home"
    prepare_session(home, 'quoted "goal", with comma')
    destination = tmp_path / "sessions.csv"
    monkeypatch.setenv("BREADCRUMBS_HOME", str(home))
    monkeypatch.setattr(
        "sys.argv", ["breadcrumbs", "export", "--format", "csv", "--output", str(destination)]
    )

    main()

    assert capsys.readouterr().out.startswith("Exported session data to")
    file_text = destination.read_text(encoding="utf-8")
    _, rows = parse_csv(file_text)
    assert len(rows) == 1
    assert rows[0]["goal"] == 'quoted "goal", with comma'


def test_csv_rejects_activity_without_flattening(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    home = tmp_path / "home"
    prepare_session(home, "plain goal")
    monkeypatch.setenv("BREADCRUMBS_HOME", str(home))
    monkeypatch.setattr(
        "sys.argv", ["breadcrumbs", "export", "--format", "csv", "--activity"]
    )

    with pytest.raises(SystemExit) as error:
        main()

    assert error.value.code == 2
    captured = capsys.readouterr()
    assert "session summaries only" in captured.err
