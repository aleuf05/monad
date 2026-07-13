"""Reflection/consolidation pipeline.

HeuristicReflectionProvider is the safe, deterministic default -- pattern
detection over stored rows, no ML. CommandReflectionProvider mirrors
captain_runtime.py's existing MONAD_CAPTAIN_PROVIDER_COMMAND pattern exactly
(an external subprocess gets JSON on stdin, returns structured JSON on
stdout), so a real LLM can eventually do richer reflection without this
module's interface changing. Any external-provider failure (timeout, bad
JSON, invalid shape) falls back to the heuristic provider, same fail-open
shape used everywhere else in Living Fleet.

A reflection is itself a stored, evidenced record -- "not unquestionable
truth" -- and everything it proposes (belief revisions, procedural lessons,
relationship updates, trait shifts) is applied transactionally and remains
fully inspectable/correctable afterward.
"""

from __future__ import annotations

import json
import os
import shlex
import sqlite3
import subprocess
from collections import Counter
from typing import Any, Optional

from . import identity, store
from .models import now, new_id

_CONTRADICTION_MARKERS = ("faulty contact data", "was actually", "turned out to be", "not reckless", "reliable after all")
_POSITIVE_RELATIONSHIP_MARKERS = ("good collaboration", "reliable", "helped", "clear guidance", "smooth handoff")
_NEGATIVE_RELATIONSHIP_MARKERS = ("unclear instructions", "friction", "confusing", "conflicting orders", "miscommunication")

REPEATED_OUTCOME_THRESHOLD = 3
TRAIT_STEP = 0.03


def gather_reflection_evidence(
    conn: sqlite3.Connection,
    captain_id: str,
    period_start: Optional[str] = None,
    period_end: Optional[str] = None,
    limit: int = 200,
) -> dict[str, Any]:
    episodes = store.fetch_by(conn, "episodic_memories", captain_id=captain_id)
    if period_start:
        episodes = [row for row in episodes if (row.get("occurred_at") or "") >= period_start]
    if period_end:
        episodes = [row for row in episodes if (row.get("occurred_at") or "") <= period_end]
    episodes = episodes[-limit:]
    active_beliefs = [row for row in store.fetch_by(conn, "semantic_beliefs", captain_id=captain_id) if row["status"] == "active"]
    relationships = store.fetch_by(conn, "relationships", captain_id=captain_id)
    procedural = [row for row in store.fetch_by(conn, "procedural_lessons", captain_id=captain_id) if row["status"] == "active"]
    return {
        "captain_id": captain_id,
        "episodes": episodes,
        "active_beliefs": active_beliefs,
        "relationships": relationships,
        "procedural_lessons": procedural,
    }


