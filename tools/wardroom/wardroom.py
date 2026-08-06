#!/usr/bin/env python3
"""Append-only Wardroom clerk for formal meeting capture.

This tool records what the meeting says; it never edits doctrine or promotes
canon. The Captain performs conflict checking and doctrine filing separately.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

KINDS = {"observation", "interpretation", "proposal", "ruling", "action", "gate", "correction"}
RULINGS = {"CANON", "HOLD", "REJECTED", "SUPERSEDED"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def events(path: Path) -> list[dict]:
    if not path.exists():
        return []
    result = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            result.append(json.loads(line))
        except json.JSONDecodeError as error:
            raise SystemExit(f"invalid ledger line {number}: {error}") from error
    return result


def append(path: Path, event: dict) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    event = {"seq": len(events(path)) + 1, "at": now(), **event}
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    return event


def require_open(path: Path) -> list[dict]:
    ledger = events(path)
    if not ledger or ledger[0].get("type") != "meeting_opened":
        raise SystemExit("meeting ledger is not initialized")
    if any(event.get("type") == "meeting_adjourned" for event in ledger):
        raise SystemExit("meeting is already adjourned")
    return ledger


def candidate_map(ledger: list[dict]) -> dict[str, dict]:
    return {event["candidate_id"]: event for event in ledger if event.get("type") == "candidate"}


def latest_rulings(ledger: list[dict]) -> dict[str, dict]:
    result = {}
    for event in ledger:
        if event.get("type") == "candidate_ruling":
            result[event["candidate_id"]] = event
    return result


def command_init(args) -> dict:
    if events(args.ledger):
        raise SystemExit("refusing to overwrite a non-empty ledger")
    return append(args.ledger, {"type": "meeting_opened", "meeting": args.meeting,
                                "purpose": args.purpose, "muster": args.muster,
                                "captain_explanation": "Opens the authoritative meeting context and its purpose."})


def command_add(args) -> dict:
    require_open(args.ledger)
    return append(args.ledger, {"type": "meeting_record", "kind": args.kind,
                                "text": args.text, "evidence": args.evidence or "UNVERIFIED",
                                "captain_explanation": args.explanation})


def command_candidate(args) -> dict:
    ledger = require_open(args.ledger)
    if args.candidate_id in candidate_map(ledger):
        raise SystemExit(f"candidate already exists: {args.candidate_id}")
    return append(args.ledger, {"type": "candidate", "candidate_id": args.candidate_id,
                                "text": args.text, "scope": args.scope,
                                "destination": args.destination or "UNRESOLVED",
                                "captain_explanation": args.explanation})


def command_rule(args) -> dict:
    ledger = require_open(args.ledger)
    if args.candidate_id not in candidate_map(ledger):
        raise SystemExit(f"unknown candidate: {args.candidate_id}")
    prior = latest_rulings(ledger).get(args.candidate_id)
    if prior and args.ruling != "SUPERSEDED":
        raise SystemExit(f"candidate already ruled {prior['ruling']}; use SUPERSEDED before replacement")
    return append(args.ledger, {"type": "candidate_ruling", "candidate_id": args.candidate_id,
                                "ruling": args.ruling, "authority": args.authority,
                                "note": args.note or "", "captain_explanation": args.explanation})


def command_action(args) -> dict:
    require_open(args.ledger)
    return append(args.ledger, {"type": "action", "owner": args.owner, "text": args.text,
                                "acceptance": args.acceptance, "state": "OPEN",
                                "captain_explanation": args.explanation})


def command_resolve_gate(args) -> dict:
    ledger = require_open(args.ledger)
    if not any(event.get("seq") == args.seq and event.get("type") == "meeting_record" and event.get("kind") == "gate" for event in ledger):
        raise SystemExit(f"unknown gate sequence: {args.seq}")
    return append(args.ledger, {"type": "gate_resolved", "gate_seq": args.seq,
                                "authority": args.authority, "note": args.note,
                                "captain_explanation": args.explanation})


def command_explain(args) -> dict:
    ledger = require_open(args.ledger)
    if not any(event.get("seq") == args.seq for event in ledger):
        raise SystemExit(f"unknown event sequence: {args.seq}")
    return append(args.ledger, {"type": "event_explained", "target_seq": args.seq,
                                "explanation": args.explanation})


def readback(ledger: list[dict]) -> str:
    candidates = candidate_map(ledger)
    rulings = latest_rulings(ledger)
    lines = ["# Captain Readback", "", "## Rulings"]
    active = {candidate_id: ruling for candidate_id, ruling in rulings.items() if ruling["ruling"] != "SUPERSEDED"}
    historical = {candidate_id: ruling for candidate_id, ruling in rulings.items() if ruling["ruling"] == "SUPERSEDED"}
    if active:
        for candidate_id, ruling in active.items():
            lines.append(f"- **{candidate_id} — {ruling['ruling']}:** {candidates[candidate_id]['text']}")
    else:
        lines.append("- No candidate rulings recorded.")
    if historical:
        lines += ["", "## Historical dispositions"]
        lines += [f"- **{candidate_id} — SUPERSEDED:** {candidates[candidate_id]['text']}"
                  for candidate_id in historical]
    lines += ["", "## Actions"]
    actions = [event for event in ledger if event.get("type") == "action"]
    lines += [f"- **{event['owner']}:** {event['text']} — acceptance: {event['acceptance']}"
              for event in actions] or ["- No actions recorded."]
    lines += ["", "## Gates"]
    resolved_gates = {event["gate_seq"] for event in ledger if event.get("type") == "gate_resolved"}
    gates = [event for event in ledger if event.get("type") == "meeting_record" and event.get("kind") == "gate" and event.get("seq") not in resolved_gates]
    lines += [f"- {event['text']}" for event in gates] or ["- No gates recorded."]
    unresolved = [key for key in candidates if key not in rulings]
    if unresolved:
        lines += ["", "## Unresolved candidates", *[f"- {key}: {candidates[key]['text']}" for key in unresolved]]
    explained = {event["target_seq"] for event in ledger if event.get("type") == "event_explained"}
    missing = [str(event["seq"]) for event in ledger
               if event.get("type") not in {"meeting_opened", "event_explained"}
               and not event.get("captain_explanation") and event.get("seq") not in explained]
    lines += ["", "## Explainability"]
    lines.append("- All durable events have Captain explanations." if not missing
                 else "- Missing Captain explanations: " + ", ".join(missing))
    return "\n".join(lines) + "\n"


def command_readback(args) -> None:
    ledger = events(args.ledger)
    if not ledger:
        raise SystemExit("meeting ledger is empty")
    sys.stdout.write(readback(ledger))


def packet(ledger: list[dict]) -> str:
    """Render one portable meeting packet without changing the ledger."""
    opened = next((event for event in ledger if event.get("type") == "meeting_opened"), {})
    lines = [
        f"# Meeting Packet — {opened.get('meeting', 'Wardroom')}", "",
        f"**Purpose:** {opened.get('purpose', 'Not recorded')}",
        f"**Muster:** {opened.get('muster', 'Not recorded')}", "",
        readback(ledger).rstrip(), "",
        "## Evidence trail",
    ]
    records = [event for event in ledger if event.get("type") not in {"meeting_opened", "event_explained"}]
    lines.extend(
        f"- **#{event['seq']} · {event.get('type')}** {event.get('text') or event.get('note') or event.get('candidate_id', '')}"
        for event in records
    )
    return "\n".join(lines) + "\n"


def command_export(args) -> None:
    ledger = events(args.ledger)
    if not ledger:
        raise SystemExit("meeting ledger is empty")
    output = args.output or args.ledger.with_suffix(".packet.md")
    output.write_text(packet(ledger), encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(output), "events": len(ledger)}, indent=2))


def command_adjourn(args) -> dict:
    ledger = require_open(args.ledger)
    unresolved = [key for key in candidate_map(ledger) if key not in latest_rulings(ledger)]
    if unresolved and not args.allow_unresolved:
        raise SystemExit("unresolved candidates: " + ", ".join(unresolved))
    return append(args.ledger, {"type": "meeting_adjourned", "authority": args.authority,
                                "note": args.note or "", "unresolved": unresolved})


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--ledger", type=Path, required=True)
    commands = root.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init"); init.add_argument("--meeting", required=True); init.add_argument("--purpose", required=True); init.add_argument("--muster", required=True); init.set_defaults(run=command_init)
    add = commands.add_parser("add"); add.add_argument("--kind", choices=sorted(KINDS), required=True); add.add_argument("--text", required=True); add.add_argument("--evidence"); add.add_argument("--explanation", required=True); add.set_defaults(run=command_add)
    candidate = commands.add_parser("candidate"); candidate.add_argument("--id", dest="candidate_id", required=True); candidate.add_argument("--text", required=True); candidate.add_argument("--scope", required=True); candidate.add_argument("--destination"); candidate.add_argument("--explanation", required=True); candidate.set_defaults(run=command_candidate)
    rule = commands.add_parser("rule"); rule.add_argument("--id", dest="candidate_id", required=True); rule.add_argument("--ruling", choices=sorted(RULINGS), required=True); rule.add_argument("--authority", required=True); rule.add_argument("--note"); rule.add_argument("--explanation", required=True); rule.set_defaults(run=command_rule)
    action = commands.add_parser("action"); action.add_argument("--owner", required=True); action.add_argument("--text", required=True); action.add_argument("--acceptance", required=True); action.add_argument("--explanation", required=True); action.set_defaults(run=command_action)
    rb = commands.add_parser("readback"); rb.set_defaults(run=command_readback)
    export = commands.add_parser("export"); export.add_argument("--output", type=Path); export.set_defaults(run=command_export)
    adjourn = commands.add_parser("adjourn"); adjourn.add_argument("--authority", required=True); adjourn.add_argument("--note"); adjourn.add_argument("--allow-unresolved", action="store_true"); adjourn.set_defaults(run=command_adjourn)
    resolve = commands.add_parser("resolve-gate"); resolve.add_argument("--seq", type=int, required=True); resolve.add_argument("--authority", required=True); resolve.add_argument("--note", required=True); resolve.add_argument("--explanation", required=True); resolve.set_defaults(run=command_resolve_gate)
    explain = commands.add_parser("explain"); explain.add_argument("--seq", type=int, required=True); explain.add_argument("--explanation", required=True); explain.set_defaults(run=command_explain)
    return root


def main() -> int:
    args = parser().parse_args()
    result = args.run(args)
    if result is not None:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
