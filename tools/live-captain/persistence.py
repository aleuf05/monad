"""Minimal SQLite persistence for the Live Captain bootstrap.

Packet section 7: chronological Admiral/Captain messages, timestamps,
session id, sequence number, kernel/bearing digest used, and service
restart markers. No modes, no per-message classification. Recent-history
selection is a plain chronological slice across the whole conversation,
not filtered by mode, project, or task type.
"""

from __future__ import annotations

import sqlite3
import threading
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
    bearing_digest TEXT NOT NULL,
    ledger_digest TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS restarts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    ts REAL NOT NULL
);
"""


class PersistenceError(RuntimeError):
    pass


def load_admiral_attestation_read_only(
    db_path: Path, seq: int
) -> tuple[str, bytes]:
    """Load Admiral evidence without migrations, restart records, or writes."""
    uri = f"file:{db_path.resolve().as_posix()}?mode=ro"
    try:
        connection = sqlite3.connect(uri, uri=True)
        try:
            row = connection.execute(
                "SELECT role, text FROM messages WHERE seq = ?", (seq,)
            ).fetchone()
        finally:
            connection.close()
    except sqlite3.DatabaseError as exc:
        raise PersistenceError(f"live-captain persistence unavailable: {exc}") from exc
    if row is None:
        raise PersistenceError(f"message sequence {seq} does not exist")
    role, message_text = row
    if role != "admiral":
        raise PersistenceError("only persisted Admiral messages can attest candidates")
    return f"message:admiral:{seq}", message_text.encode("utf-8")


class LiveCaptainStore:
    def __init__(self, db_path: Path):
        # ThreadingHTTPServer hands each request its own thread, and every
        # request handler shares this one connection (check_same_thread is
        # deliberately False so that's even possible) -- without this lock,
        # two threads calling execute()/fetchone()/commit() on the same
        # sqlite3.Connection at once corrupts its internal statement state
        # and raises sqlite3.InterfaceError: bad parameter or other API
        # misuse. Confirmed live in production 2026-08-02 (a real POST
        # /api/turn crashed mid-record_message while a concurrent
        # /api/status poll was also hitting the connection). Every method
        # below that touches self._conn must hold this lock for its full
        # duration, not just around the final commit.
        self._lock = threading.Lock()
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
            with self._lock:
                self._conn.execute("PRAGMA journal_mode=WAL")
                self._conn.executescript(SCHEMA)
                self._migrate_schema()
                self._conn.commit()
        except sqlite3.DatabaseError as exc:
            raise PersistenceError(f"live-captain persistence unavailable: {exc}") from exc
        self.session_id = uuid.uuid4().hex
        self._seq = self._next_seq()
        self._record_restart()

    def _migrate_schema(self) -> None:
        """Add provenance fields introduced after the bootstrap database.

        Existing rows retain an empty ledger digest, which truthfully means
        that no ledger version was recorded for those historical turns.

        Caller must hold self._lock.
        """
        columns = {
            row[1] for row in self._conn.execute("PRAGMA table_info(messages)").fetchall()
        }
        if "ledger_digest" not in columns:
            self._conn.execute(
                "ALTER TABLE messages ADD COLUMN ledger_digest TEXT NOT NULL DEFAULT ''"
            )

    def _next_seq(self) -> int:
        with self._lock:
            row = self._conn.execute("SELECT MAX(seq) FROM messages").fetchone()
        return (row[0] or 0) + 1

    def _record_restart(self) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO restarts (session_id, ts) VALUES (?, ?)",
                (self.session_id, time.time()),
            )
            self._conn.commit()

    def record_message(
        self,
        role: str,
        text: str,
        kernel_digest: str,
        bearing_digest: str,
        ledger_digest: str,
    ) -> int:
        if role not in ("admiral", "captain"):
            raise PersistenceError(f"invalid message role: {role!r}")
        if not text or not text.strip():
            raise PersistenceError("cannot record an empty message")
        try:
            with self._lock:
                seq = self._seq
                self._seq += 1
                self._conn.execute(
                    "INSERT INTO messages "
                    "(session_id, seq, role, text, ts, kernel_digest, bearing_digest, ledger_digest) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        self.session_id,
                        seq,
                        role,
                        text,
                        time.time(),
                        kernel_digest,
                        bearing_digest,
                        ledger_digest,
                    ),
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
        with self._lock:
            total = self._conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
            rows = self._conn.execute(
                "SELECT seq, role, text, ts, kernel_digest, bearing_digest, ledger_digest "
                "FROM messages ORDER BY seq DESC LIMIT ?",
                (limit,),
            ).fetchall()
        rows.reverse()
        messages = [
            {
                "seq": seq,
                "role": role,
                "text": text,
                "ts": ts,
                "kernel_digest": kernel_digest,
                "bearing_digest": bearing_digest,
                "ledger_digest": ledger_digest,
            }
            for seq, role, text, ts, kernel_digest, bearing_digest, ledger_digest in rows
        ]
        omitted = max(0, total - len(messages))
        return messages, omitted

    def load_admiral_attestation(self, seq: int) -> tuple[str, bytes]:
        """Return immutable evidence bytes for one persisted Admiral command.

        The reference is derived from stored role and sequence metadata rather
        than accepted from a candidate envelope. Captain-authored rows and
        missing sequences fail closed.
        """
        with self._lock:
            row = self._conn.execute(
                "SELECT role, text FROM messages WHERE seq = ?", (seq,)
            ).fetchone()
        if row is None:
            raise PersistenceError(f"message sequence {seq} does not exist")
        role, message_text = row
        if role != "admiral":
            raise PersistenceError("only persisted Admiral messages can attest candidates")
        return f"message:admiral:{seq}", message_text.encode("utf-8")

    def restart_count(self) -> int:
        with self._lock:
            return self._conn.execute("SELECT COUNT(*) FROM restarts").fetchone()[0]

    def close(self) -> None:
        with self._lock:
            self._conn.close()
