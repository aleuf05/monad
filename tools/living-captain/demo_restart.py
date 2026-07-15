#!/usr/bin/env python3
"""Living Captain V0.1 restart demonstration.

The acceptance test for the whole engineering order
(docs/engineering-orders/living-captain-v0.1.md): assemble a Captain
instance, have it observe real live fleet state, drop it without any
graceful shutdown (there is no shutdown method to call -- nothing in
this design relies on one), reassemble a fresh instance from persisted
disk state, and prove identity and action-record history survived
unchanged and uninterrupted.

Runs against real fleetcore-serve and world-intake, not fixtures, per
this repo's live-test policy. Exits 0 on pass, 1 on fail.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from captain import LivingCaptain, DEFAULT_STATE_DIR


def check(label: str, condition: bool, detail: str = "") -> bool:
    status = "PASS" if condition else "FAIL"
    line = f"[{status}] {label}"
    if detail:
        line += f" -- {detail}"
    print(line)
    return condition


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        state_dir = Path(temp_dir)
        print(f"Living Captain V0.1 restart demonstration, state dir: {state_dir}")
        print()

        print("-- boot instance A --")
        captain_a = LivingCaptain.assemble(state_dir, observe_limit=2)
        identity_a = captain_a.identity()
        observation_a = captain_a.observe()
        proposal_a = captain_a.record_proposal(
            "FleetCore and World Intake are both reachable; continue the restart proof.",
            detail={
                "fleetcore_tick": observation_a["detail"]["fleetcore_tick"],
                "pending_proposals": observation_a["detail"]["world_intake_pending_count"],
            },
        )
        actions_before = captain_a.actions()
        print(f"identity: {identity_a}")
        print(f"observation: {observation_a['summary']}")
        print(f"proposal: {proposal_a['summary']}")
        print(f"action log length: {len(actions_before)}")
        print()

        print("-- simulated crash: instance A dropped, no shutdown call --")
        del captain_a
        print()

        print("-- boot instance B from persisted disk state --")
        captain_b = LivingCaptain.assemble(state_dir, observe_limit=2)
        identity_b = captain_b.identity()
        observation_b = captain_b.observe()
        proposal_b = captain_b.record_proposal(
            "FleetCore and World Intake remain reachable after restart.",
            detail={
                "fleetcore_tick": observation_b["detail"]["fleetcore_tick"],
                "pending_proposals": observation_b["detail"]["world_intake_pending_count"],
            },
        )
        actions_after = captain_b.actions()
        print(f"identity: {identity_b}")
        print(f"observation: {observation_b['summary']}")
        print(f"proposal: {proposal_b['summary']}")
        print(f"action log length: {len(actions_after)}")
        print()

        print("-- checks --")
        results = []
        results.append(check(
            "identity persists across restart (captain_id)",
            identity_a["captain_id"] == identity_b["captain_id"],
            f"{identity_a['captain_id']!r} == {identity_b['captain_id']!r}",
        ))
        results.append(check(
            "identity persists across restart (created_at)",
            identity_a["created_at"] == identity_b["created_at"],
            f"{identity_a['created_at']!r} == {identity_b['created_at']!r}",
        ))
        results.append(check(
            "restart_count advanced by exactly one",
            identity_b["restart_count"] == identity_a["restart_count"] + 1,
            f"{identity_a['restart_count']} -> {identity_b['restart_count']}",
        ))
        results.append(check(
            "action log grew, nothing lost",
            len(actions_after) == len(actions_before) + 2,
            f"{len(actions_before)} -> {len(actions_after)}",
        ))
        prefix_matches = actions_after[: len(actions_before)] == actions_before
        results.append(check(
            "pre-restart action entries unchanged, no duplication or reordering",
            prefix_matches,
        ))
        sequences = [entry["sequence"] for entry in actions_after]
        results.append(check(
            "action sequence numbers are contiguous and gap-free",
            sequences == list(range(1, len(sequences) + 1)),
            f"{sequences}",
        ))
        kinds_before = [entry["kind"] for entry in actions_before[-2:]]
        kinds_after = [entry["kind"] for entry in actions_after[-2:]]
        results.append(check(
            "proposal notes are recorded alongside observations",
            kinds_before == ["observation", "proposal_note"]
            and kinds_after == ["observation", "proposal_note"],
            f"before={kinds_before}, after={kinds_after}",
        ))

        print()
        if all(results):
            print("RESULT: PASS -- durable command presence demonstrated across a restart.")
            return 0
        print("RESULT: FAIL")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
