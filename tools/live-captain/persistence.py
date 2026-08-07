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
import json
import re
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

CREATE TABLE IF NOT EXISTS concept_rooms (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    source_scope_json TEXT NOT NULL DEFAULT '{"mode":"whole-corpus"}',
    archived INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS concept_turns (
    id TEXT PRIMARY KEY,
    room_id TEXT NOT NULL REFERENCES concept_rooms(id),
    role TEXT NOT NULL CHECK (role IN ('admiral', 'captain')),
    text TEXT NOT NULL,
    state TEXT NOT NULL,
    retrieval_json TEXT NOT NULL DEFAULT '{}',
    spoken_brief TEXT NOT NULL DEFAULT '',
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_concept_turns_room ON concept_turns(room_id, created_at);

CREATE TABLE IF NOT EXISTS concepts (
    id TEXT PRIMARY KEY,
    room_id TEXT NOT NULL REFERENCES concept_rooms(id),
    slug TEXT NOT NULL,
    title TEXT NOT NULL,
    current_revision INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    UNIQUE(room_id, slug)
);

CREATE TABLE IF NOT EXISTS concept_revisions (
    id TEXT PRIMARY KEY,
    concept_id TEXT NOT NULL REFERENCES concepts(id),
    revision INTEGER NOT NULL,
    synopsis TEXT NOT NULL,
    epistemic_state TEXT NOT NULL,
    source_turn_id TEXT NOT NULL REFERENCES concept_turns(id),
    created_at REAL NOT NULL,
    UNIQUE(concept_id, revision)
);

CREATE TABLE IF NOT EXISTS concept_evidence (
    revision_id TEXT NOT NULL REFERENCES concept_revisions(id),
    source_id TEXT NOT NULL,
    path TEXT NOT NULL,
    heading TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    excerpt TEXT NOT NULL,
    PRIMARY KEY(revision_id, source_id)
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

    @staticmethod
    def _row_dict(row, columns: tuple[str, ...]) -> dict:
        return dict(zip(columns, row))

    def create_concept_room(self, title: str = "New Concept Room") -> dict:
        clean = (title or "New Concept Room").strip()[:140]
        room_id = "room-" + uuid.uuid4().hex[:16]
        timestamp = time.time()
        with self._lock:
            self._conn.execute(
                "INSERT INTO concept_rooms(id,title,created_at,updated_at) VALUES(?,?,?,?)",
                (room_id, clean, timestamp, timestamp),
            )
            self._conn.commit()
        return self.get_concept_room(room_id)

    def list_concept_rooms(self, include_archived: bool = False) -> list[dict]:
        where = "" if include_archived else "WHERE archived=0"
        with self._lock:
            rows = self._conn.execute(
                f"SELECT id,title,source_scope_json,archived,created_at,updated_at FROM concept_rooms {where} ORDER BY updated_at DESC"
            ).fetchall()
        return [
            {"id": row[0], "title": row[1], "source_scope": json.loads(row[2]),
             "archived": bool(row[3]), "created_at": row[4], "updated_at": row[5]}
            for row in rows
        ]

    def get_concept_room(self, room_id: str) -> dict:
        with self._lock:
            row = self._conn.execute(
                "SELECT id,title,source_scope_json,archived,created_at,updated_at FROM concept_rooms WHERE id=?",
                (room_id,),
            ).fetchone()
        if row is None:
            raise PersistenceError("concept room does not exist")
        return {"id": row[0], "title": row[1], "source_scope": json.loads(row[2]),
                "archived": bool(row[3]), "created_at": row[4], "updated_at": row[5]}

    def record_concept_turn(self, room_id: str, role: str, text: str, *, state: str = "complete", retrieval: dict | None = None, brief: str = "") -> dict:
        if role not in {"admiral", "captain"} or not text.strip():
            raise PersistenceError("invalid concept turn")
        self.get_concept_room(room_id)
        turn_id = "turn-" + uuid.uuid4().hex[:16]
        timestamp = time.time()
        with self._lock:
            self._conn.execute(
                "INSERT INTO concept_turns(id,room_id,role,text,state,retrieval_json,spoken_brief,created_at) VALUES(?,?,?,?,?,?,?,?)",
                (turn_id, room_id, role, text.strip(), state, json.dumps(retrieval or {}), brief, timestamp),
            )
            self._conn.execute("UPDATE concept_rooms SET updated_at=? WHERE id=?", (timestamp, room_id))
            self._conn.commit()
        return {"id": turn_id, "room_id": room_id, "role": role, "text": text.strip(),
                "state": state, "retrieval": retrieval or {}, "spoken_brief": brief, "created_at": timestamp}

    def load_concept_turns(self, room_id: str, limit: int = 100) -> list[dict]:
        self.get_concept_room(room_id)
        with self._lock:
            rows = self._conn.execute(
                "SELECT id,room_id,role,text,state,retrieval_json,spoken_brief,created_at FROM concept_turns WHERE room_id=? ORDER BY created_at DESC LIMIT ?",
                (room_id, limit),
            ).fetchall()
        rows.reverse()
        return [
            {"id": row[0], "room_id": row[1], "role": row[2], "text": row[3], "state": row[4],
             "retrieval": json.loads(row[5]), "spoken_brief": row[6], "created_at": row[7]}
            for row in rows
        ]

    @staticmethod
    def _concept_slug(title: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:120] or "concept"

    def append_concept_revision(self, room_id: str, title: str, synopsis: str, source_turn_id: str, evidence: list[dict], epistemic_state: str = "inferred") -> dict:
        slug = self._concept_slug(title)
        timestamp = time.time()
        with self._lock:
            row = self._conn.execute(
                "SELECT id,current_revision FROM concepts WHERE room_id=? AND slug=?", (room_id, slug)
            ).fetchone()
            if row:
                concept_id, current = row
            else:
                concept_id, current = "concept-" + uuid.uuid4().hex[:16], 0
                self._conn.execute(
                    "INSERT INTO concepts(id,room_id,slug,title,current_revision,created_at,updated_at) VALUES(?,?,?,?,0,?,?)",
                    (concept_id, room_id, slug, title[:140], timestamp, timestamp),
                )
            revision = current + 1
            revision_id = "revision-" + uuid.uuid4().hex[:16]
            self._conn.execute(
                "INSERT INTO concept_revisions(id,concept_id,revision,synopsis,epistemic_state,source_turn_id,created_at) VALUES(?,?,?,?,?,?,?)",
                (revision_id, concept_id, revision, synopsis[:12000], epistemic_state, source_turn_id, timestamp),
            )
            for item in evidence:
                self._conn.execute(
                    "INSERT INTO concept_evidence(revision_id,source_id,path,heading,content_hash,excerpt) VALUES(?,?,?,?,?,?)",
                    (revision_id, item.get("id", "source"), item.get("path", ""), item.get("heading", ""),
                     item.get("content_hash", ""), item.get("excerpt", "")[:1800]),
                )
            self._conn.execute(
                "UPDATE concepts SET current_revision=?,title=?,updated_at=? WHERE id=?",
                (revision, title[:140], timestamp, concept_id),
            )
            self._conn.commit()
        return self.get_concept(concept_id)

    def list_concepts(self, room_id: str) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT id,title,current_revision,created_at,updated_at FROM concepts WHERE room_id=? ORDER BY updated_at DESC",
                (room_id,),
            ).fetchall()
        return [{"id": row[0], "title": row[1], "current_revision": row[2],
                 "created_at": row[3], "updated_at": row[4]} for row in rows]

    def get_concept(self, concept_id: str) -> dict:
        with self._lock:
            concept = self._conn.execute(
                "SELECT id,room_id,title,current_revision,created_at,updated_at FROM concepts WHERE id=?", (concept_id,)
            ).fetchone()
            if concept is None:
                raise PersistenceError("concept does not exist")
            revisions = self._conn.execute(
                "SELECT id,revision,synopsis,epistemic_state,source_turn_id,created_at FROM concept_revisions WHERE concept_id=? ORDER BY revision",
                (concept_id,),
            ).fetchall()
            revision_items = []
            for revision in revisions:
                evidence = self._conn.execute(
                    "SELECT source_id,path,heading,content_hash,excerpt FROM concept_evidence WHERE revision_id=? ORDER BY source_id",
                    (revision[0],),
                ).fetchall()
                revision_items.append({"id": revision[0], "revision": revision[1], "synopsis": revision[2],
                    "epistemic_state": revision[3], "source_turn_id": revision[4], "created_at": revision[5],
                    "evidence": [{"id": e[0], "path": e[1], "heading": e[2], "content_hash": e[3], "excerpt": e[4]} for e in evidence]})
        return {"id": concept[0], "room_id": concept[1], "title": concept[2],
                "current_revision": concept[3], "created_at": concept[4], "updated_at": concept[5],
                "revisions": revision_items}

    def close(self) -> None:
        with self._lock:
            self._conn.close()
