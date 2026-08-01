"""Minimal SQLite persistence for the Live Captain bootstrap.

Packet section 7: chronological Admiral/Captain messages, timestamps,
session id, sequence number, kernel/bearing digest used, and service
restart markers. No modes, no per-message classification. Recent-history
selection is a plain chronological slice across the whole conversation,
not filtered by mode, project, or task type.
"""

from __future__ import annotations

import sqlite3
import time
import uuid
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    seq INTEGER NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admiral', 'captain')),
    text TEXT NOT NULL,
    ts REAL NOT NULL,
    kernel_digest TEXT NOT NULL,
    bearing_digest TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS restarts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    ts REAL NOT NULL
);
"""


class PersistenceError(RuntimeError):
    pass


class LiveCaptainStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.executescript(SCHEMA)
            self._conn.commit()
        except sqlite3.DatabaseError as exc:
            raise PersistenceError(f"live-captain persistence unavailable: {exc}") from exc
        self.session_id = uuid.uuid4().hex
        self._seq = self._next_seq()
        self._record_restart()

    def _next_seq(self) -> int:
        row = self._conn.execute("SELECT MAX(seq) FROM messages").fetchone()
        return (row[0] or 0) + 1

    def _record_restart(self) -> None:
        self._conn.execute(
            "INSERT INTO restarts (session_id, ts) VALUES (?, ?)",
            (self.session_id, time.time()),
        )
        self._conn.commit()

    def record_message(self, role: str, text: str, kernel_digest: str, bearing_digest: str) -> int:
        if role not in ("admiral", "captain"):
            raise PersistenceError(f"invalid message role: {role!r}")
        if not text or not text.strip():
            raise PersistenceError("cannot record an empty message")
        seq = self._seq
        self._seq += 1
        try:
            self._conn.execute(
                "INSERT INTO messages (session_id, seq, role, text, ts, kernel_digest, bearing_digest) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (self.session_id, seq, role, text, time.time(), kernel_digest, bearing_digest),
            )
            self._conn.commit()
        except sqlite3.DatabaseError as exc:
            raise PersistenceError(f"failed to record message: {exc}") from exc
        return seq

    def load_recent_messages(self, limit: int = 30) -> tuple[list[dict], int]:
        """Return (messages, omitted_count). messages is chronological
        (oldest of the window first); omitted_count is how many older
        messages exist beyond the window, for truthful reporting."""
        if limit < 0:
            raise PersistenceError("recent-message limit cannot be negative")
        total = self._conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        rows = self._conn.execute(
            "SELECT seq, role, text, ts FROM messages ORDER BY seq DESC LIMIT ?",
            (limit,),
        ).fetchall()
        rows.reverse()
        messages = [
            {"seq": seq, "role": role, "text": text, "ts": ts} for seq, role, text, ts in rows
        ]
        omitted = max(0, total - len(messages))
        return messages, omitted

    def restart_count(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM restarts").fetchone()[0]

    def close(self) -> None:
        self._conn.close()
