from pathlib import Path

import pytest

from breadcrumbs.__main__ import main
from breadcrumbs.db import Database


def prepare_database(home: Path) -> list[dict]:
    home.mkdir()
    database = Database(home / "breadcrumbs.db")
    session_id = database.begin_session("focus", 60, "private-session-content")
    database.finish_session(session_id, 60)
    exported = database.export()
    database.close()
    return exported


def read_database(home: Path) -> list[dict]:
    database = Database(home / "breadcrumbs.db")
    exported = database.export()
    database.close()
    return exported


@pytest.mark.parametrize("failure", ["permission", "missing-parent", "directory"])
def test_export_write_error_is_actionable_and_preserves_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], failure: str
) -> None:
    home = tmp_path / "home"
    before = prepare_database(home)
    destination = tmp_path / "export.json"
    if failure == "missing-parent":
        destination = tmp_path / "missing" / "export.json"
    elif failure == "directory":
        destination.mkdir()
    else:
        destination.write_text("keep this file", encoding="utf-8")
        write_text = Path.write_text

        def fail_destination(path: Path, *args, **kwargs):
            if path == destination:
                raise PermissionError("access denied")
            return write_text(path, *args, **kwargs)

        monkeypatch.setattr(Path, "write_text", fail_destination)

    monkeypatch.setenv("BREADCRUMBS_HOME", str(home))
    monkeypatch.setattr("sys.argv", ["breadcrumbs", "export", "--output", str(destination)])

    with pytest.raises(SystemExit) as error:
        main()

    captured = capsys.readouterr()
    assert error.value.code == 1
    assert captured.out == ""
    assert str(destination) in captured.err
    assert "parent directory exists" in captured.err
    assert "private-session-content" not in captured.err
    assert read_database(home) == before
    if failure == "permission":
        assert destination.read_text(encoding="utf-8") == "keep this file"
    elif failure == "directory":
        assert destination.is_dir()
        assert list(destination.iterdir()) == []


@pytest.mark.parametrize(
    ("extra_args", "expected"),
    [([], "Exported session data"), (["--activity"], "Exported session and activity data")],
)
def test_export_output_names_included_data(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    extra_args: list[str],
    expected: str,
) -> None:
    home = tmp_path / "home"
    prepare_database(home)
    destination = tmp_path / "export.json"
    monkeypatch.setenv("BREADCRUMBS_HOME", str(home))
    monkeypatch.setattr(
        "sys.argv", ["breadcrumbs", "export", *extra_args, "--output", str(destination)]
    )

    main()

    assert capsys.readouterr().out.startswith(expected)
    assert destination.is_file()
