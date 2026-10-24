from pathlib import Path
import tomllib

from breadcrumbs.config import Settings, data_dir
from breadcrumbs.db import Database
from breadcrumbs.bridge import BridgeState, ControlConflict
from breadcrumbs import __version__, updater
import pytest


def test_existing_tlock_database_and_preferences_are_reused_without_copy(tmp_path, monkeypatch):
    monkeypatch.delenv("BREADCRUMBS_HOME", raising=False)
    monkeypatch.delenv("TLOCK_HOME", raising=False)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    legacy = tmp_path / ".tlock"
    legacy.mkdir()
    monkeypatch.setenv("TLOCK_HOME", str(legacy))
    Settings(focus_minutes=50).save()
    old = Database(legacy / "tlock.db")
    sid = old.begin_session("focus", 3000, "Keep my intentions", "migration-check")
    old.checkpoint(sid, 2700, "paused", "Keep my intentions")
    old.close()
    monkeypatch.delenv("TLOCK_HOME")
    assert data_dir() == legacy
    assert Settings.load().focus_minutes == 50
    new = Database()
    assert new.path == legacy / "tlock.db"
    assert new.recoverable("migration-check")[0]["remaining_seconds"] == 2700
    assert not (tmp_path / ".breadcrumbs").exists()
    new.close()


def test_new_home_and_explicit_home_precedence(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.delenv("BREADCRUMBS_HOME", raising=False)
    monkeypatch.delenv("TLOCK_HOME", raising=False)
    assert data_dir() == tmp_path / ".breadcrumbs"
    monkeypatch.setenv("TLOCK_HOME", str(tmp_path / "legacy-custom"))
    monkeypatch.setenv("BREADCRUMBS_HOME", str(tmp_path / "canonical-custom"))
    assert data_dir() == tmp_path / "canonical-custom"
    monkeypatch.delenv("BREADCRUMBS_HOME")
    assert data_dir() == tmp_path / "legacy-custom"


def test_new_database_defaults_and_release_identity(tmp_path, monkeypatch):
    monkeypatch.setenv("BREADCRUMBS_HOME", str(tmp_path))
    db = Database()
    assert db.path.name == "breadcrumbs.db"
    db.close()
    project = tomllib.loads((Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(encoding="utf-8"))
    assert __version__ == project["project"]["version"]
    monkeypatch.delenv("BREADCRUMBS_REPOSITORY", raising=False)
    monkeypatch.setenv("TLOCK_REPOSITORY", "legacy/repository")
    assert updater.repository() == "legacy/repository"
    monkeypatch.setenv("BREADCRUMBS_REPOSITORY", "canonical/repository")
    assert updater.repository() == "canonical/repository"


def test_stale_command_cannot_replay_after_bridge_restart():
    first, second = BridgeState(), BridgeState()
    snapshot = dict(status="running", session_id=1, name="same-recovered-session", kind="focus",
                    can_control=True, remaining_seconds=600, ui_theme="midnight")
    first.publish_timer(snapshot)
    second.publish_timer(snapshot)
    old = first.status()["timer"]
    assert old["revision"] < 2**53
    with pytest.raises(ControlConflict):
        second.queue_control(dict(action="finish", session_id=1, revision=old["revision"]))
