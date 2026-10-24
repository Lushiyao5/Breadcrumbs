"""Refresh known legacy unpacked-extension folders after a runtime upgrade.

Chrome identifies an unpacked extension by its directory. Keeping that directory
up to date preserves pairing storage; Chrome still requires an extension reload.
No Chrome preferences, browsing data, or cookies are edited.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from importlib.resources import files
from pathlib import Path


def sync_legacy_extensions(local_app_data: Path | None = None, source: Path | None = None) -> list[Path]:
    if local_app_data is None:
        value = os.environ.get("LOCALAPPDATA")
        if not value or os.name != "nt":
            return []
        local_app_data = Path(value)
    base = local_app_data.resolve()
    source = source or Path(str(files("breadcrumbs") / "assets/browser-extension"))
    source = source.resolve()
    current = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    updated = []
    for namespace in ("tlock", "breadcrumbs"):
        destination = base / "Tlock/venv/Lib/site-packages" / namespace / "assets/browser-extension"
        if not (destination / "manifest.json").is_file():
            continue
        destination = destination.resolve()
        if not destination.is_relative_to(base) or destination == source:
            continue
        old = json.loads((destination / "manifest.json").read_text(encoding="utf-8"))
        if not any(word in str(old.get("name", "")).lower() for word in ("tlock", "breadcrumbs")):
            continue
        if tuple(int(part) for part in str(old.get("version", "0")).split(".")) >= tuple(
                int(part) for part in str(current["version"]).split(".")):
            continue
        items = sorted((item for item in source.rglob("*") if item.is_file()),
                       key=lambda item: (item.name == "manifest.json", str(item)))
        # Publish the version last so an interrupted copy retries on the next run.
        for item in items:
            target = destination / item.relative_to(source)
            if not target.resolve().is_relative_to(destination):
                raise OSError("Extension compatibility path leaves its directory")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)
        updated.append(destination)
    return updated


def refresh_installed_compatibility() -> list[Path]:
    """Only real private Windows runtimes self-repair; source/test apps do not."""
    value = os.environ.get("LOCALAPPDATA")
    if os.name != "nt" or not value:
        return []
    base = Path(value).resolve()
    runtime = Path(sys.prefix).resolve()
    if runtime not in (base / "Breadcrumbs/venv", base / "Tlock/venv"):
        return []
    if not Path(__file__).resolve().is_relative_to(runtime / "Lib/site-packages"):
        return []
    return sync_legacy_extensions(base)


def main() -> int:
    try:
        updated = sync_legacy_extensions()
    except (OSError, ValueError):
        print("Could not refresh the old extension folder. Load the folder from 'breadcrumbs browser path' instead.")
        return 1
    if updated:
        print("Updated the existing extension folder. Reload Breadcrumbs in chrome://extensions or edge://extensions.")
    else:
        print("No outdated legacy extension folder found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
