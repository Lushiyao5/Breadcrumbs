import json

from breadcrumbs.browser_install import sync_legacy_extensions


def test_known_old_extension_folder_is_refreshed_without_touching_user_data(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    current = {"name": "Breadcrumbs Browser Bridge", "version": "0.4.2"}
    (source / "manifest.json").write_text(json.dumps(current), encoding="utf-8")
    (source / "background.mjs").write_text("new worker", encoding="utf-8")
    base = tmp_path / "Local"
    old = base / "Tlock/venv/Lib/site-packages/tlock/assets/browser-extension"
    old.mkdir(parents=True)
    (old / "manifest.json").write_text(json.dumps({**current, "version": "0.2.0"}), encoding="utf-8")
    (old / "background.mjs").write_text("old worker", encoding="utf-8")
    history = base / "history.db"
    history.write_bytes(b"do not alter")
    assert sync_legacy_extensions(base, source) == [old]
    assert (old / "background.mjs").read_text(encoding="utf-8") == "new worker"
    assert json.loads((old / "manifest.json").read_text(encoding="utf-8")) == current
    assert history.read_bytes() == b"do not alter"
    assert sync_legacy_extensions(base, source) == []
    (old / "manifest.json").write_text(json.dumps({**current, "version": "9.0.0"}), encoding="utf-8")
    assert sync_legacy_extensions(base, source) == []  # never downgrade a newer extension


def test_compatibility_refresh_does_not_create_legacy_installs_or_replace_unknown_extensions(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "manifest.json").write_text(json.dumps({"name": "Breadcrumbs", "version": "0.4.2"}), encoding="utf-8")
    base = tmp_path / "Local"
    base.mkdir()
    assert sync_legacy_extensions(base, source) == []
    assert list(base.iterdir()) == []
    other = base / "Tlock/venv/Lib/site-packages/tlock/assets/browser-extension"
    other.mkdir(parents=True)
    metadata = json.dumps({"name": "Unrelated extension", "version": "1.0"})
    (other / "manifest.json").write_text(metadata, encoding="utf-8")
    assert sync_legacy_extensions(base, source) == []
    assert (other / "manifest.json").read_text(encoding="utf-8") == metadata


def test_unknown_diagnostic_changes_are_preserved_with_each_observation(tmp_path):
    from dataclasses import replace
    from breadcrumbs.activity import Context
    from breadcrumbs.db import Database
    db = Database(tmp_path / "diagnostics.db")
    sid = db.begin_session("focus", 60, "")
    span = db.open_span(sid, 1000)
    context = Context("chrome.exe", status="unknown", notice="An old browser extension is still reporting")
    db.record_activity(sid, span, context, "unknown", 1000)
    db.record_activity(sid, span, replace(context, notice="Waiting for a focused web tab"), "unknown", 1001)
    assert [row["notice"] for row in db.activity_for(sid)] == [context.notice, "Waiting for a focused web tab"]
    db.close()
