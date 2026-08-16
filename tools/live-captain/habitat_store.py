"""Captain Habitat Storage Engine.

Provides persistent thread management, message history, tool event logs,
and Heart operational learning lessons.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional


SCHEMA = """
CREATE TABLE IF NOT EXISTS threads (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    archived INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL REFERENCES threads(id),
    seq INTEGER NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admiral', 'captain', 'system')),
    text TEXT NOT NULL,
    attachments_json TEXT NOT NULL DEFAULT '[]',
    tool_events_json TEXT NOT NULL DEFAULT '[]',
    ts REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_thread ON messages(thread_id, seq);

CREATE TABLE IF NOT EXISTS heart_lessons (
    id TEXT PRIMARY KEY,
    lesson TEXT NOT NULL,
    source TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'correction',
    created_at REAL NOT NULL,
    applied_count INTEGER NOT NULL DEFAULT 0
);
"""


class HabitatStore:
    """Thread-safe SQLite store for Captain Habitat."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self) -> None:
        with self._lock, self._get_connection() as conn:
            conn.executescript(SCHEMA)

    # --- THREAD MANAGEMENT ---

    def create_thread(self, title: Optional[str] = None) -> Dict[str, Any]:
        thread_id = f"thread-{uuid.uuid4().hex[:12]}"
        now = time.time()
        title_str = title.strip() if title and title.strip() else "New Conversation"

        with self._lock, self._get_connection() as conn:
            conn.execute(
                "INSERT INTO threads (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (thread_id, title_str, now, now)
            )

        return {
            "id": thread_id,
            "title": title_str,
            "created_at": now,
            "updated_at": now,
            "message_count": 0
        }

    def list_threads(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock, self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT t.id, t.title, t.created_at, t.updated_at,
                       COUNT(m.id) as message_count,
                       (SELECT text FROM messages WHERE thread_id = t.id ORDER BY seq DESC LIMIT 1) as last_message
                FROM threads t
                LEFT JOIN messages m ON t.id = m.thread_id
                WHERE t.archived = 0
                GROUP BY t.id
                ORDER BY t.updated_at DESC
                LIMIT ?
                """,
                (limit,)
            ).fetchall()

        threads = []
        for r in rows:
            threads.append({
                "id": r["id"],
                "title": r["title"],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
                "message_count": r["message_count"],
                "last_message": r["last_message"] or ""
            })
        return threads

    def get_thread(self, thread_id: str) -> Optional[Dict[str, Any]]:
        with self._lock, self._get_connection() as conn:
            t = conn.execute("SELECT * FROM threads WHERE id = ?", (thread_id,)).fetchone()
            if not t:
                return None

            messages = conn.execute(
                "SELECT * FROM messages WHERE thread_id = ? ORDER BY seq ASC", (thread_id,)
            ).fetchall()

        msg_list = []
        for m in messages:
            msg_list.append({
                "id": m["id"],
                "role": m["role"],
                "text": m["text"],
                "attachments": json.loads(m["attachments_json"]),
                "tool_events": json.loads(m["tool_events_json"]),
                "ts": m["ts"]
            })

        return {
            "id": t["id"],
            "title": t["title"],
            "created_at": t["created_at"],
            "updated_at": t["updated_at"],
            "messages": msg_list
        }

    def update_thread_title(self, thread_id: str, new_title: str) -> bool:
        with self._lock, self._get_connection() as conn:
            res = conn.execute("UPDATE threads SET title = ?, updated_at = ? WHERE id = ?", (new_title, time.time(), thread_id))
            return res.rowcount > 0

    def delete_thread(self, thread_id: str) -> bool:
        with self._lock, self._get_connection() as conn:
            conn.execute("DELETE FROM messages WHERE thread_id = ?", (thread_id,))
            res = conn.execute("DELETE FROM threads WHERE id = ?", (thread_id,))
            return res.rowcount > 0

    # --- MESSAGES ---

    def add_message(
        self,
        thread_id: str,
        role: str,
        text: str,
        attachments: Optional[List[Dict[str, Any]]] = None,
        tool_events: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        msg_id = f"msg-{uuid.uuid4().hex[:12]}"
        now = time.time()
        attachments_json = json.dumps(attachments or [])
        tool_events_json = json.dumps(tool_events or [])

        with self._lock, self._get_connection() as conn:
            # Ensure thread exists
            t = conn.execute("SELECT id, title FROM threads WHERE id = ?", (thread_id,)).fetchone()
            if not t:
                conn.execute("INSERT INTO threads (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                             (thread_id, text[:40] or "New Conversation", now, now))
                thread_title = text[:40] or "New Conversation"
            else:
                thread_title = t["title"]

            # Get next seq
            seq_row = conn.execute("SELECT MAX(seq) as max_seq FROM messages WHERE thread_id = ?", (thread_id,)).fetchone()
            next_seq = (seq_row["max_seq"] or 0) + 1 if seq_row and seq_row["max_seq"] is not None else 1

            conn.execute(
                """
                INSERT INTO messages (id, thread_id, seq, role, text, attachments_json, tool_events_json, ts)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (msg_id, thread_id, next_seq, role, text, attachments_json, tool_events_json, now)
            )

            # Auto-update thread title if it's default
            if thread_title == "New Conversation" and role == "admiral" and text.strip():
                clean_title = text.strip().split("\n")[0][:45]
                conn.execute("UPDATE threads SET title = ?, updated_at = ? WHERE id = ?", (clean_title, now, thread_id))
            else:
                conn.execute("UPDATE threads SET updated_at = ? WHERE id = ?", (now, thread_id))

        return {
            "id": msg_id,
            "thread_id": thread_id,
            "seq": next_seq,
            "role": role,
            "text": text,
            "attachments": attachments or [],
            "tool_events": tool_events or [],
            "ts": now
        }

    # --- HEART LESSONS ---

    def add_heart_lesson(self, lesson: str, source: str, category: str = "correction") -> Dict[str, Any]:
        lesson_id = f"heart-{uuid.uuid4().hex[:8]}"
        now = time.time()
        with self._lock, self._get_connection() as conn:
            conn.execute(
                "INSERT INTO heart_lessons (id, lesson, source, category, created_at) VALUES (?, ?, ?, ?, ?)",
                (lesson_id, lesson.strip(), source.strip(), category, now)
            )
        return {"id": lesson_id, "lesson": lesson, "source": source, "category": category, "created_at": now}

    def get_heart_lessons(self, limit: int = 30) -> List[Dict[str, Any]]:
        with self._lock, self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM heart_lessons ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]
