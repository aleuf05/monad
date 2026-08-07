"""Persistent, Admiral-approved bounded objectives for the Live Captain watch."""

from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from pathlib import Path

STATES = {"DRAFT", "AWAITING_ADMIRAL", "APPROVED", "ACTIVE", "CHECKPOINT", "PAUSED", "COMPLETE", "BLOCKED", "REJECTED"}


class ObjectiveError(ValueError):
    pass


class ObjectiveStore:
    def __init__(self, path: Path):
        self._lock = threading.RLock()
        self._db = sqlite3.connect(str(path), check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        with self._lock:
            self._db.executescript("""
                CREATE TABLE IF NOT EXISTS captain_objectives (
                    id TEXT PRIMARY KEY, objective TEXT NOT NULL, scope TEXT NOT NULL,
                    success_criteria TEXT NOT NULL, state TEXT NOT NULL,
                    move_budget INTEGER NOT NULL, moves_used INTEGER NOT NULL DEFAULT 0,
                    approved_at REAL, created_at REAL NOT NULL, updated_at REAL NOT NULL,
                    last_result TEXT NOT NULL DEFAULT '', error TEXT NOT NULL DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS captain_objective_moves (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, objective_id TEXT NOT NULL,
                    move_number INTEGER NOT NULL, started_at REAL NOT NULL,
                    completed_at REAL, result TEXT NOT NULL DEFAULT '', status TEXT NOT NULL,
                    FOREIGN KEY(objective_id) REFERENCES captain_objectives(id)
                );
            """)
            self._db.commit()

    def propose(self, objective: str, scope: str, success_criteria: list[str], move_budget: int = 3) -> dict:
        if not objective.strip() or not scope.strip() or not success_criteria:
            raise ObjectiveError("objective, scope, and success criteria are required")
        if not 1 <= move_budget <= 12:
            raise ObjectiveError("move budget must be between 1 and 12")
        now = time.time()
        oid = uuid.uuid4().hex[:12]
        with self._lock:
            active = self._db.execute("SELECT id FROM captain_objectives WHERE state IN ('APPROVED','ACTIVE')").fetchone()
            if active:
                raise ObjectiveError("another Captain objective is already active")
            self._db.execute(
                "INSERT INTO captain_objectives VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (oid, objective.strip(), scope.strip(), json.dumps(success_criteria), "AWAITING_ADMIRAL", move_budget, 0, None, now, now, "", ""),
            )
            self._db.commit()
        return self.get(oid)

    def latest(self) -> dict | None:
        with self._lock:
            row = self._db.execute("SELECT * FROM captain_objectives ORDER BY created_at DESC LIMIT 1").fetchone()
        return self._as_dict(row) if row else None

    def get(self, oid: str) -> dict:
        with self._lock:
            row = self._db.execute("SELECT * FROM captain_objectives WHERE id=?", (oid,)).fetchone()
        if not row:
            raise ObjectiveError("unknown Captain objective")
        return self._as_dict(row)

    def transition(self, oid: str, action: str) -> dict:
        transitions = {
            "approve": ({"AWAITING_ADMIRAL", "CHECKPOINT"}, "APPROVED"),
            "pause": ({"APPROVED", "ACTIVE"}, "PAUSED"),
            "resume": ({"PAUSED"}, "APPROVED"),
            "reject": ({"AWAITING_ADMIRAL", "CHECKPOINT", "PAUSED"}, "REJECTED"),
        }
        if action not in transitions:
            raise ObjectiveError("unknown objective action")
        allowed, target = transitions[action]
        with self._lock:
            row = self._db.execute("SELECT state FROM captain_objectives WHERE id=?", (oid,)).fetchone()
            if not row:
                raise ObjectiveError("unknown Captain objective")
            if row["state"] not in allowed:
                raise ObjectiveError(f"cannot {action} objective from {row['state']}")
            now = time.time()
            approved = now if action == "approve" else None
            budget_sql = ", move_budget=move_budget+3" if action == "approve" and row["state"] == "CHECKPOINT" else ""
            self._db.execute(
                f"UPDATE captain_objectives SET state=?, approved_at=COALESCE(?,approved_at), updated_at=?, error='' {budget_sql} WHERE id=?",
                (target, approved, now, oid),
            )
            self._db.commit()
        return self.get(oid)

    def claim_move(self) -> tuple[dict, int] | None:
        """Atomically claim one approved move; concurrent workers cannot double-run it."""
        with self._lock:
            self._db.execute("BEGIN IMMEDIATE")
            row = self._db.execute(
                "SELECT * FROM captain_objectives WHERE state='APPROVED' ORDER BY approved_at LIMIT 1"
            ).fetchone()
            if not row:
                self._db.commit()
                return None
            move = row["moves_used"] + 1
            self._db.execute("UPDATE captain_objectives SET state='ACTIVE', updated_at=? WHERE id=?", (time.time(), row["id"]))
            self._db.execute(
                "INSERT INTO captain_objective_moves(objective_id,move_number,started_at,status) VALUES (?,?,?,'ACTIVE')",
                (row["id"], move, time.time()),
            )
            self._db.commit()
        return self.get(row["id"]), move

    def finish_move(self, oid: str, move: int, result: str) -> dict:
        with self._lock:
            row = self._db.execute("SELECT move_budget,state FROM captain_objectives WHERE id=?", (oid,)).fetchone()
            if not row or row["state"] not in {"ACTIVE", "PAUSED"}:
                raise ObjectiveError("objective has no active move")
            target = "PAUSED" if row["state"] == "PAUSED" else ("CHECKPOINT" if move >= row["move_budget"] else "APPROVED")
            now = time.time()
            self._db.execute(
                "UPDATE captain_objective_moves SET completed_at=?,result=?,status='COMPLETE' WHERE objective_id=? AND move_number=?",
                (now, result, oid, move),
            )
            self._db.execute(
                "UPDATE captain_objectives SET state=?,moves_used=?,last_result=?,updated_at=? WHERE id=?",
                (target, move, result, now, oid),
            )
            self._db.commit()
        return self.get(oid)

    def fail_move(self, oid: str, move: int, error: str) -> dict:
        with self._lock:
            now = time.time()
            self._db.execute("UPDATE captain_objective_moves SET completed_at=?,result=?,status='FAILED' WHERE objective_id=? AND move_number=?", (now, error, oid, move))
            self._db.execute("UPDATE captain_objectives SET state='BLOCKED',error=?,updated_at=? WHERE id=?", (error, now, oid))
            self._db.commit()
        return self.get(oid)

    def _as_dict(self, row: sqlite3.Row) -> dict:
        value = dict(row)
        value["success_criteria"] = json.loads(value["success_criteria"])
        return value

    def close(self) -> None:
        with self._lock:
            self._db.close()


class WatchController:
    def __init__(self, store: ObjectiveStore, execute):
        self.store, self.execute = store, execute
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True, name="captain-watch")

    def start(self):
        self._thread.start()

    def wake(self):
        self._wake.set()

    def close(self):
        self._stop.set(); self._wake.set(); self._thread.join(timeout=5)

    def _run(self):
        while not self._stop.is_set():
            self._wake.wait(1); self._wake.clear()
            while not self._stop.is_set():
                claimed = self.store.claim_move()
                if not claimed:
                    break
                objective, move = claimed
                try:
                    result = self.execute(objective, move)
                    self.store.finish_move(objective["id"], move, result)
                except Exception as exc:
                    self.store.fail_move(objective["id"], move, str(exc))
                    break
