#!/usr/bin/env python3
"""Pause and resume the Live Captain.

    python3 tools/live-captain/pause.py status
    python3 tools/live-captain/pause.py on  "holding while I read the ledger"
    python3 tools/live-captain/pause.py off

Deliberately a plain file toggle rather than an API call, so it works when
the services are down, when Caddy is down, and from a phone over SSH. The
services read the same flag; nothing here needs them to be running.

This does **not** stop the services, and that is the point. A paused Captain
still answers `/api/status` and reports that it is paused, with the reason.
A stopped Captain is indistinguishable from a crashed one.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pause_state  # noqa: E402


def show() -> int:
    state = pause_state.read()
    if state["paused"]:
        print("Live Captain: PAUSED")
        print(f"  reason: {state.get('reason')}")
        print(f"  since:  {state.get('since')}")
        print(f"  by:     {state.get('by')}")
        print("\n  Services stay up and keep reporting status.")
        print("  New turns are refused; continuity is intact.")
        print("  Resume: python3 tools/live-captain/pause.py off")
    else:
        print("Live Captain: RUNNING")
        print(f"  flag file: {pause_state.PAUSE_PATH}")
    return 0


def main(argv: list[str]) -> int:
    action = (argv[1] if len(argv) > 1 else "status").lower()

    if action in ("status", "show"):
        return show()

    if action in ("on", "pause"):
        reason = " ".join(argv[2:])
        result = pause_state.pause(reason)
        print("Live Captain: PAUSED")
        print(f"  reason: {result['reason']}")
        print(f"  since:  {result['since']}")
        database = result["database"]
        if database.get("checkpointed"):
            before = database.get("wal_bytes_before", 0)
            after = database.get("wal_bytes_after", 0)
            print(f"  database checkpointed: WAL {before:,} -> {after:,} bytes")
            print("  on-disk database is now complete on its own — safe to copy")
        else:
            print(f"  database not checkpointed: {database.get('reason')}")
            print("  (pause still holds; this is tidying, not the pause itself)")
        print("\n  In-flight turns finish normally. New turns are refused.")
        print("  Resume: python3 tools/live-captain/pause.py off")
        return 0

    if action in ("off", "resume"):
        result = pause_state.resume()
        if result["was_paused"]:
            print("Live Captain: RUNNING")
            print(f"  cleared pause: {result['previous_reason']}")
        else:
            print("Live Captain: RUNNING (was not paused)")
        return 0

    if action == "json":
        print(json.dumps(pause_state.read(), indent=2))
        return 0

    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
