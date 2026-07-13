#!/usr/bin/env python3
"""Curated Monad seed-memory importer.

Imports a deliberately small, curated subset of existing Monad history --
NOT the entire historical transcript -- clearly tagged as imported
orientation rather than firsthand captain experience. Idempotent: every seed
row uses a stable, deterministic id and re-running skips rows that already
exist rather than duplicating them.

Run directly: `python3 tools/living-fleet/memory/seed_import.py [--db PATH]`
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from memory import store  # noqa: E402
from memory.models import FLEET_SCOPE, now  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
SEED_DATA = Path(__file__).with_name("seed_data")
DEFAULT_DB = REPO_ROOT / "data" / "living-fleet" / "memory.db"
DEFAULT_CAPTAINS = Path(__file__).resolve().parents[1] / "captains.json"
QUACKEN_MISSION = REPO_ROOT / "web" / "missions" / "quacken-transit-002" / "mission.json"


def _seed_id(*parts: str) -> str:
    slug = "-".join(re.sub(r"[^a-z0-9]+", "-", part.lower()).strip("-") for part in parts)
    return f"seed-{slug}"


def _read_captains(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as stream:
        return json.load(stream)


def _insert_if_missing(conn, table: str, row: dict) -> bool:
    from memory.models import ID_COLUMNS

    id_column = ID_COLUMNS[table]
    existing = store.fetch_one(conn, table, row[id_column])
    if existing:
        return False
    store.insert(conn, table, row)
    return True


def _import_doctrine(conn, captain_id: str) -> int:
    text = (SEED_DATA / "doctrine_living_fleet.md").read_text()
    belief_id = _seed_id("bel", captain_id, "doctrine-living-fleet")
    at = now()
    return int(
        _insert_if_missing(
            conn,
            "semantic_beliefs",
            {
                "belief_id": belief_id,
                "captain_id": captain_id,
                "subject": "doctrine.living-fleet",
                "statement": text.strip(),
                "belief_type": "doctrine",
                "confidence": 1.0,
                "evidence_json": [{"file": "docs/architecture/living-fleet-v0.1.md"}],
                "provenance": "imported-history",
                "status": "active",
                "supersedes_belief_id": None,
                "superseded_by_belief_id": None,
                "revision_reason": None,
                "created_at": at,
                "updated_at": at,
            },
        )
    )


def _import_role(conn, captain_id: str, role: str) -> int:
    belief_id = _seed_id("bel", captain_id, "self-role")
    at = now()
    return int(
        _insert_if_missing(
            conn,
            "semantic_beliefs",
            {
                "belief_id": belief_id,
                "captain_id": captain_id,
                "subject": "self.role",
                "statement": f"My assigned role is: {role}.",
                "belief_type": "fact",
                "confidence": 1.0,
                "evidence_json": [{"file": "tools/living-fleet/captains.json"}],
                "provenance": "imported-history",
                "status": "active",
                "supersedes_belief_id": None,
                "superseded_by_belief_id": None,
                "revision_reason": None,
                "created_at": at,
                "updated_at": at,
            },
        )
    )


def _import_lieutenant_preferences(conn, captain_id: str) -> int:
    text = (SEED_DATA / "lieutenant_cgl_preferences.md").read_text()
    belief_id = _seed_id("bel", captain_id, "lieutenant-preferences")
    at = now()
    inserted = int(
        _insert_if_missing(
            conn,
            "semantic_beliefs",
            {
                "belief_id": belief_id,
                "captain_id": captain_id,
                "subject": "lieutenant.cgl",
                "statement": text.strip(),
                "belief_type": "belief",
                "confidence": 0.75,
                "evidence_json": [{"file": "CLAUDE.md"}],
                "provenance": "imported-history",
                "status": "active",
                "supersedes_belief_id": None,
                "superseded_by_belief_id": None,
                "revision_reason": None,
                "created_at": at,
                "updated_at": at,
            },
        )
    )
    relationship_id = _seed_id("rel", captain_id, "lieutenant-cgl")
    existing = store.fetch_by(conn, "relationships", captain_id=captain_id, other_id="lieutenant.cgl")
    if not existing:
        store.insert(
            conn,
            "relationships",
            {
                "relationship_id": relationship_id,
                "captain_id": captain_id,
                "other_id": "lieutenant.cgl",
                "trust": 0.5,
                "friction": 0.0,
                "history_summary": "Imported orientation from CLAUDE.md policy, not firsthand interaction history.",
                "last_interaction_at": None,
                "interaction_count": 0,
                "evidence_json": [{"file": "CLAUDE.md"}],
                "updated_at": at,
            },
        )
        inserted += 1
    return inserted


def _import_workflow_lesson(conn, captain_id: str) -> int:
    text = (SEED_DATA / "workflow_cleanup_lessons.md").read_text()
    lesson_id = _seed_id("les", captain_id, "workflow-cleanup")
    at = now()
    return int(
        _insert_if_missing(
            conn,
            "procedural_lessons",
            {
                "lesson_id": lesson_id,
                "captain_id": captain_id,
                "situation": "Receiving a work packet or instruction that references prior work or a prerequisite.",
                "guidance": (
                    "Verify the referenced prior work actually exists in the repository before building on it as "
                    "an assumption; surface any discrepancy explicitly."
                ),
                "confidence": 0.8,
                "evidence_json": [{"file": "toys/periscope/mk4/ENGINEERING_REPORT.md", "provenance": "imported-history"}],
                "status": "active",
                "times_reinforced": 1,
                "created_at": at,
                "updated_at": at,
            },
        )
    )


def _parse_quacken_fact(mission_path: Path) -> dict[str, Any]:
    data = json.loads(mission_path.read_text())
    complete_events = [e for e in data["evidence"] if e.get("phase") == "RENDEZVOUS_HOLD" and "hold criteria" in e.get("detail", "")]
    hold_detail = complete_events[0]["detail"] if complete_events else "rendezvous hold complete"
    tick = complete_events[0].get("tick") if complete_events else None
    return {
        "outcome": data.get("outcome", "unknown"),
        "phase": data.get("phase"),
        "hold_detail": hold_detail,
        "tick": tick,
        "mission_id": data.get("mission_id", "quacken-transit-002"),
    }


def _import_operation_quacken(conn, captains: list[dict]) -> int:
    if not QUACKEN_MISSION.exists():
        return 0
    fact = _parse_quacken_fact(QUACKEN_MISSION)
    fact_summary = (
        f"Mission {fact['mission_id']}: MONAD held rendezvous with contact QUACKEN; {fact['hold_detail']}"
        + (f" (tick {fact['tick']})" if fact["tick"] else "")
        + f"; outcome: {fact['outcome']}."
    )
    mythology_text = (SEED_DATA / "operation_quacken.md").read_text()
    mythology_section = mythology_text.split("## MYTHOLOGY", 1)[-1].split("\n", 1)[-1].strip()

    inserted = 0
    fleet_episodic_id = _seed_id("epi", "fleet", "operation-quacken")
    at = now()
    inserted += int(
        _insert_if_missing(
            conn,
            "episodic_memories",
            {
                "episodic_id": fleet_episodic_id,
                "captain_id": FLEET_SCOPE,
                "source_event_id": None,
                "occurred_at": "2026-07-13T19:27:50Z",
                "who_json": ["vessel.monad", "contact.rubber-ducky"],
                "what": fact_summary,
                "outcome": fact["outcome"],
                "evidence_json": [{"file": "web/missions/quacken-transit-002/mission.json"}],
                "certainty": 1.0,
                "interpretation": None,
                "interpretation_history_json": [],
                "salience_score": 0.9,
                "strength": 1.0,
                "tags_json": ["quacken", "mission-complete", "narrative"],
                "influenced_decisions_json": [],
                "is_imported_history": 1,
                "embedding_json": None,
                "created_at": at,
                "updated_at": at,
            },
        )
    )
    for captain in captains:
        narrative_id = _seed_id("nar", captain["captain_id"], "operation-quacken")
        inserted += int(
            _insert_if_missing(
                conn,
                "narrative_memories",
                {
                    "narrative_id": narrative_id,
                    "captain_id": captain["captain_id"],
                    "title": "Operation QUACKEN",
                    "fact_ref_episodic_id": fleet_episodic_id,
                    "fact_summary": fact_summary,
                    "mythology": mythology_section,
                    "tags_json": ["quacken", "fleet-lore"],
                    "is_imported_history": 1,
                    "created_at": at,
                    "updated_at": at,
                },
            )
        )
    return inserted


def import_seed_memory(db_path: Path = DEFAULT_DB, captains_path: Path = DEFAULT_CAPTAINS) -> dict[str, int]:
    conn = store.connect(db_path)
    captains = _read_captains(captains_path)
    counts = {"doctrine": 0, "roles": 0, "lieutenant_preferences": 0, "workflow_lessons": 0, "operation_quacken": 0}
    for captain in captains:
        captain_id = captain["captain_id"]
        counts["doctrine"] += _import_doctrine(conn, captain_id)
        counts["roles"] += _import_role(conn, captain_id, captain.get("role", ""))
        counts["lieutenant_preferences"] += _import_lieutenant_preferences(conn, captain_id)
        counts["workflow_lessons"] += _import_workflow_lesson(conn, captain_id)
    counts["operation_quacken"] += _import_operation_quacken(conn, captains)
    conn.close()
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description="Import curated Monad seed memory.")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--captains", default=str(DEFAULT_CAPTAINS))
    args = parser.parse_args()
    counts = import_seed_memory(Path(args.db), Path(args.captains))
    print(json.dumps(counts, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
