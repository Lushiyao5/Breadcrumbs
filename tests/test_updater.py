import io
import json

from breadcrumbs import updater


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
