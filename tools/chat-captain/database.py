"""Durable SQLite state for Chat Captain. The ship's own state -- not the
Codex provider -- is the sole continuity layer across restarts (see
docs/doctrine/2026-07-27-continuity-truth-living-captain.md, design
principle 5: continuity belongs to the ship, not the provider session).
"""

from __future__ import annotations

import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any, Optional

MODES = (
    "master",
    "project_formation",
    "design",
    "review",
    "associative_lab",
    "record",
)
DEFAULT_MODE = "master"

HARVEST_TYPES = (
    "vision",
    "principle",
    "project_candidate",
    "decision",
    "design",
    "engineering_handoff",
    "experiment",
    "open_question",
    "safety_rule",
    "communication_rule",
    "next_action",
    "incident_note",
    "captain_brief",
)
HARVEST_STATUSES = ("candidate", "accepted", "rejected", "superseded", "unresolved")

SCHEMA = """
CREATE TABLE IF NOT EXISTS captain_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    captain_id TEXT NOT NULL,
    current_mode TEXT NOT NULL,
    active_project_id TEXT,
    current_session_id TEXT,
    last_session_brief TEXT,
    last_successful_interaction_at TEXT,
    last_successful_harvest_at TEXT,
    provider_name TEXT,
    provider_model TEXT,
    safety_state TEXT NOT NULL DEFAULT 'green',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    purpose TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    active INTEGER NOT NULL DEFAULT 1,
    current_mode TEXT,
    current_summary TEXT,
    next_action TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    mode_at_start TEXT NOT NULL,
    mode_at_end TEXT,
    project_id TEXT,
    brief TEXT,
    status TEXT NOT NULL DEFAULT 'open'
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    mode TEXT,
    project_id TEXT,
    provider TEXT,
    model TEXT,
    image_job_id TEXT
);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, id);

CREATE TABLE IF NOT EXISTS image_jobs (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    prompt TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    artifact_name TEXT,
    artifact_mime TEXT,
    error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_image_jobs_session ON image_jobs(session_id, created_at);

CREATE TABLE IF NOT EXISTS harvest_items (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'candidate',
    project_id TEXT,
    session_id TEXT,
    provenance_note TEXT,
    confidence REAL,
    created_at TEXT NOT NULL,
    reviewed_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_harvest_status ON harvest_items(status, created_at);

CREATE TABLE IF NOT EXISTS mode_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    previous_mode TEXT,
    new_mode TEXT NOT NULL,
    reason TEXT,
    source TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""

DEFAULT_CAPTAIN_ID = "chat-captain.monad"


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:16]}"


def connect(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=FULL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA)
    _migrate(conn)
    _ensure_state_row(conn)
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    # CREATE TABLE IF NOT EXISTS above doesn't add columns to a table that
    # already existed before this column was introduced -- explicit,
    # idempotent ALTER for databases created before image generation.
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(messages)").fetchall()}
    if "image_job_id" not in columns:
        conn.execute("ALTER TABLE messages ADD COLUMN image_job_id TEXT")


def _ensure_state_row(conn: sqlite3.Connection) -> None:
    existing = conn.execute("SELECT id FROM captain_state WHERE id = 1").fetchone()
    if existing is not None:
        return
    timestamp = now()
    conn.execute(
        """INSERT INTO captain_state
           (id, captain_id, current_mode, safety_state, created_at, updated_at)
           VALUES (1, ?, ?, 'green', ?, ?)""",
        (DEFAULT_CAPTAIN_ID, DEFAULT_MODE, timestamp, timestamp),
    )


def row_to_dict(row: Optional[sqlite3.Row]) -> Optional[dict[str, Any]]:
    return dict(row) if row is not None else None


# --- captain_state -----------------------------------------------------

def get_state(conn: sqlite3.Connection) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM captain_state WHERE id = 1").fetchone()
    return row_to_dict(row)


def update_state(conn: sqlite3.Connection, **fields: Any) -> dict[str, Any]:
    if not fields:
        return get_state(conn)
    fields["updated_at"] = now()
    columns = ", ".join(f"{key} = ?" for key in fields)
    conn.execute(f"UPDATE captain_state SET {columns} WHERE id = 1", tuple(fields.values()))
    return get_state(conn)


# --- projects ------------------------------------------------------------

def create_project(
    conn: sqlite3.Connection,
    *,
    title: str,
    purpose: str = "",
    current_mode: str = DEFAULT_MODE,
) -> dict[str, Any]:
    project_id = new_id("proj")
    timestamp = now()
    conn.execute(
        """INSERT INTO projects
           (id, title, purpose, status, active, current_mode, created_at, updated_at)
           VALUES (?, ?, ?, 'active', 1, ?, ?, ?)""",
        (project_id, title, purpose, current_mode, timestamp, timestamp),
    )
    return get_project(conn, project_id)


def get_project(conn: sqlite3.Connection, project_id: str) -> Optional[dict[str, Any]]:
    row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    return row_to_dict(row)


def list_projects(conn: sqlite3.Connection, *, active_only: bool = False) -> list[dict[str, Any]]:
    query = "SELECT * FROM projects"
    if active_only:
        query += " WHERE active = 1"
    query += " ORDER BY updated_at DESC"
    return [dict(row) for row in conn.execute(query).fetchall()]


def update_project(conn: sqlite3.Connection, project_id: str, **fields: Any) -> Optional[dict[str, Any]]:
    if not fields:
        return get_project(conn, project_id)
    fields["updated_at"] = now()
    columns = ", ".join(f"{key} = ?" for key in fields)
    conn.execute(f"UPDATE projects SET {columns} WHERE id = ?", (*fields.values(), project_id))
    return get_project(conn, project_id)


# --- sessions ------------------------------------------------------------

def create_session(conn: sqlite3.Connection, *, mode: str, project_id: Optional[str]) -> dict[str, Any]:
    session_id = new_id("sess")
    timestamp = now()
    conn.execute(
        """INSERT INTO sessions (id, started_at, mode_at_start, project_id, status)
           VALUES (?, ?, ?, ?, 'open')""",
        (session_id, timestamp, mode, project_id),
    )
    return get_session(conn, session_id)


def get_session(conn: sqlite3.Connection, session_id: str) -> Optional[dict[str, Any]]:
    row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    return row_to_dict(row)


def close_session(conn: sqlite3.Connection, session_id: str, *, mode_at_end: str, brief: str) -> dict[str, Any]:
    conn.execute(
        """UPDATE sessions SET ended_at = ?, mode_at_end = ?, brief = ?, status = 'closed'
           WHERE id = ?""",
        (now(), mode_at_end, brief, session_id),
    )
    return get_session(conn, session_id)


# --- messages --------------------------------------------------------------

def append_message(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    role: str,
    content: str,
    mode: Optional[str] = None,
    project_id: Optional[str] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    image_job_id: Optional[str] = None,
) -> dict[str, Any]:
    timestamp = now()
    cursor = conn.execute(
        """INSERT INTO messages
           (session_id, role, content, created_at, mode, project_id, provider, model, image_job_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (session_id, role, content, timestamp, mode, project_id, provider, model, image_job_id),
    )
    row = conn.execute("SELECT * FROM messages WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return dict(row)


def list_messages(conn: sqlite3.Connection, session_id: str, *, limit: int = 200) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM messages WHERE session_id = ? ORDER BY id ASC LIMIT ?",
        (session_id, limit),
    ).fetchall()
    return [dict(row) for row in rows]