class HeuristicReflectionProvider:
    name = "heuristic-reflection-v1"

    def reflect(self, captain_id: str, reason: str, evidence: dict[str, Any]) -> dict[str, Any]:
        episodes = evidence.get("episodes", [])
        active_beliefs = evidence.get("active_beliefs", [])

        patterns: list[dict] = []
        belief_revisions: list[dict] = []
        procedural_lessons: list[dict] = []
        relationship_updates: list[dict] = []
        memory_strength_changes: list[dict] = []
        trait_shift: dict[str, float] = {}

        # 1. Repeated similar outcomes -> pattern + procedural lesson candidate.
        tag_counter: Counter[str] = Counter()
        tag_outcomes: dict[str, list[str]] = {}
        for episode in episodes:
            for tag in episode.get("tags_json") or []:
                tag_counter[tag] += 1
                tag_outcomes.setdefault(tag, []).append(str(episode.get("outcome") or "").lower())
        for tag, count in tag_counter.items():
            if count < REPEATED_OUTCOME_THRESHOLD:
                continue
            outcomes = tag_outcomes[tag]
            positive = sum(1 for o in outcomes if o in ("success", "accepted"))
            negative = sum(1 for o in outcomes if o in ("failure", "rejected"))
            if positive >= REPEATED_OUTCOME_THRESHOLD and negative == 0:
                patterns.append({"tag": tag, "direction": "positive", "count": count})
                procedural_lessons.append(
                    {
                        "action": "new",
                        "situation": f"Encountering a '{tag}' situation",
                        "guidance": f"Continue the current approach -- it has succeeded {positive} times in a row.",
                        "confidence": min(0.9, 0.5 + 0.1 * positive),
                    }
                )
                trait_shift["initiative"] = trait_shift.get("initiative", 0.0) + TRAIT_STEP
            elif negative >= REPEATED_OUTCOME_THRESHOLD and positive == 0:
                patterns.append({"tag": tag, "direction": "negative", "count": count})
                procedural_lessons.append(
                    {
                        "action": "new",
                        "situation": f"Encountering a '{tag}' situation",
                        "guidance": f"Reconsider the current approach -- it has failed {negative} times in a row.",
                        "confidence": min(0.9, 0.5 + 0.1 * negative),
                    }
                )
                trait_shift["caution"] = trait_shift.get("caution", 0.0) + TRAIT_STEP
                # A repeated negative pattern specifically about another
                # entity (tagged with its id, e.g. "captain.alpha") is also
                # grounds to originate a new belief about that entity --
                # not just a procedural lesson for the observing captain's
                # own behavior. Only originates if no active belief about
                # that subject exists yet; a later contradicting episode is
                # handled by the revision pass below, not by this one.
                if "." in tag and not any(belief["subject"] == tag for belief in active_beliefs):
                    belief_revisions.append(
                        {
                            "action": "new",
                            "old_belief_id": None,
                            "subject": tag,
                            "new_statement": (
                                f"{tag} appears unreliable, based on {negative} recent negative outcome(s) this period."
                            ),
                            "confidence": min(0.75, 0.4 + 0.1 * negative),
                            "revision_reason": "Repeated negative outcomes observed this period.",
                        }
                    )

        # 2. Conflicting memories -> belief revision proposal.
        for belief in active_beliefs:
            subject = str(belief.get("subject") or "").lower()
            for episode in episodes:
                text = f"{episode.get('what', '')} {episode.get('interpretation') or ''}".lower()
                if subject and subject in text and any(marker in text for marker in _CONTRADICTION_MARKERS):
                    belief_revisions.append(
                        {
                            "action": "supersede",
                            "old_belief_id": belief["belief_id"],
                            "subject": belief["subject"],
                            "new_statement": (
                                f"Earlier assessment of {belief['subject']} was revised: {episode.get('what', '')}"
                            ),
                            "confidence": max(0.4, belief["confidence"] - 0.2),
                            "revision_reason": f"Contradicted by episodic memory {episode['episodic_id']}",
                        }
                    )
                    memory_strength_changes.append({"episodic_id": episode["episodic_id"], "strength_delta": 0.2})
                    trait_shift["uncertainty_tolerance"] = trait_shift.get("uncertainty_tolerance", 0.0) + TRAIT_STEP
                    trait_shift["trust"] = trait_shift.get("trust", 0.0) + TRAIT_STEP
                    break

        # 3. Major failure/success -> reinforce or form a procedural lesson.
        if reason in ("major-failure", "major-success"):
            candidates = sorted(episodes, key=lambda item: item.get("salience_score", 0.0), reverse=True)
            if candidates:
                top = candidates[0]
                direction = "avoid a repeat of" if reason == "major-failure" else "repeat the approach behind"
                procedural_lessons.append(
                    {
                        "action": "new",
                        "situation": top.get("what", "a similar situation"),
                        "guidance": f"Deliberately {direction}: {top.get('what', '')}",
                        "confidence": 0.7,
                    }
                )

        # 4. Relationship signal from episode text mentioning another party.
        relationship_signal: dict[str, dict[str, float]] = {}
        for episode in episodes:
            who = episode.get("who_json") or []
            text = f"{episode.get('what', '')} {episode.get('interpretation') or ''}".lower()
            positive = any(marker in text for marker in _POSITIVE_RELATIONSHIP_MARKERS)
            negative = any(marker in text for marker in _NEGATIVE_RELATIONSHIP_MARKERS)
            if not (positive or negative):
                continue
            for other_id in who:
                if other_id == captain_id:
                    continue
                bucket = relationship_signal.setdefault(other_id, {"trust_delta": 0.0, "friction_delta": 0.0, "count": 0})
                if positive:
                    bucket["trust_delta"] += 0.03
                if negative:
                    bucket["friction_delta"] += 0.03
                bucket["count"] += 1
        for other_id, bucket in relationship_signal.items():
            relationship_updates.append(
                {
                    "other_id": other_id,
                    "trust_delta": round(min(0.15, bucket["trust_delta"]), 3),
                    "friction_delta": round(min(0.15, bucket["friction_delta"]), 3),
                    "note": f"{bucket['count']} relevant interaction(s) observed this period.",
                }
            )
            if other_id == "lieutenant.cgl" and bucket["friction_delta"] > 0:
                procedural_lessons.append(
                    {
                        "action": "new",
                        "situation": "Receiving instructions from the Lieutenant",
                        "guidance": "Prefer explicit doctrine over improvisation when instructions are ambiguous.",
                        "confidence": 0.6,
                    }
                )

        # 5. A high-absurdity narrative episode nudges humor a little.
        if any("quacken" in " ".join(episode.get("tags_json") or []).lower() for episode in episodes):
            trait_shift["humor"] = trait_shift.get("humor", 0.0) + TRAIT_STEP

        summary_parts = [f"Reflection triggered by {reason}."]
        if patterns:
            summary_parts.append(f"Found {len(patterns)} recurring pattern(s).")
        if belief_revisions:
            summary_parts.append(f"Proposed {len(belief_revisions)} belief revision(s).")
        if relationship_updates:
            summary_parts.append(f"Updated {len(relationship_updates)} relationship(s).")
        if not (patterns or belief_revisions or relationship_updates):
            summary_parts.append("No strong patterns found this period.")

        return {
            "summary": " ".join(summary_parts),
            "patterns": patterns,
            "belief_revisions": belief_revisions,
            "procedural_lessons": procedural_lessons,
            "relationship_updates": relationship_updates,
            "memory_strength_changes": memory_strength_changes,
            "trait_shift_proposal": trait_shift,
        }


