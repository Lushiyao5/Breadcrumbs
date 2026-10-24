from __future__ import annotations

import argparse
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    from .updater import current_version

    parser = argparse.ArgumentParser(prog="tlock", description="Terminal focus companion")
    parser.add_argument("--version", action="version", version=f"tlock {current_version()}")
    session = parser.add_mutually_exclusive_group()
    session.add_argument("--resume", "--session", metavar="NAME", help="Recover a saved block by name")
    session.add_argument("--name", metavar="NAME", help="Name a new block")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("sessions", help="List resumable saved blocks")
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
    parser = build_parser()
    args = parser.parse_args()
    if args.command and (args.resume or args.name):
        parser.error("Use --resume or --name when opening the timer, without a subcommand.")
    if args.command == "sessions":
        from .db import Database

        database = Database()
        try:
            rows = database.recoverable()
            if not rows:
                print("No saved blocks.")
            for row in rows:
                seconds = int(row["remaining_seconds"])
                print(f"{row['name']}  {row['timer_kind']}  {seconds // 60}m {seconds % 60}s left")
                print(f"  tlock --resume {row['name']}")
        finally:
            database.close()
        return
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
    from .db import Database
    from .session_names import normalize_name

    for attribute in ("name", "resume"):
        value = getattr(args, attribute)
        if value is not None:
            try:
                setattr(args, attribute, normalize_name(value))
            except ValueError as exc:
                parser.error(str(exc))
    if args.resume or args.name:
        database = Database()
        try:
            if args.resume and not database.recoverable(args.resume):
                parser.error(f"No saved block named '{args.resume}'. Run 'tlock sessions' to list saves.")
            if args.name and database.name_exists(args.name):
                parser.error("That name is already used. Resume it with --resume or choose another name.")
        finally:
            database.close()
    app = TlockApp(resume_name=args.resume, session_name=args.name)
    app.run()
    if app.resume_hint:
        print(f"Saved {app.resume_hint}. Resume with: tlock --resume {app.resume_hint}")


if __name__ == "__main__":
    main()
