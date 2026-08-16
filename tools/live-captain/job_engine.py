"""Persistent Agent Job Engine & Multi-Embodiment Worker Routing.

Implements Sections 9 & 10 of Live Captain Commissioning.
Delegates asynchronous tasks to AGY, Claude, Codex, and local tools,
tracks persistent lifecycle in SQLite, captures output, and notifies on completion.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3
import subprocess
import threading
import time
from typing import Any, Dict, List, Optional
import uuid

ROOT_DIR = Path(__file__).resolve().parent
REPO_ROOT = ROOT_DIR.parent.parent
DB_PATH = REPO_ROOT / "data" / "live-captain" / "jobs.db"
AGY_BIN = os.environ.get("AGY_BIN", "/home/cgl/.local/bin/agy")
CLAUDE_BIN = os.environ.get("CLAUDE_BIN", "/home/cgl/.local/bin/claude")
CODEX_BIN = os.environ.get("CODEX_BIN", "/home/cgl/.local/bin/codex")

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    requester TEXT NOT NULL,
    worker TEXT NOT NULL,
    request TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    result TEXT,
    error TEXT,
    conversation_id TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_jobs_state ON jobs(state);
CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at DESC);
"""


class JobStore:
    """Thread-safe SQLite store for background jobs."""

    def __init__(self, db_path: Path = DB_PATH):
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

    def create_job(
        self,
        worker: str,
        request: str,
        requester: str = "admiral",
        conversation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        job_id = f"job-{uuid.uuid4().hex[:8]}"
        now = time.time()
        meta_json = json.dumps(metadata or {})
        with self._lock, self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO jobs (id, requester, worker, request, state, created_at, updated_at, conversation_id, metadata_json)
                VALUES (?, ?, ?, ?, 'pending', ?, ?, ?, ?)
                """,
                (job_id, requester, worker, request, now, now, conversation_id, meta_json),
            )
        return self.get_job(job_id)  # type: ignore

    def update_job(
        self,
        job_id: str,
        state: str,
        result: Optional[str] = None,
        error: Optional[str] = None,
    ) -> bool:
        now = time.time()
        with self._lock, self._get_connection() as conn:
            res = conn.execute(
                """
                UPDATE jobs
                SET state = ?, result = COALESCE(?, result), error = COALESCE(?, error), updated_at = ?
                WHERE id = ?
                """,
                (state, result, error, now, job_id),
            )
            return res.rowcount > 0

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock, self._get_connection() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
            if not row:
                return None
            return {
                "id": row["id"],
                "requester": row["requester"],
                "worker": row["worker"],
                "request": row["request"],
                "state": row["state"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "result": row["result"] or "",
                "error": row["error"] or "",
                "conversation_id": row["conversation_id"],
                "metadata": json.loads(row["metadata_json"] or "{}"),
            }

    def list_jobs(self, limit: int = 30, state: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock, self._get_connection() as conn:
            if state:
                rows = conn.execute(
                    "SELECT * FROM jobs WHERE state = ? ORDER BY created_at DESC LIMIT ?",
                    (state, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)
                ).fetchall()
        jobs = []
        for r in rows:
            jobs.append({
                "id": r["id"],
                "requester": r["requester"],
                "worker": r["worker"],
                "request": r["request"],
                "state": r["state"],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
                "result": r["result"] or "",
                "error": r["error"] or "",
                "conversation_id": r["conversation_id"],
                "metadata": json.loads(r["metadata_json"] or "{}"),
            })
        return jobs


class JobRunner:
    """Dispatches jobs to backend workers (AGY, Claude, Codex, local tools)."""

    def __init__(self, store: Optional[JobStore] = None):
        self.store = store or JobStore()
        self._active_processes: Dict[str, subprocess.Popen] = {}
        self._threads: List[threading.Thread] = []
        self._lock = threading.Lock()

    def submit(
        self,
        worker: str,
        request: str,
        requester: str = "admiral",
        conversation_id: Optional[str] = None,
        on_complete: Optional[Any] = None,
    ) -> Dict[str, Any]:
        job = self.store.create_job(worker, request, requester, conversation_id)
        thread = threading.Thread(
            target=self._run_worker,
            args=(job["id"], worker, request, conversation_id, on_complete),
            daemon=True,
            name=f"job-runner-{job['id']}",
        )
        with self._lock:
            self._threads.append(thread)
        thread.start()
        return job

    def wait_all(self, timeout: float = 3.0) -> None:
        with self._lock:
            threads = list(self._threads)
        for t in threads:
            if t.is_alive():
                t.join(timeout=timeout)

    def cancel(self, job_id: str) -> bool:
        with self._lock:
            proc = self._active_processes.get(job_id)
            if proc:
                try:
                    proc.terminate()
                except Exception:
                    pass
        return self.store.update_job(job_id, state="cancelled", error="Cancelled by operator")

    def _run_worker(
        self,
        job_id: str,
        worker: str,
        request: str,
        conversation_id: Optional[str],
        on_complete: Optional[Any],
    ) -> None:
        self.store.update_job(job_id, state="running")
        cmd: List[str] = []

        if worker == "agy":
            cmd = [AGY_BIN, "-p", request, "--output-format", "text", "--dangerously-skip-permissions"]
        elif worker == "claude":
            cmd = [CLAUDE_BIN, "-p", request, "--permission-mode", "bypassPermissions"]
        elif worker == "codex":
            cmd = [CODEX_BIN, "exec", request]
        elif worker == "sound_ship":
            cmd = ["bash", "scripts/sound-the-ship.sh"]
        else:
            # Fallback direct shell execution for local tools
            cmd = ["bash", "-c", request]

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=REPO_ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            with self._lock:
                self._active_processes[job_id] = proc

            stdout, _ = proc.communicate(timeout=300)
            exit_code = proc.returncode

            with self._lock:
                self._active_processes.pop(job_id, None)

            try:
                curr = self.store.get_job(job_id)
                if curr and curr["state"] == "cancelled":
                    return

                if exit_code == 0:
                    self.store.update_job(job_id, state="completed", result=stdout.strip())
                else:
                    self.store.update_job(
                        job_id,
                        state="failed",
                        result=stdout.strip(),
                        error=f"Process exited with code {exit_code}",
                    )
            except (sqlite3.OperationalError, sqlite3.DatabaseError):
                pass

        except subprocess.TimeoutExpired:
            with self._lock:
                proc = self._active_processes.pop(job_id, None)
                if proc:
                    proc.kill()
            try:
                curr = self.store.get_job(job_id)
                if not (curr and curr["state"] == "cancelled"):
                    self.store.update_job(job_id, state="failed", error="Job timed out after 300s")
            except (sqlite3.OperationalError, sqlite3.DatabaseError):
                pass
        except Exception as e:
            with self._lock:
                self._active_processes.pop(job_id, None)
            try:
                curr = self.store.get_job(job_id)
                if not (curr and curr["state"] == "cancelled"):
                    self.store.update_job(job_id, state="failed", error=str(e))
            except (sqlite3.OperationalError, sqlite3.DatabaseError):
                pass

        if on_complete:
            try:
                final_job = self.store.get_job(job_id)
                if final_job:
                    on_complete(final_job)
            except Exception:
                pass


GLOBAL_JOB_RUNNER = JobRunner()
