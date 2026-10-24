from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


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
        "--force-reinstall",
        archive_url,
    ]
    with log_path.open("w", encoding="utf-8") as log:
        result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=False)
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
