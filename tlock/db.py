from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import data_dir


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Database:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or data_dir() / "tlock.db"
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA foreign_keys=ON")
        self._migrate()

    def _migrate(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timer_kind TEXT NOT NULL,
                planned_seconds INTEGER NOT NULL CHECK (planned_seconds > 0),
                elapsed_seconds INTEGER NOT NULL DEFAULT 0,
                goal TEXT NOT NULL DEFAULT '',
                actual TEXT NOT NULL DEFAULT '',
                rating INTEGER CHECK (rating IS NULL OR rating BETWEEN 1 AND 5),
                started_at TEXT NOT NULL,
                ended_at TEXT,
                status TEXT NOT NULL DEFAULT 'running'
                    CHECK (status IN ('running', 'completed', 'abandoned'))
            );
            CREATE INDEX IF NOT EXISTS idx_sessions_started_at
                ON sessions(started_at DESC);
            CREATE TABLE IF NOT EXISTS drafts (
                name TEXT PRIMARY KEY,
                content TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_sessions_status
                ON sessions(status);
            CREATE VIEW IF NOT EXISTS completed_activity AS
                SELECT id, timer_kind, planned_seconds, elapsed_seconds, goal,
                       actual, rating, started_at, ended_at
                FROM sessions WHERE status = 'completed';
            """
        )
        self.connection.commit()

    def begin_session(self, timer_kind: str, planned_seconds: int, goal: str) -> int:
        cursor = self.connection.execute(
            """INSERT INTO sessions
               (timer_kind, planned_seconds, goal, started_at)
               VALUES (?, ?, ?, ?)""",
            (timer_kind, planned_seconds, goal.strip(), utc_now()),
        )
        self.connection.commit()
        return int(cursor.lastrowid)

    def load_draft(self) -> str:
        row = self.connection.execute(
            "SELECT content FROM drafts WHERE name = 'intentions'"
        ).fetchone()
        return row[0] if row else "- [ ] "

    def save_draft(self, content: str) -> None:
        self.connection.execute(
            "INSERT INTO drafts(name, content) VALUES ('intentions', ?) "
            "ON CONFLICT(name) DO UPDATE SET content = excluded.content", (content,)
        )
        self.connection.commit()

    def finish_session(self, session_id: int, elapsed_seconds: int) -> None:
        self.connection.execute(
            """UPDATE sessions SET elapsed_seconds = ?, ended_at = ?, status = 'completed'
               WHERE id = ?""",
            (elapsed_seconds, utc_now(), session_id),
        )
        self.connection.commit()

    def abandon_session(self, session_id: int, elapsed_seconds: int) -> None:
        self.connection.execute(
            """UPDATE sessions SET elapsed_seconds = ?, ended_at = ?, status = 'abandoned'
               WHERE id = ? AND status = 'running'""",
            (elapsed_seconds, utc_now(), session_id),
        )
        self.connection.commit()

    def add_reflection(self, session_id: int, actual: str, rating: int | None) -> None:
        self.connection.execute(
            "UPDATE sessions SET actual = ?, rating = ? WHERE id = ?",
            (actual.strip(), rating, session_id),
        )
        self.connection.commit()

    def update_goal(self, session_id: int, goal: str) -> None:
        self.connection.execute(
            "UPDATE sessions SET goal = ? WHERE id = ? AND status = 'running'",
            (goal.strip(), session_id),
        )
        self.connection.commit()

    def recent(self, limit: int = 8) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT * FROM sessions ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(row) for row in rows]

    def stats(self) -> dict[str, int]:
        row = self.connection.execute(
            """SELECT
                COUNT(*) AS completed,
                COALESCE(SUM(elapsed_seconds), 0) AS elapsed_seconds,
                COALESCE(SUM(CASE WHEN timer_kind IN ('focus', 'custom') THEN 1 ELSE 0 END), 0)
                    AS completed_focuses
               FROM sessions WHERE status = 'completed'"""
        ).fetchone()
        return {key: int(row[key]) for key in row.keys()}

    def export(self, limit: int | None = None) -> list[dict[str, Any]]:
        sql = "SELECT * FROM sessions ORDER BY started_at DESC"
        params: tuple[int, ...] = ()
        if limit is not None:
            sql += " LIMIT ?"
            params = (limit,)
        return [dict(row) for row in self.connection.execute(sql, params).fetchall()]

    def export_json(self, limit: int | None = None) -> str:
        return json.dumps(self.export(limit), indent=2, ensure_ascii=False)

    def close(self) -> None:
        self.connection.close()
