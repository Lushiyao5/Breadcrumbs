import os
import tempfile
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


@pytest.mark.parametrize("failure", ["create-temp", "missing-parent", "directory"])
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

        def fail_mkstemp(*args, **kwargs):
            raise PermissionError("access denied")

        monkeypatch.setattr(tempfile, "mkstemp", fail_mkstemp)

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
    assert list(tmp_path.rglob("*.tmp")) == []
    if failure == "create-temp":
        assert destination.read_text(encoding="utf-8") == "keep this file"
    elif failure == "directory":
        assert destination.is_dir()
        assert list(destination.iterdir()) == []


def test_export_partial_write_failure_preserves_existing_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    home = tmp_path / "home"
    before = prepare_database(home)
    destination = tmp_path / "export.json"
    destination.write_text("keep this file", encoding="utf-8")
    real_fdopen = os.fdopen

    def partially_failing_fdopen(descriptor, *args, **kwargs):
        handle = real_fdopen(descriptor, *args, **kwargs)
        real_write = handle.write

        def fail_midway(data):
            real_write(data[: len(data) // 2])
            raise OSError("No space left on device")

        handle.write = fail_midway
        return handle

    monkeypatch.setattr(os, "fdopen", partially_failing_fdopen)
    monkeypatch.setenv("BREADCRUMBS_HOME", str(home))
    monkeypatch.setattr("sys.argv", ["breadcrumbs", "export", "--output", str(destination)])

    with pytest.raises(SystemExit) as error:
        main()

    captured = capsys.readouterr()
    assert error.value.code == 1
    assert captured.out == ""
    assert str(destination) in captured.err
    assert destination.read_text(encoding="utf-8") == "keep this file"
    assert list(tmp_path.rglob("*.tmp")) == []
    assert read_database(home) == before


def test_export_replacement_failure_preserves_existing_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    home = tmp_path / "home"
    before = prepare_database(home)
    destination = tmp_path / "export.json"
    destination.write_text("keep this file", encoding="utf-8")

    def fail_replace(source, target):
        raise PermissionError("destination locked")

    monkeypatch.setattr(os, "replace", fail_replace)
    monkeypatch.setenv("BREADCRUMBS_HOME", str(home))
    monkeypatch.setattr("sys.argv", ["breadcrumbs", "export", "--output", str(destination)])

    with pytest.raises(SystemExit) as error:
        main()

    captured = capsys.readouterr()
    assert error.value.code == 1
    assert captured.out == ""
    assert str(destination) in captured.err
    assert destination.read_text(encoding="utf-8") == "keep this file"
    assert list(tmp_path.rglob("*.tmp")) == []
    assert read_database(home) == before


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