class CommandReflectionProvider:
    def __init__(self, command: str):
        self.command = shlex.split(command)
        if not self.command:
            raise ValueError("reflection provider command is empty")
        self.name = f"command:{self.command[0].rsplit('/', 1)[-1]}"

    def reflect(self, captain_id: str, reason: str, evidence: dict[str, Any]) -> dict[str, Any]:
        request = {"captain_id": captain_id, "reason": reason, "evidence": evidence}
        completed = subprocess.run(
            self.command,
            input=json.dumps(request),
            text=True,
            capture_output=True,
            timeout=20,
            check=True,
        )
        return json.loads(completed.stdout)


def build_default_reflection_provider() -> "HeuristicReflectionProvider | CommandReflectionProvider":
    command = os.getenv("MONAD_REFLECTION_PROVIDER_COMMAND")
    if command:
        try:
            return CommandReflectionProvider(command)
        except ValueError:
            pass
    return HeuristicReflectionProvider()


def _validate_content(content: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(content, dict) or not str(content.get("summary", "")).strip():
        raise ValueError("reflection content must be a dict with a non-empty summary")
    return {
        "summary": str(content["summary"])[:2000],
        "patterns": content.get("patterns") or [],
        "belief_revisions": content.get("belief_revisions") or [],
        "procedural_lessons": content.get("procedural_lessons") or [],
        "relationship_updates": content.get("relationship_updates") or [],
        "memory_strength_changes": content.get("memory_strength_changes") or [],
        "trait_shift_proposal": content.get("trait_shift_proposal") or {},
    }


def apply_reflection(
    conn: sqlite3.Connection,
    captain_id: str,
    *,
    reason: str,
    content: dict[str, Any],
    provider_name: str,
    evidence: dict[str, Any],
    period_start: Optional[str] = None,
    period_end: Optional[str] = None,
) -> dict[str, Any]:
    content = _validate_content(content)
    at = now()

    for revision in content["belief_revisions"]:
        old_belief_id = revision.get("old_belief_id")
        new_belief_id = new_id("bel")
        # semantic_beliefs.superseded_by_belief_id and supersedes_belief_id
        # both reference semantic_beliefs itself, so the new row must exist
        # before the old row can be updated to point at it.
        store.insert(
            conn,
            "semantic_beliefs",
            {
                "belief_id": new_belief_id,
                "captain_id": captain_id,
                "subject": revision.get("subject", "unknown"),
                "statement": revision.get("new_statement", ""),
                "belief_type": "belief",
                "confidence": revision.get("confidence", 0.5),
                "evidence_json": revision.get("evidence", []),
                "provenance": "reflection",
                "status": "active",
                "supersedes_belief_id": old_belief_id,
                "superseded_by_belief_id": None,
                "revision_reason": revision.get("revision_reason", ""),
                "created_at": at,
                "updated_at": at,
            },
        )
        if old_belief_id:
            store.update(
                conn,
                "semantic_beliefs",
                old_belief_id,
                {"status": "superseded", "superseded_by_belief_id": new_belief_id, "updated_at": at},
            )

    for lesson in content["procedural_lessons"]:
        store.insert(
            conn,
            "procedural_lessons",
            {
                "lesson_id": new_id("les"),
                "captain_id": captain_id,
                "situation": lesson.get("situation", ""),
                "guidance": lesson.get("guidance", ""),
                "confidence": lesson.get("confidence", 0.5),
                "evidence_json": lesson.get("evidence", []),
                "status": "active",
                "times_reinforced": 1,
                "created_at": at,
                "updated_at": at,
            },
        )

    for update in content["relationship_updates"]:
        other_id = update["other_id"]
        existing = store.fetch_by(conn, "relationships", captain_id=captain_id, other_id=other_id)
        trust_delta = update.get("trust_delta", 0.0)
        friction_delta = update.get("friction_delta", 0.0)
        if existing:
            row = existing[0]
            store.update(
                conn,
                "relationships",
                row["relationship_id"],
                {
                    "trust": max(0.0, min(1.0, row["trust"] + trust_delta)),
                    "friction": max(0.0, min(1.0, row["friction"] + friction_delta)),
                    "history_summary": update.get("note", row.get("history_summary")),
                    "interaction_count": row.get("interaction_count", 0) + 1,
                    "updated_at": at,
                },
            )
        else:
            store.insert(
                conn,
                "relationships",
                {
                    "relationship_id": new_id("rel"),
                    "captain_id": captain_id,
                    "other_id": other_id,
                    "trust": max(0.0, min(1.0, 0.5 + trust_delta)),
                    "friction": max(0.0, min(1.0, friction_delta)),
                    "history_summary": update.get("note", ""),
                    "last_interaction_at": period_end,
                    "interaction_count": 1,
                    "evidence_json": [],
                    "updated_at": at,
                },
            )

    for change in content["memory_strength_changes"]:
        episodic = store.fetch_one(conn, "episodic_memories", change["episodic_id"])
        if episodic:
            new_strength = max(0.0, min(1.0, episodic["strength"] + change.get("strength_delta", 0.0)))
            store.update(conn, "episodic_memories", change["episodic_id"], {"strength": new_strength, "updated_at": at})

    trait_shift_applied = False
    if content["trait_shift_proposal"]:
        reflection_id_placeholder = new_id("refl")
        identity.apply_trait_shift(
            conn, captain_id, content["trait_shift_proposal"], reason=f"reflection:{reason}", reflection_id=reflection_id_placeholder
        )
        trait_shift_applied = True
    else:
        reflection_id_placeholder = new_id("refl")

    row = {
        "reflection_id": reflection_id_placeholder,
        "captain_id": captain_id,
        "triggered_by": reason,
        "period_start": period_start,
        "period_end": period_end,
        "summary": content["summary"],
        "patterns_json": content["patterns"],
        "belief_revisions_json": content["belief_revisions"],
        "procedural_lessons_json": content["procedural_lessons"],
        "relationship_updates_json": content["relationship_updates"],
        "memory_strength_changes_json": content["memory_strength_changes"],
        "trait_shift_proposal_json": content["trait_shift_proposal"],
        "trait_shift_applied": int(trait_shift_applied),
        "provider": provider_name,
        "evidence_json": {"episode_count": len(evidence.get("episodes", []))},
        "created_at": at,
    }
    store.insert(conn, "reflections", row)
    return store.fetch_one(conn, "reflections", reflection_id_placeholder)
