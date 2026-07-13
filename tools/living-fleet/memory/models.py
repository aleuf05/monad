"""Shared row shapes, id generation, and JSON-column registry for the memory
store. Kept intentionally lightweight (plain dicts + a couple of dataclasses
for the two prompt-facing return shapes) rather than a full ORM layer -- this
mirrors the stdlib-only, no-framework style already used by
tools/living-fleet/captain_runtime.py.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

FLEET_SCOPE = "fleet"


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:16]}"


def now() -> float:
    return time.time()


# Columns that are stored as JSON text and must be encoded/decoded on the way
# in/out of sqlite3. Registered per table so store.py's generic CRUD helpers
# can stay generic instead of hand-rolling (de)serialization per call site.
JSON_COLUMNS: dict[str, tuple[str, ...]] = {
    "events": ("who_json", "payload_json", "salience_factors_json"),
    "episodic_memories": (
        "who_json",
        "evidence_json",
        "interpretation_history_json",
        "tags_json",
        "influenced_decisions_json",
        "embedding_json",
    ),
    "semantic_beliefs": ("evidence_json",),
    "procedural_lessons": ("evidence_json",),
    "relationships": ("evidence_json",),
    "narrative_memories": ("tags_json",),
    "reflections": (
        "patterns_json",
        "belief_revisions_json",
        "procedural_lessons_json",
        "relationship_updates_json",
        "memory_strength_changes_json",
        "trait_shift_proposal_json",
        "evidence_json",
    ),
    "identity_traits": ("seed_json", "traits_json", "trait_bounds_json", "drift_log_json"),
    "corrections": ("before_json", "after_json"),
}

ID_COLUMNS: dict[str, str] = {
    "events": "event_id",
    "episodic_memories": "episodic_id",
    "semantic_beliefs": "belief_id",
    "procedural_lessons": "lesson_id",
    "relationships": "relationship_id",
    "narrative_memories": "narrative_id",
    "reflections": "reflection_id",
    "identity_traits": "captain_id",
    "corrections": "correction_id",
}

ID_PREFIXES: dict[str, str] = {
    "events": "evt",
    "episodic_memories": "epi",
    "semantic_beliefs": "bel",
    "procedural_lessons": "les",
    "relationships": "rel",
    "narrative_memories": "nar",
    "reflections": "refl",
    "corrections": "cor",
}


@dataclass
class RecordResult:
    event_id: str
    disposition: str
    salience_score: float
    episodic_id: Optional[str] = None
    reflection_triggered: bool = False
    reflection_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "disposition": self.disposition,
            "salience_score": self.salience_score,
            "episodic_id": self.episodic_id,
            "reflection_triggered": self.reflection_triggered,
            "reflection_id": self.reflection_id,
        }


@dataclass
class ContextBundle:
    captain_id: str
    purpose: str
    generated_at: float = field(default_factory=now)
    facts: list[dict] = field(default_factory=list)
    beliefs: list[dict] = field(default_factory=list)
    episodes: list[dict] = field(default_factory=list)
    procedural_guidance: list[dict] = field(default_factory=list)
    relationship_context: dict[str, dict] = field(default_factory=dict)
    narrative: list[dict] = field(default_factory=list)
    contradictions: list[dict] = field(default_factory=list)
    uncertainty_notes: list[str] = field(default_factory=list)
    identity_summary: dict = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "captain_id": self.captain_id,
            "purpose": self.purpose,
            "generated_at": self.generated_at,
            "facts": self.facts,
            "beliefs": self.beliefs,
            "episodes": self.episodes,
            "procedural_guidance": self.procedural_guidance,
            "relationship_context": self.relationship_context,
            "narrative": self.narrative,
            "contradictions": self.contradictions,
            "uncertainty_notes": self.uncertainty_notes,
            "identity_summary": self.identity_summary,
        }


DEFAULT_TRAIT_BOUNDS = {
    trait: {"min": 0.05, "max": 0.95, "max_delta_per_reflection": 0.07}
    for trait in ("caution", "initiative", "curiosity", "humor", "trust", "uncertainty_tolerance")
}