# --- harvest_items -----------------------------------------------------------

def create_harvest_item(
    conn: sqlite3.Connection,
    *,
    type: str,
    title: str,
    summary: str,
    project_id: Optional[str],
    session_id: Optional[str],
    provenance_note: Optional[str],
    confidence: Optional[float],
) -> dict[str, Any]:
    item_id = new_id("harv")
    timestamp = now()
    conn.execute(
        """INSERT INTO harvest_items
           (id, type, title, summary, status, project_id, session_id,
            provenance_note, confidence, created_at)
           VALUES (?, ?, ?, ?, 'candidate', ?, ?, ?, ?, ?)""",
        (item_id, type, title, summary, project_id, session_id, provenance_note, confidence, timestamp),
    )
    return get_harvest_item(conn, item_id)


def get_harvest_item(conn: sqlite3.Connection, item_id: str) -> Optional[dict[str, Any]]:
    row = conn.execute("SELECT * FROM harvest_items WHERE id = ?", (item_id,)).fetchone()
    return row_to_dict(row)


def list_harvest_items(conn: sqlite3.Connection, *, status: Optional[str] = None) -> list[dict[str, Any]]:
    if status:
        rows = conn.execute(
            "SELECT * FROM harvest_items WHERE status = ? ORDER BY created_at DESC",
            (status,),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM harvest_items ORDER BY created_at DESC").fetchall()
    return [dict(row) for row in rows]


def set_harvest_status(conn: sqlite3.Connection, item_id: str, status: str) -> Optional[dict[str, Any]]:
    if status not in HARVEST_STATUSES:
        raise ValueError(f"unsupported harvest status {status!r}")
    conn.execute(
        "UPDATE harvest_items SET status = ?, reviewed_at = ? WHERE id = ?",
        (status, now(), item_id),
    )
    return get_harvest_item(conn, item_id)


# --- mode_events -------------------------------------------------------------

def log_mode_event(
    conn: sqlite3.Connection,
    *,
    previous_mode: Optional[str],
    new_mode: str,
    reason: Optional[str],
    source: str,
) -> dict[str, Any]:
    if new_mode not in MODES:
        raise ValueError(f"unsupported mode {new_mode!r}")
    timestamp = now()
    cursor = conn.execute(
        """INSERT INTO mode_events (previous_mode, new_mode, reason, source, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (previous_mode, new_mode, reason, source, timestamp),
    )
    row = conn.execute("SELECT * FROM mode_events WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return dict(row)


# --- image_jobs ----------------------------------------------------------

IMAGE_JOB_STATUSES = ("queued", "running", "succeeded", "failed")


def create_image_job(conn: sqlite3.Connection, *, session_id: str, prompt: str) -> dict[str, Any]:
    job_id = new_id("img")
    timestamp = now()
    conn.execute(
        """INSERT INTO image_jobs (id, session_id, prompt, status, created_at, updated_at)
           VALUES (?, ?, ?, 'queued', ?, ?)""",
        (job_id, session_id, prompt, timestamp, timestamp),
    )
    return get_image_job(conn, job_id)


def get_image_job(conn: sqlite3.Connection, job_id: str) -> Optional[dict[str, Any]]:
    row = conn.execute("SELECT * FROM image_jobs WHERE id = ?", (job_id,)).fetchone()
    return row_to_dict(row)


def update_image_job(conn: sqlite3.Connection, job_id: str, **fields: Any) -> Optional[dict[str, Any]]:
    if not fields:
        return get_image_job(conn, job_id)
    fields["updated_at"] = now()
    columns = ", ".join(f"{key} = ?" for key in fields)
    conn.execute(f"UPDATE image_jobs SET {columns} WHERE id = ?", (*fields.values(), job_id))
    return get_image_job(conn, job_id)
