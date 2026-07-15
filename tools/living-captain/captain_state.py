"""Minimum persistent state for a Living Captain instance.

Holds only identity and pointers into other systems' state (FleetCore's
tick/event sequence, World Intake's pending count) -- never a copy of
canon, which stays owned by FleetCore. Written with the same durability
bar as FleetCore's own persistence: a temp-file-plus-rename, fsynced
before the rename, so an unclean kill mid-write can never leave a
half-written state.json behind.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

DEFAULT_CAPTAIN_ID = "captain.monad"
DEFAULT_OBSERVE_LIMIT = 1


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _fresh_identity(captain_id: str) -> dict[str, Any]:
    return {
        "captain_id": captain_id,
        "created_at": now(),
        "restart_count": 0,
        "last_assembled_at": None,
        "last_seen_fleetcore_tick": None,
        "last_seen_fleetcore_event_sequence": None,
        "last_seen_world_intake_pending_count": None,
        "custody_manifest": None,
        "observe_count": 0,
        "observe_limit": DEFAULT_OBSERVE_LIMIT,
    }


def load_state(path: str | Path, *, captain_id: str = DEFAULT_CAPTAIN_ID) -> dict[str, Any]:
    """Load persisted state, or hand back a fresh identity if this Captain
    has never been assembled before. Never raises on a missing file --
    "no state yet" is the expected first-boot condition, not an error."""
    path = Path(path)
    if not path.exists():
        return _fresh_identity(captain_id)
    state = json.loads(path.read_text())
    defaults = _fresh_identity(captain_id)
    for key, value in defaults.items():
        state.setdefault(key, value)
    return state


def save_state(path: str | Path, state: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with open(tmp_path, "w") as handle:
        json.dump(state, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp_path, path)
