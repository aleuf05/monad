#!/usr/bin/env python3
"""Shared pause state for the Live Captain.

**Pause is a state, not an absence.** Stopping the unit would also halt the
Captain, but it destroys the distinction between "deliberately held" and
"crashed" — the status endpoint goes dark and the Admiral cannot tell which
happened. A paused Captain keeps answering status and says, in its own
voice, that it is paused and why.

Four safety properties, each deliberate:

1. **Survives restart.** The flag is a file, not memory. A pause must not
   silently lift because a service bounced — that is the one failure that
   would make pausing untrustworthy.
2. **Settable while the service is down.** It is a plain file, so the
   Captain can be pinned paused *before* being started.
3. **Never loses an in-flight turn.** The gate refuses *new* turns. A turn
   already running completes and is recorded normally.
4. **Leaves clean state on disk.** Pausing checkpoints the SQLite WAL, so a
   paused Captain is a safe point to inspect, copy, or stop.

Both Live Captain services read this one file, so there is a single answer
to "is the Captain paused" rather than two that can disagree.
"""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Overridable so tests never touch the operator's real pause flag. Without
# this the whole suite failed simply because the Captain was legitimately
# paused — the test server booted, read the live flag, and refused its own
# turn. Operator state leaking into tests is a defect in the tests.
_DEFAULT_STATE_DIR = REPO_ROOT / "data" / "live-captain"


def state_dir() -> Path:
    return Path(os.environ.get("MONAD_LIVE_CAPTAIN_STATE_DIR") or _DEFAULT_STATE_DIR)


def pause_path() -> Path:
    return state_dir() / "paused.json"


def db_path() -> Path:
    return state_dir() / "live-captain.db"


# Kept as module attributes for callers that only ever want the real one.
STATE_DIR = _DEFAULT_STATE_DIR
PAUSE_PATH = _DEFAULT_STATE_DIR / "paused.json"
DB_PATH = _DEFAULT_STATE_DIR / "live-captain.db"


def read() -> dict:
    """Current pause state. A missing or unreadable file means running —
    failing *open* is right here: a corrupt flag must not strand the Captain
    in a pause nobody asked for."""
    try:
        data = json.loads(pause_path().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"paused": False}
    if not isinstance(data, dict) or not data.get("paused"):
        return {"paused": False}
    return {
        "paused": True,
        "reason": data.get("reason") or "(no reason given)",
        "since": data.get("since"),
        "by": data.get("by") or "unknown",
    }


def is_paused() -> bool:
    return read()["paused"]


def _write_atomic(payload: dict) -> None:
    """Write via temp file + rename. A half-written flag read by the other
    service is exactly the kind of split-brain this file exists to prevent."""
    target = pause_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    handle, tmp = tempfile.mkstemp(dir=str(target.parent), suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as out:
            json.dump(payload, out, indent=2)
            out.flush()
            os.fsync(out.fileno())
        os.replace(tmp, target)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def checkpoint_database() -> dict:
    """Fold the write-ahead log back into the database.

    A paused Captain should be safe to copy or kill. Left alone this WAL runs
    to several times the size of the database it fronts, so an unclean stop
    replays far more than it needs to. Checkpointing at pause makes the
    on-disk database complete on its own.
    """
    database = db_path()
    if not database.is_file():
        return {"checkpointed": False, "reason": "no database yet"}
    before = database.with_suffix(".db-wal")
    before_size = before.stat().st_size if before.exists() else 0
    try:
        # A short timeout, and never fail the pause over this: holding the
        # Captain is the point; tidying the WAL is a bonus.
        connection = sqlite3.connect(str(database), timeout=5.0)
        try:
            connection.execute("pragma wal_checkpoint(TRUNCATE)")
        finally:
            connection.close()
    except sqlite3.Error as error:
        return {"checkpointed": False, "reason": str(error),
                "wal_bytes_before": before_size}
    after_size = before.stat().st_size if before.exists() else 0
    return {"checkpointed": True, "wal_bytes_before": before_size,
            "wal_bytes_after": after_size}


def pause(reason: str = "", by: str = "admiral") -> dict:
    payload = {
        "paused": True,
        "reason": reason.strip() or "(no reason given)",
        "since": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "by": by,
    }
    _write_atomic(payload)
    return {**payload, "database": checkpoint_database()}


def resume(by: str = "admiral") -> dict:
    previous = read()
    _write_atomic({
        "paused": False,
        "resumed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "by": by,
    })
    return {"paused": False, "was_paused": previous["paused"],
            "previous_reason": previous.get("reason")}


def refusal() -> dict:
    """The body a gated endpoint returns. Says paused, not broken, and says
    exactly how to undo it."""
    state = read()
    return {
        "error": "live captain is paused",
        "paused": True,
        "reason": state.get("reason"),
        "since": state.get("since"),
        "by": state.get("by"),
        "resume_with": "python3 tools/live-captain/pause.py off",
        "note": ("Held deliberately, not failed. Continuity is intact and "
                 "nothing was recorded for this turn."),
    }
