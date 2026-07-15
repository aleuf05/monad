"""The Captain assembly contract.

One seam: given persisted state plus configuration, produce one running
LivingCaptain instance. Two calls to assemble() against the same state
directory must produce equivalent identity -- that equivalence is the
whole point, and is what the restart demonstration in demo_restart.py
proves against real live services.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

import action_log
import captain_state
import sight

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATE_DIR = ROOT / "data" / "living-captain"
DEFAULT_FLEETCORE_URL = "http://127.0.0.1:4771/snapshot"
DEFAULT_WORLD_INTAKE_URL = "http://127.0.0.1:4773/proposals?status=pending"


class LivingCaptain:
    def __init__(
        self,
        state: dict[str, Any],
        state_path: Path,
        action_log_path: Path,
        fleetcore_url: str,
        world_intake_url: str,
    ):
        self.state = state
        self.state_path = state_path
        self.action_log_path = action_log_path
        self.fleetcore_url = fleetcore_url
        self.world_intake_url = world_intake_url

    @classmethod
    def assemble(
        cls,
        state_dir: str | Path = DEFAULT_STATE_DIR,
        *,
        captain_id: str = captain_state.DEFAULT_CAPTAIN_ID,
        fleetcore_url: str = DEFAULT_FLEETCORE_URL,
        world_intake_url: str = DEFAULT_WORLD_INTAKE_URL,
    ) -> "LivingCaptain":
        state_dir = Path(state_dir)
        state_path = state_dir / "state.json"
        action_log_path = state_dir / "actions.jsonl"

        state = captain_state.load_state(state_path, captain_id=captain_id)
        state["restart_count"] = state.get("restart_count", 0) + 1
        state["last_assembled_at"] = captain_state.now()
        captain_state.save_state(state_path, state)

        return cls(state, state_path, action_log_path, fleetcore_url, world_intake_url)

    def identity(self) -> dict[str, Any]:
        return {
            "captain_id": self.state["captain_id"],
            "created_at": self.state["created_at"],
            "restart_count": self.state["restart_count"],
        }

    def observe(self) -> dict[str, Any]:
        """Read real fleet state and the World Intake queue through the
        read-only sight adapters, persist the resulting pointers, and
        record the observation. Never mutates anything it reads."""
        snapshot = sight.fetch_fleetcore_snapshot(self.fleetcore_url)
        pending = sight.fetch_world_intake_pending(self.world_intake_url)

        self.state["last_seen_fleetcore_tick"] = snapshot.get("tick")
        self.state["last_seen_fleetcore_event_sequence"] = snapshot.get("event_sequence")
        self.state["last_seen_world_intake_pending_count"] = len(pending)
        captain_state.save_state(self.state_path, self.state)

        return action_log.append_action(
            self.action_log_path,
            kind="observation",
            summary=(
                f"tick={snapshot.get('tick')} "
                f"event_sequence={snapshot.get('event_sequence')} "
                f"pending_proposals={len(pending)}"
            ),
            detail={
                "fleetcore_tick": snapshot.get("tick"),
                "fleetcore_event_sequence": snapshot.get("event_sequence"),
                "world_intake_pending_count": len(pending),
            },
        )

    def actions(self) -> list[dict[str, Any]]:
        return action_log.read_actions(self.action_log_path)
