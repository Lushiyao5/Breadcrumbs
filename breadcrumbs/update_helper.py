from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path


def launcher_busy(path: Path) -> bool:
    """Probe delete access without changing a running Windows launcher."""
    if os.name != "nt" or not path.exists():
        return False
    import ctypes
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                  wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.CreateFileW(str(path), 0x10000, 7, None, 3, 0, None)
    if handle == ctypes.c_void_p(-1).value:
        error = ctypes.get_last_error()
        if error in (5, 32, 33):
            return True
        raise ctypes.WinError(error)
    kernel.CloseHandle(handle)
    return False


def wait_for_launchers(timeout: float = 120) -> bool:
    deadline = time.monotonic() + timeout
    scripts = Path(sys.executable).parent
    while any(launcher_busy(scripts / name) for name in ("breadcrumbs.exe", "tlock.exe")):
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.5)
    return True


def main() -> int:
    if len(sys.argv) != 5:
        return 2
    archive_url, log_name, status_name, target_version = sys.argv[1:]
    log_path = Path(log_name)
    status_path = Path(status_name)
    time.sleep(1.5)  # Let the parent breadcrumbs.exe release its Windows file handle.
    command = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "--no-cache-dir",
        "--upgrade",
        archive_url,
    ]
    with log_path.open("w", encoding="utf-8") as log:
        if not wait_for_launchers():
            message = "Close running Breadcrumbs windows and retry the update. No packages were changed."
            log.write(message + "\n")
            status_path.write_text(json.dumps({"status": "failed", "version": target_version,
                "message": message, "log": str(log_path)}, indent=2), encoding="utf-8")
            return 1
        # pip uninstalls before replacing entry points. Keep the importable package
        # available even if a new Windows lock appears after our preflight check.
        import sysconfig
        site = Path(sysconfig.get_path("purelib"))
        with tempfile.TemporaryDirectory(prefix="breadcrumbs-update-backup-") as backup_name:
            backup = Path(backup_name)
            saved = [path for path in site.glob("breadcrumbs*")
                     if path.is_dir() and (path.name == "breadcrumbs" or path.name.endswith(".dist-info"))]
            for path in saved:
                shutil.copytree(path, backup / path.name)
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=False)
            if result.returncode != 0:
                for path in saved:
                    shutil.copytree(backup / path.name, path, dirs_exist_ok=True)
                log.write("\nRestored the previous Breadcrumbs package after the failed update.\n")
        if result.returncode == 0:
            subprocess.run([sys.executable, "-m", "breadcrumbs.browser_install"],
                           stdout=log, stderr=subprocess.STDOUT, check=False)
    payload = {
        "status": "complete" if result.returncode == 0 else "failed",
        "version": target_version,
        "finished_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "log": str(log_path),
    }
    status_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
