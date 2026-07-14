"""Context retrieval: Captain Runtime asks for context BY PURPOSE, never by
querying raw storage directly. request_context() balances relevance
(including local TF-IDF cosine similarity), recency, salience, and diversity
so one dramatic memory can't crowd out contradictory experience, and always
keeps facts/beliefs/narrative in separate keys so fact vs. interpretation vs.
mythology stay distinguishable in whatever consumes the bundle.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any, Optional

from . import embeddings, identity, store
from .models import FLEET_SCOPE, ContextBundle, now

# Purpose profiles name exactly the packet's own examples. Each controls
# which memory kinds get pulled and whether relationship/narrative context is
# relevant at all for that purpose.
PURPOSE_PROFILES: dict[str, dict[str, bool]] = {
    "prepare-mission-assessment": dict(beliefs=True, episodes=True, procedural=True, relationships=False, narrative=True),
    "respond-to-lieutenant": dict(beliefs=True, episodes=True, procedural=True, relationships=True, narrative=False),
    "evaluate-reliability": dict(beliefs=True, episodes=True, procedural=False, relationships=True, narrative=False),
    "interpret-new-contact": dict(beliefs=True, episodes=True, procedural=True, relationships=False, narrative=True),
    "reflect-on-mission": dict(beliefs=True, episodes=True, procedural=True, relationships=False, narrative=True),
    "choose-procedure": dict(beliefs=True, episodes=False, procedural=True, relationships=False, narrative=False),
    "recall-doctrine": dict(beliefs=True, episodes=False, procedural=False, relationships=False, narrative=False),
}
DEFAULT_PROFILE = dict(beliefs=True, episodes=True, procedural=True, relationships=True, narrative=True)

RELEVANCE_WEIGHT = 0.4
RECENCY_WEIGHT = 0.3
SALIENCE_WEIGHT = 0.3
DIVERSITY_PENALTY = 0.5


def _parse_time(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value)
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def _recency_score(occurred_at: Any, reference_ts: float) -> float:
    occurred_ts = _parse_time(occurred_at)
    if occurred_ts <= 0:
        return 0.0
    age_seconds = max(0.0, reference_ts - occurred_ts)
    # Half-life-ish decay: ~1.0 for "just happened", ~0.5 around 6 hours old,
    # asymptoting toward 0 for genuinely old memories -- tunable, not exact.
    return 1.0 / (1.0 + age_seconds / 21600.0)


def _tag_set(row: dict) -> set[str]:
    tags = row.get("tags_json") or []
    if isinstance(tags, str):
        tags = [tags]
    return set(tags)


def _rank_and_select(rows: list[dict], query_vector: dict[str, float], idf: dict, reference_ts: float, max_items: int, text_field: str) -> list[dict]:
    if not rows:
        return []
    scored = []
    for row in rows:
        row_vector = embeddings.vectorize(str(row.get(text_field) or ""), idf)
        relevance = embeddings.cosine_similarity(query_vector, row_vector) if query_vector else 0.3
        recency = _recency_score(row.get("occurred_at") or row.get("created_at"), reference_ts)
        salience = float(row.get("salience_score") or row.get("confidence") or 0.5)
        score = RELEVANCE_WEIGHT * relevance + RECENCY_WEIGHT * recency + SALIENCE_WEIGHT * salience
        scored.append((score, row))
    scored.sort(key=lambda pair: pair[0], reverse=True)

    selected: list[dict] = []
    selected_tags: set[str] = set()
    for score, row in scored:
        if len(selected) >= max_items:
            break
        row_tags = _tag_set(row)
        overlap_penalty = DIVERSITY_PENALTY if (row_tags and row_tags & selected_tags) else 0.0
        effective_score = score * (1.0 - overlap_penalty)
        if effective_score < 0 and selected:
            continue
        selected.append(row)
        selected_tags |= row_tags
    return selected


def _query_text(purpose: str, subject: Optional[str]) -> str:
    return f"{purpose.replace('-', ' ')} {subject or ''}".strip()


def request_context(
    conn: sqlite3.Connection,
    captain_id: str,
    *,
    purpose: str,
    subject: Optional[str] = None,
    max_items: int = 8,
) -> dict[str, Any]:
    profile = PURPOSE_PROFILES.get(purpose, DEFAULT_PROFILE)
    reference_ts = now()

    active_beliefs = [
        row for row in store.fetch_by(conn, "semantic_beliefs", captain_id=captain_id) if row["status"] == "active"
    ]
    episodes = store.fetch_by(conn, "episodic_memories", captain_id=captain_id)
    fleet_episodes = store.fetch_by(conn, "episodic_memories", captain_id=FLEET_SCOPE)
    procedural = [row for row in store.fetch_by(conn, "procedural_lessons", captain_id=captain_id) if row["status"] == "active"]
    narrative = store.fetch_by(conn, "narrative_memories", captain_id=captain_id) + store.fetch_by(
        conn, "narrative_memories", captain_id=FLEET_SCOPE
    )

    corpus = (
        [row["statement"] for row in active_beliefs]
        + [row["what"] for row in episodes]
        + [row["what"] for row in fleet_episodes]
        + [row["guidance"] for row in procedural]
    )
    idf = embeddings.build_idf(corpus) if corpus else {}
    query_vector = embeddings.vectorize(_query_text(purpose, subject), idf) if idf else {}

    bundle = ContextBundle(captain_id=captain_id, purpose=purpose)

    if profile.get("beliefs"):
        subject_filtered = (
            [row for row in active_beliefs if subject and subject.lower() in str(row.get("subject", "")).lower()]
            if subject
            else active_beliefs
        )
        pool = subject_filtered or active_beliefs
        facts_pool = [row for row in pool if row["belief_type"] in ("fact", "doctrine")]
        beliefs_pool = [row for row in pool if row["belief_type"] == "belief"]
        bundle.facts = _rank_and_select(facts_pool, query_vector, idf, reference_ts, max_items, "statement")
        bundle.beliefs = _rank_and_select(beliefs_pool, query_vector, idf, reference_ts, max_items, "statement")

        by_subject: dict[str, list[dict]] = {}
        for row in active_beliefs:
            by_subject.setdefault(row["subject"], []).append(row)
        for subject_key, rows in by_subject.items():
            if len(rows) > 1 and len({row["statement"] for row in rows}) > 1:
                bundle.contradictions.append(
                    {"subject": subject_key, "statements": [row["statement"] for row in rows]}
                )
        bundle.uncertainty_notes.extend(
            f"Low confidence ({row['confidence']:.2f}) on: {row['statement']}"
            for row in pool
            if row["confidence"] < 0.5
        )

    if profile.get("episodes"):
        pool = episodes
        if subject:
            pool = [row for row in pool if subject.lower() in (str(row.get("who_json") or "") + row.get("what", "")).lower()] or episodes
        bundle.episodes = _rank_and_select(pool, query_vector, idf, reference_ts, max_items, "what")
        bundle.uncertainty_notes.extend(
            f"Low certainty ({row['certainty']:.2f}) on: {row['what']}" for row in bundle.episodes if row["certainty"] < 0.6
        )

    if profile.get("procedural"):
        bundle.procedural_guidance = _rank_and_select(procedural, query_vector, idf, reference_ts, max_items, "guidance")

    if profile.get("relationships"):
        relationships = store.fetch_by(conn, "relationships", captain_id=captain_id)
        bundle.relationship_context = {row["other_id"]: row for row in relationships}

    if profile.get("narrative"):
        bundle.narrative = _rank_and_select(narrative, query_vector, idf, reference_ts, max_items, "fact_summary")

    bundle.identity_summary = _identity_summary(conn, captain_id)
    return bundle.to_dict()


def _identity_summary(conn: sqlite3.Connection, captain_id: str) -> dict[str, Any]:
    traits_row = identity.get_traits(conn, captain_id)
    seed = traits_row["seed_json"]
    return {
        "role": seed.get("role_summary"),
        "values": seed.get("values_priorities"),
        "communication_style": seed.get("communication_style"),
        "current_tendencies": traits_row["traits_json"],
    }


def request_relationship_context(conn: sqlite3.Connection, captain_id: str, other_id: str) -> dict[str, Any]:
    rows = store.fetch_by(conn, "relationships", captain_id=captain_id, other_id=other_id)
    if rows:
        return rows[0]
    return {
        "relationship_id": None,
        "captain_id": captain_id,
        "other_id": other_id,
        "trust": 0.5,
        "friction": 0.0,
        "history_summary": "No recorded history yet.",
        "interaction_count": 0,
    }
