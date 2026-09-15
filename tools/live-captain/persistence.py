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

-- One durable record per browser submission. request_id is supplied by the
-- browser and makes reconnect/retry idempotent: the same request can only
-- acquire one execution slot and one Admiral message.
CREATE TABLE IF NOT EXISTS executions (
    id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL UNIQUE,
    session_id TEXT NOT NULL,
    source TEXT NOT NULL,
    interaction_mode TEXT NOT NULL,
    input_text TEXT NOT NULL,
    admiral_seq INTEGER,
    captain_seq INTEGER,
    status TEXT NOT NULL CHECK (status IN ('running', 'completed', 'failed')),
    thread_id TEXT,
    started_at REAL NOT NULL,
    completed_at REAL,
    result_text TEXT NOT NULL DEFAULT '',
    error_json TEXT NOT NULL DEFAULT '',
    metadata_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_executions_started ON executions(started_at);
CREATE TABLE IF NOT EXISTS execution_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id TEXT NOT NULL REFERENCES executions(id),
    ordinal INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at REAL NOT NULL,
    UNIQUE(execution_id, ordinal)
);
CREATE INDEX IF NOT EXISTS idx_execution_events_execution
    ON execution_events(execution_id, ordinal);

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
        self._recover_interrupted_executions()
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

    def _recover_interrupted_executions(self) -> None:
        """Turn stale `running` rows into truthful restart failures.

        The inference process cannot survive this store being reconstructed,
        so retaining `running` after service startup would create permanent,
        misleading progress in every browser.
        """
        now = time.time()
        error = {"message": "service restarted before this execution completed"}
        with self._lock:
            rows = self._conn.execute(
                "SELECT id FROM executions WHERE status='running'"
            ).fetchall()
            for (execution_id,) in rows:
                ordinal = self._conn.execute(
                    "SELECT COALESCE(MAX(ordinal), 0) + 1 FROM execution_events WHERE execution_id=?",
                    (execution_id,),
                ).fetchone()[0]
                self._conn.execute(
                    "UPDATE executions SET status='failed',completed_at=?,error_json=? WHERE id=?",
                    (now, json.dumps(error, sort_keys=True), execution_id),
                )
                self._conn.execute(
                    "INSERT INTO execution_events(execution_id,ordinal,event_type,payload_json,created_at) "
                    "VALUES(?,?,?,?,?)",
                    (execution_id, ordinal, "interrupted", json.dumps(error, sort_keys=True), now),
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

    @staticmethod
    def _execution_dict(row) -> dict:
        if row is None:
            return None
        (
            execution_id, request_id, session_id, source, interaction_mode,
            input_text, admiral_seq, captain_seq, status, thread_id,
            started_at, completed_at, result_text, error_json, metadata_json,
        ) = row
        try:
            error = json.loads(error_json) if error_json else None
        except json.JSONDecodeError:
            error = {"message": error_json}
        try:
            metadata = json.loads(metadata_json or "{}")
        except json.JSONDecodeError:
            metadata = {}
        return {
            "id": execution_id, "request_id": request_id, "session_id": session_id,
            "source": source, "interaction_mode": interaction_mode,
            "input_text": input_text, "admiral_seq": admiral_seq,
            "captain_seq": captain_seq, "status": status, "thread_id": thread_id,
            "started_at": started_at, "completed_at": completed_at,
            "result_text": result_text, "error": error, "metadata": metadata,
        }

    def begin_execution(
        self, request_id: str, text: str, source: str, interaction_mode: str,
        kernel_digest: str = "", bearing_digest: str = "", ledger_digest: str = "",
    ) -> tuple[dict, bool]:
        """Atomically reserve a request and persist its Admiral message.

        Returns (execution, created). A repeated request_id returns the
        original execution without recording or running anything again.
        """
        request_id = (request_id or "").strip()
        if not request_id or not text.strip():
            raise PersistenceError("request_id and message are required")
        with self._lock:
            existing = self._conn.execute(
                "SELECT id,request_id,session_id,source,interaction_mode,input_text,"
                "admiral_seq,captain_seq,status,thread_id,started_at,completed_at,"
                "result_text,error_json,metadata_json FROM executions WHERE request_id=?",
                (request_id,),
            ).fetchone()
            if existing is not None:
                execution = self._execution_dict(existing)
                if execution["input_text"] != text.strip():
                    raise PersistenceError("request_id was already used for different message text")
                return execution, False

            seq = self._seq
            self._seq += 1
            execution_id = "execution-" + uuid.uuid4().hex[:16]
            now = time.time()
            self._conn.execute(
                "INSERT INTO messages(session_id,seq,role,text,ts,kernel_digest,bearing_digest,ledger_digest) "
                "VALUES(?,?,?,?,?,?,?,?)",
                (self.session_id, seq, "admiral", text.strip(), now,
                 kernel_digest, bearing_digest, ledger_digest),
            )
            self._conn.execute(
                "INSERT INTO executions(id,request_id,session_id,source,interaction_mode,input_text,"
                "admiral_seq,status,started_at) VALUES(?,?,?,?,?,?,?,?,?)",
                (execution_id, request_id, self.session_id, source, interaction_mode,
                 text.strip(), seq, "running", now),
            )
            self._conn.commit()
            row = self._conn.execute(
                "SELECT id,request_id,session_id,source,interaction_mode,input_text,"
                "admiral_seq,captain_seq,status,thread_id,started_at,completed_at,"
                "result_text,error_json,metadata_json FROM executions WHERE id=?",
                (execution_id,),
            ).fetchone()
        return self._execution_dict(row), True

    def load_executions(self, limit: int = 20) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT id,request_id,session_id,source,interaction_mode,input_text,"
                "admiral_seq,captain_seq,status,thread_id,started_at,completed_at,"
                "result_text,error_json,metadata_json FROM executions ORDER BY started_at DESC LIMIT ?",
                (max(1, min(int(limit), 200)),),
            ).fetchall()
        return [self._execution_dict(row) for row in rows]

    def update_execution(
        self, execution_id: str, *, status: str | None = None,
        captain_seq: int | None = None, thread_id: str | None = None,
        result_text: str | None = None, error: dict | None = None,
        metadata: dict | None = None, completed: bool = False,
    ) -> dict:
        assignments, values = [], []
        if status is not None:
            assignments.append("status=?"); values.append(status)
        if captain_seq is not None:
            assignments.append("captain_seq=?"); values.append(captain_seq)
        if thread_id is not None:
            assignments.append("thread_id=?"); values.append(thread_id)
        if result_text is not None:
            assignments.append("result_text=?"); values.append(result_text)
        if error is not None:
            assignments.append("error_json=?"); values.append(json.dumps(error, sort_keys=True))
        if metadata is not None:
            assignments.append("metadata_json=?"); values.append(json.dumps(metadata, sort_keys=True))
        if completed:
            assignments.append("completed_at=?"); values.append(time.time())
        if not assignments:
            raise PersistenceError("no execution update supplied")
        values.append(execution_id)
        with self._lock:
            self._conn.execute(f"UPDATE executions SET {', '.join(assignments)} WHERE id=?", values)
            self._conn.commit()
            row = self._conn.execute(
                "SELECT id,request_id,session_id,source,interaction_mode,input_text,"
                "admiral_seq,captain_seq,status,thread_id,started_at,completed_at,"
                "result_text,error_json,metadata_json FROM executions WHERE id=?",
                (execution_id,),
            ).fetchone()
        if row is None:
            raise PersistenceError(f"execution does not exist: {execution_id}")
        return self._execution_dict(row)

    def record_execution_event(self, execution_id: str, event_type: str, payload: dict) -> dict:
        with self._lock:
            ordinal = self._conn.execute(
                "SELECT COALESCE(MAX(ordinal), 0) + 1 FROM execution_events WHERE execution_id=?",
                (execution_id,),
            ).fetchone()[0]
            now = time.time()
            self._conn.execute(
                "INSERT INTO execution_events(execution_id,ordinal,event_type,payload_json,created_at) "
                "VALUES(?,?,?,?,?)",
                (execution_id, ordinal, event_type, json.dumps(payload, sort_keys=True, default=str), now),
            )
            self._conn.commit()
        return {"execution_id": execution_id, "ordinal": ordinal,
                "event_type": event_type, "payload": payload, "created_at": now}

    def get_execution(self, execution_id: str) -> dict | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT id,request_id,session_id,source,interaction_mode,input_text,"
                "admiral_seq,captain_seq,status,thread_id,started_at,completed_at,"
                "result_text,error_json,metadata_json FROM executions WHERE id=?",
                (execution_id,),
            ).fetchone()
            if row is None:
                return None
            events = self._conn.execute(
                "SELECT ordinal,event_type,payload_json,created_at FROM execution_events "
                "WHERE execution_id=? ORDER BY ordinal", (execution_id,)
            ).fetchall()
        execution = self._execution_dict(row)
        execution["events"] = [
            {"ordinal": e[0], "event_type": e[1], "payload": json.loads(e[2]), "created_at": e[3]}
            for e in events
        ]
        return execution

    def get_execution_by_request_id(self, request_id: str) -> dict | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT id,request_id,session_id,source,interaction_mode,input_text,"
                "admiral_seq,captain_seq,status,thread_id,started_at,completed_at,"
                "result_text,error_json,metadata_json FROM executions WHERE request_id=?",
                (request_id,),
            ).fetchone()
        return self._execution_dict(row) if row is not None else None

    def load_history(self, limit: int = 200) -> tuple[list[dict], int, list[dict]]:
        """Load durable messages and their execution records for UI restore."""
        limit = max(1, min(int(limit), 1000))
        with self._lock:
            total = self._conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
            rows = self._conn.execute(
                "SELECT seq,role,text,ts FROM messages ORDER BY seq DESC LIMIT ?", (limit,)
            ).fetchall()
            rows.reverse()
            executions = self._conn.execute(
                "SELECT id,request_id,session_id,source,interaction_mode,input_text,"
                "admiral_seq,captain_seq,status,thread_id,started_at,completed_at,"
                "result_text,error_json,metadata_json FROM executions ORDER BY started_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            execution_ids = [row[0] for row in executions]
            event_rows = []
            if execution_ids:
                placeholders = ",".join("?" for _ in execution_ids)
                event_rows = self._conn.execute(
                    f"SELECT execution_id,ordinal,event_type,payload_json,created_at FROM execution_events "
                    f"WHERE execution_id IN ({placeholders}) ORDER BY execution_id,ordinal", execution_ids
                ).fetchall()
        by_seq = {}
        for execution in executions:
            item = self._execution_dict(execution)
            item["events"] = []
            by_seq[item["admiral_seq"]] = item
            if item["captain_seq"]:
                by_seq[item["captain_seq"]] = item
        by_id = {item["id"]: item for item in by_seq.values()}
        for execution_id, ordinal, event_type, payload_json, created_at in event_rows:
            item = by_id.get(execution_id)
            if item is not None:
                item["events"].append({"ordinal": ordinal, "event_type": event_type,
                                       "payload": json.loads(payload_json), "created_at": created_at})
        messages = []
        for seq, role, text, ts in rows:
            messages.append({"seq": seq, "role": role, "text": text, "ts": ts,
                             "execution": by_seq.get(seq)})
        return messages, max(0, total - len(messages)), list(by_id.values())

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
