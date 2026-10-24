from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .config import data_dir


DEFAULT_REPOSITORY = "SaroashDS/Breadcrumbs"


class UpdateError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class Release:
    version: str
    tag: str
    page_url: str
    archive_url: str
    notes: str


def repository() -> str:
    return (os.environ.get("BREADCRUMBS_REPOSITORY") or os.environ.get("TLOCK_REPOSITORY") or DEFAULT_REPOSITORY).strip()


def current_version() -> str:
    try:
        return version("breadcrumbs")
    except PackageNotFoundError:
        from . import __version__

        return __version__


def version_key(value: str) -> tuple[int, ...]:
    clean = value.strip().lower().removeprefix("v").split("-", 1)[0]
    try:
        return tuple(int(part) for part in clean.split("."))
    except ValueError as exc:
        raise UpdateError(f"Unsupported release version: {value}") from exc


def latest_release(repo: str | None = None, *, timeout: float = 8.0) -> Release:
    repo = repo or repository()
    request = Request(
        f"https://api.github.com/repos/{repo}/releases/latest",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"breadcrumbs/{current_version()}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
    except HTTPError as exc:
        if exc.code == 404:
            raise UpdateError(f"No published release was found for {repo}.") from exc
        raise UpdateError(f"GitHub returned HTTP {exc.code}.") from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise UpdateError(f"Could not check GitHub for updates: {exc}") from exc

    tag = str(payload.get("tag_name", ""))
    archive_url = str(payload.get("zipball_url", ""))
    if not tag or not archive_url:
        raise UpdateError("The latest GitHub release is missing required metadata.")
    return Release(
        version=tag.removeprefix("v"),
        tag=tag,
        page_url=str(payload.get("html_url", "")),
        archive_url=archive_url,
        notes=str(payload.get("body") or ""),
    )


def update_available(release: Release, installed: str | None = None) -> bool:
    return version_key(release.version) > version_key(installed or current_version())


def launch_update(release: Release) -> tuple[Path, Path]:
    root = data_dir()
    log_path = root / "update.log"
    status_path = root / "update-status.json"
    command = [
        sys.executable,
        "-m",
        "breadcrumbs.update_helper",
        release.archive_url,
        str(log_path),
        str(status_path),
        release.version,
    ]
    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        creationflags=creationflags,
    )
    return log_path, status_path


def read_update_status() -> dict[str, str] | None:
    path = data_dir() / "update-status.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None
