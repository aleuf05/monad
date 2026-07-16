#!/usr/bin/env python3
"""Assemble evidence and validate provider-produced fleet legends."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


COMPLETE_PHASE = "MISSION_COMPLETE"
REQUIRED_CANDIDATE_FIELDS = {"title", "mythology", "classification", "source_ids"}


class PipelineError(ValueError):
    """Raised when evidence or a legend candidate fails closed."""


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PipelineError(f"cannot read JSON from {path}: {error}") from error
    if not isinstance(value, dict):
        raise PipelineError(f"expected a JSON object in {path}")
    return value


def assemble_evidence(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    mission = load_json(path)
    mission_id = mission.get("mission_id")
    if not mission_id:
        raise PipelineError("mission_id is required")
    if mission.get("phase") != COMPLETE_PHASE or mission.get("outcome") != "success":
        raise PipelineError("only completed successful missions are eligible for legend generation")
    transitions = [event for event in mission.get("evidence", []) if event.get("kind") == "phase_transition"]
    completion = [event for event in transitions if "-> MISSION_COMPLETE:" in str(event.get("detail", ""))]
    rendezvous = [event for event in transitions if "-> RENDEZVOUS_HOLD:" in str(event.get("detail", ""))]
    if len(completion) != 1 or len(rendezvous) != 1:
        raise PipelineError("mission requires exactly one rendezvous and one completion transition")
    if completion[0].get("tick", 0) < rendezvous[0].get("tick", 0):
        raise PipelineError("contradictory evidence: completion precedes rendezvous")
    source_id = f"mission.{mission_id}"
    facts = [
        {"claim": f"Mission {mission_id} completed successfully.", "source_ids": [source_id]},
        {"claim": rendezvous[0]["detail"], "source_ids": [source_id]},
        {"claim": completion[0]["detail"], "source_ids": [source_id]},
    ]
    return {
        "request_id": f"legend.{mission_id}",
        "subject": f"Mission {mission_id}",
        "source_id": source_id,
        "source": {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest()},
        "verified_facts": facts,
        "unknowns": [],
        "contradictions": [],
        "mission": {
            "mission_id": mission_id,
            "outcome": mission["outcome"],
            "completion_tick": completion[0].get("tick"),
            "completion_time": completion[0].get("sim_time"),
        },
    }


def render_fact(bundle: dict[str, Any]) -> dict[str, Any]:
    mission = bundle["mission"]
    details = [fact["claim"] for fact in bundle["verified_facts"]]
    hold = details[2].split(":", 1)[-1].strip().rstrip(".")
    summary = (
        f"Mission {mission['mission_id']}: MONAD reached rendezvous with contact QUACKEN; "
        f"{hold}; outcome: {mission['outcome']}."
    )
    return {
        "fact_summary": summary,
        "fact_claims": bundle["verified_facts"],
        "source_ids": [bundle["source_id"]],
    }


def generation_request(bundle: dict[str, Any], fact: dict[str, Any]) -> dict[str, Any]:
    return {
        "request_id": bundle["request_id"],
        "task": "Write a short fleet legend inspired by the verified record.",
        "verified_record": fact,
        "rules": [
            "Return JSON only with title, mythology, classification, and source_ids.",
            "classification must be fleet-lore.",
            "Make the retelling playful and culturally memorable.",
            "Do not claim the mythology is operational fact or alter the verified record.",
            "Do not introduce real people, secrets, credentials, or private data.",
            "Use only the supplied source_ids.",
        ],
        "output_schema": {
            "title": "string",
            "mythology": "string",
            "classification": "fleet-lore",
            "source_ids": [bundle["source_id"]],
        },
    }


def validate_candidate(bundle: dict[str, Any], fact: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    missing = REQUIRED_CANDIDATE_FIELDS - candidate.keys()
    if missing:
        errors.append(f"missing fields: {', '.join(sorted(missing))}")
    title = str(candidate.get("title", "")).strip()
    mythology = str(candidate.get("mythology", "")).strip()
    if not title or not mythology:
        errors.append("title and mythology must be non-empty")
    if candidate.get("classification") != "fleet-lore":
        errors.append("classification must be fleet-lore")
    if candidate.get("source_ids") != [bundle["source_id"]]:
        errors.append("source_ids must exactly match the evidence bundle")
    if mythology == fact["fact_summary"]:
        errors.append("mythology must remain distinct from the factual summary")
    lowered = mythology.lower()
    forbidden_claims = ("operational fact", "simulation truth", "verified fact")
    if any(term in lowered for term in forbidden_claims):
        errors.append("mythology may not present itself as operational truth")
    if len(mythology) > 2000:
        errors.append("mythology exceeds the 2000-character v1 limit")
    if errors:
        raise PipelineError("; ".join(errors))
    return {
        "status": "validated-candidate",
        "request_id": bundle["request_id"],
        "candidate": candidate,
        "fact_summary": fact["fact_summary"],
        "provenance": bundle["source"],
    }


def prepare(path: Path) -> dict[str, Any]:
    bundle = assemble_evidence(path)
    fact = render_fact(bundle)
    return {"evidence_bundle": bundle, "fact": fact, "generation_request": generation_request(bundle, fact)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("mission", type=Path)
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("mission", type=Path)
    validate_parser.add_argument("candidate", type=Path)
    args = parser.parse_args()
    try:
        result = prepare(args.mission)
        if args.command == "validate":
            result = validate_candidate(result["evidence_bundle"], result["fact"], load_json(args.candidate))
    except PipelineError as error:
        parser.error(str(error))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
