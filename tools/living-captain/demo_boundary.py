#!/usr/bin/env python3
"""Living Captain V0.2 custody/spend boundary demonstration.

Proves the new boundary slice against the real live read endpoints:

- non-GET or out-of-manifest reads are rejected before network I/O;
- an assembled Captain can spend exactly one observe call by default;
- the exhausted budget survives restart and does not reset silently.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

from captain import LivingCaptain, SpendBudgetExceeded
import sight


def check(label: str, condition: bool, detail: str = "") -> bool:
    status = "PASS" if condition else "FAIL"
    line = f"[{status}] {label}"
    if detail:
        line += f" -- {detail}"
    print(line)
    return condition


def prove_custody_guard() -> bool:
    print("-- custody guard --")
    results = []

    with patch("urllib.request.urlopen") as urlopen:
        try:
            sight.request_json(
                "http://127.0.0.1:4771/snapshot",
                method="POST",
            )
        except sight.CustodyViolation as error:
            results.append(check("non-GET request rejected before network call", True, str(error)))
        else:
            results.append(check("non-GET request rejected before network call", False))
        results.append(check("network layer was never reached", not urlopen.called))

    with patch("urllib.request.urlopen") as urlopen:
        try:
            sight.request_json("http://example.invalid/forbidden")
        except sight.CustodyViolation as error:
            results.append(check("out-of-manifest URL rejected before network call", True, str(error)))
        else:
            results.append(check("out-of-manifest URL rejected before network call", False))
        results.append(check("network layer was never reached", not urlopen.called))

    print()
    return all(results)


def prove_spend_restart() -> bool:
    print("-- spend boundary --")
    results = []

    with tempfile.TemporaryDirectory() as temp_dir:
        state_dir = Path(temp_dir)
        captain_a = LivingCaptain.assemble(state_dir)
        identity_a = captain_a.identity()
        observation_a = captain_a.observe()
        spend_a = captain_a.spend_status()

        captain_b = LivingCaptain.assemble(state_dir)
        identity_b = captain_b.identity()
        spend_b = captain_b.spend_status()

        try:
            captain_b.observe()
        except SpendBudgetExceeded as error:
            exhausted = True
            exhausted_message = str(error)
        else:
            exhausted = False
            exhausted_message = ""

        actions = captain_b.actions()
        persisted_state = json.loads((state_dir / "state.json").read_text())

        print(f"identity A: {identity_a}")
        print(f"identity B: {identity_b}")
        print(f"observation: {observation_a['summary']}")
        print(f"spend A: {spend_a}")
        print(f"spend B: {spend_b}")
        print(f"last action: {actions[-1]}")
        print()

        results.append(check(
            "identity survives restart",
            identity_a["captain_id"] == identity_b["captain_id"]
            and identity_a["created_at"] == identity_b["created_at"],
        ))
        results.append(check(
            "restart count advances",
            identity_b["restart_count"] == identity_a["restart_count"] + 1,
            f"{identity_a['restart_count']} -> {identity_b['restart_count']}",
        ))
        results.append(check(
            "first observe consumed the only allowed spend",
            spend_a == {"observe_count": 1, "observe_limit": 1, "remaining_observes": 0},
            f"{spend_a}",
        ))
        results.append(check(
            "restart does not reset the spent budget",
            spend_b == {"observe_count": 1, "observe_limit": 1, "remaining_observes": 0},
            f"{spend_b}",
        ))
        results.append(check(
            "second observe is rejected after restart",
            exhausted,
            exhausted_message,
        ))
        results.append(check(
            "exhaustion is logged durably",
            actions[-1]["kind"] == "spend_exhausted",
            actions[-1]["summary"],
        ))
        results.append(check(
            "persisted state retains custody manifest and spend count",
            persisted_state["custody_manifest"] == sight.custody_manifest()
            and persisted_state["observe_count"] == 1
            and persisted_state["observe_limit"] == 1,
            json.dumps(persisted_state["custody_manifest"], sort_keys=True),
        ))

    print()
    return all(results)


def main() -> int:
    print("Living Captain V0.2 custody/spend demonstration")
    print()

    guard_ok = prove_custody_guard()
    spend_ok = prove_spend_restart()

    if guard_ok and spend_ok:
        print("RESULT: PASS -- custody and spend boundaries survive restart.")
        return 0
    print("RESULT: FAIL")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
