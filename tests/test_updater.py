import io
import json

from breadcrumbs import updater
from breadcrumbs import update_helper


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def test_latest_release_and_version_comparison(monkeypatch) -> None:
    payload = {
        "tag_name": "v0.5.0",
        "html_url": "https://github.com/SaroashDS/Breadcrumbs/releases/tag/v0.5.0",
        "zipball_url": "https://api.github.com/repos/SaroashDS/Breadcrumbs/zipball/v0.5.0",
        "body": "Release notes",
    }
    monkeypatch.setattr(
        updater,
        "urlopen",
        lambda request, timeout: FakeResponse(json.dumps(payload).encode()),
    )

    release = updater.latest_release(timeout=0.1)

    assert release.version == "0.5.0"
    assert updater.update_available(release, "0.1.0") is True
    assert updater.update_available(release, "0.5.0") is False


def test_launch_update_uses_detached_helper(tmp_path, monkeypatch) -> None:
    calls = []
    monkeypatch.setenv("BREADCRUMBS_HOME", str(tmp_path))
    monkeypatch.setattr(updater.subprocess, "Popen", lambda command, **kwargs: calls.append(command))
    release = updater.Release("0.5.0", "v0.5.0", "page", "archive", "")

    log_path, status_path = updater.launch_update(release)

    assert calls[0][1:4] == ["-m", "breadcrumbs.update_helper", "archive"]
    assert log_path.parent == tmp_path
    assert status_path.parent == tmp_path


def test_busy_launcher_does_not_start_pip(tmp_path, monkeypatch):
    log = tmp_path / "update.log"
    status = tmp_path / "status.json"
    monkeypatch.setattr(update_helper.sys, "argv", ["helper", "archive", str(log), str(status), "0.4.3"])
    monkeypatch.setattr(update_helper.time, "sleep", lambda _: None)
    monkeypatch.setattr(update_helper, "wait_for_launchers", lambda: False)
    calls = []
    monkeypatch.setattr(update_helper.subprocess, "run", lambda *a, **k: calls.append(a))
    assert update_helper.main() == 1
    assert calls == []
    assert "No packages were changed" in json.loads(status.read_text())["message"]


def test_failed_install_restores_importable_package(tmp_path, monkeypatch):
    import sysconfig
    from types import SimpleNamespace

    site = tmp_path / "site-packages"
    package = site / "breadcrumbs"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("original")
    metadata = site / "breadcrumbs-0.4.2.dist-info"
    metadata.mkdir()
    (metadata / "METADATA").write_text("Version: 0.4.2")
    monkeypatch.setattr(update_helper.sys, "argv", ["helper", "archive", str(tmp_path / "log"), str(tmp_path / "status"), "0.4.3"])
    monkeypatch.setattr(update_helper.time, "sleep", lambda _: None)
    monkeypatch.setattr(update_helper, "wait_for_launchers", lambda: True)
    monkeypatch.setattr(sysconfig, "get_path", lambda _: str(site))

    def broken_install(*args, **kwargs):
        (package / "__init__.py").unlink()
        (metadata / "METADATA").unlink()
        return SimpleNamespace(returncode=1)

    monkeypatch.setattr(update_helper.subprocess, "run", broken_install)
    assert update_helper.main() == 1
    assert (package / "__init__.py").read_text() == "original"
    assert (metadata / "METADATA").read_text() == "Version: 0.4.2"
