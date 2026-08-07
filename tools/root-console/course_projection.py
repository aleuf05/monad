"""Captain-readable projection over existing Monad operational sources.

This module owns no state. It reads authoritative projections and receives
the already-established handoff and Ship's Log results from the Root Console.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def _json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def build(repo_root: Path, handoffs: list[dict], log_entries: list[dict], speech: dict) -> dict:
    fleet = _json(repo_root / "web/data/fleetnet.json")
    officer = _json(repo_root / "web/data/watch-officer-status.json")
    operations = fleet.get("operations") or {}
    alerts = operations.get("alerts") or []
    world = officer.get("world_intake") or {}
    speech_outcome = speech.get("outcome", "pending")

    if alerts:
        captain_action = alerts[0].get("action") or "Inspect the highest-severity operator alert."
    elif world.get("pending_count", 0):
        captain_action = (
            f"Advance Living Captain Intake over the existing World Intake backlog "
            f"({world['pending_count']} pending); preserve its authoritative source."
        )
    else:
        captain_action = "Advance the next Living Captain Master Page integration slice."

    human_gate = (
        "Full spoken round trip awaits Admiral acceptance."
        if speech_outcome == "pending"
        else "Speech loop passed human acceptance."
        if speech_outcome == "passed"
        else f"Speech-loop fault recorded: {speech.get('note') or 'inspect the bridge record'}."
    )
    latest_handoff = handoffs[0] if handoffs else None
    latest_log = log_entries[0] if log_entries else None
    return {
        "schema": "monad.captainCourse.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mission": "Make Living Captain the central operational UX of Monad.",
        "standing_loop": "watch → verify → repair → refine → preserve → report → watch",
        "captain_action": captain_action,
        "human_gate": human_gate,
        "watch": {
            "status": operations.get("status", "unknown"),
            "alert_count": len(alerts),
            "next_action": operations.get("next_action", "Refresh Fleetnet operator watch."),
            "generated": fleet.get("generated"),
            "resources": operations.get("resources") or {},
        },
        "speech": speech,
        "engineering": fleet.get("tree") or {},
        "backlog": {
            "world_intake_pending": world.get("pending_count"),
            "oldest_pending_hours": world.get("oldest_pending_age_hours"),
        },
        "continuity": {
            "latest_handoff": latest_handoff,
            "latest_log": latest_log,
        },
        "sources": [
            "web/data/fleetnet.json",
            "web/data/watch-officer-status.json",
            "Root Console handoff index",
            "Root Console Ship's Log",
            "data/root-console/speech-acceptance.json",
        ],
    }
