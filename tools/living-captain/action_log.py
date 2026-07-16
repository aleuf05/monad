"""Append-only action record for a Living Captain instance.

V0.1 has no write/command authority (see the scope freeze in
docs/engineering-orders/living-captain-v0.1.md), so the only entry kinds
that exist are things the Captain *noticed*, never things it *did* to
canon. Any real canon mutation still goes through FleetCore's own
authenticated command path, same as every other system in this repo --
this log is deliberately incapable of recording anything else, so it
can't be misread later as a command trail it never was.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Optional

ALLOWED_KINDS = {
    "observation",
    "proposal_note",
    "custody_rejection",
    "spend_exhausted",
}


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def append_action(
    path: str | Path,
    *,
    kind: str,
    summary: str,
    detail: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    if kind not in ALLOWED_KINDS:
        raise ValueError(f"unsupported action kind {kind!r}; must be one of {sorted(ALLOWED_KINDS)}")

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    sequence = len(read_actions(path)) + 1
    entry = {
        "sequence": sequence,
        "recorded_at": _now(),
        "kind": kind,
        "summary": summary,
        "detail": detail or {},
    }
    with open(path, "a") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return entry


def read_actions(path: str | Path) -> list[dict[str, Any]]:
    path = Path(path)
    if not path.exists():
        return []
    entries = []
    with open(path) as handle:
        for line in handle:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries
