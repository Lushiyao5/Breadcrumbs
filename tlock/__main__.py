from __future__ import annotations

import argparse
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    from .updater import current_version

    parser = argparse.ArgumentParser(prog="tlock", description="Terminal focus companion")
    parser.add_argument("--version", action="version", version=f"tlock {current_version()}")
    subparsers = parser.add_subparsers(dest="command")
    export = subparsers.add_parser("export", help="Export local activity as JSON")
    export.add_argument("--limit", type=int, default=None)
    export.add_argument("--output", type=Path, default=None)
    update = subparsers.add_parser("update", help="Update Tlock from its latest GitHub release")
    mode = update.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="Check without installing")
    mode.add_argument("--status", action="store_true", help="Show the last background update result")
    update.add_argument("--yes", action="store_true", help="Install without confirmation")
    return parser


def handle_update(*, check: bool, status: bool, assume_yes: bool) -> None:
    from .updater import (
        UpdateError,
        current_version,
        latest_release,
        launch_update,
        read_update_status,
        update_available,
    )

    if status:
        result = read_update_status()
        if result is None:
            print("No background update result is available yet.")
            return
        print(f"Update {result.get('status', 'unknown')}: v{result.get('version', '?')}")
        print(f"Log: {result.get('log', 'unavailable')}")
        return

    installed = current_version()
    try:
        release = latest_release()
    except UpdateError as exc:
        print(f"Update check failed: {exc}")
        return
    print(f"Installed: v{installed}  ·  Latest: {release.tag}")
    if not update_available(release, installed):
        print("Tlock is already up to date.")
        return
    print(f"Release: {release.page_url}")
    if check:
        return
    if not assume_yes:
        answer = input(f"Install Tlock {release.tag}? [Y/n] ").strip().lower()
        if answer not in ("", "y", "yes"):
            print("Update cancelled.")
            return
    log_path, _ = launch_update(release)
    print("Update started in the background. Tlock can now exit safely.")
    print("Wait a moment, then run: tlock update --status")
    print(f"Detailed log: {log_path}")


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "update":
        handle_update(check=args.check, status=args.status, assume_yes=args.yes)
        return
    if args.command == "export":
        from .db import Database

        database = Database()
        try:
            payload = database.export_json(args.limit)
        finally:
            database.close()
        if args.output:
            args.output.write_text(payload + "\n", encoding="utf-8")
            print(f"Exported activity to {args.output}")
        else:
            print(payload)
        return

    from .app import TlockApp

    TlockApp().run()


if __name__ == "__main__":
    main()
