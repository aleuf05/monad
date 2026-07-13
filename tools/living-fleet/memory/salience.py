"""Salience scoring: what deserves to become durable memory.

Stdlib-only, rule-based, fully inspectable -- no ML/embeddings here (see
embeddings.py for the separate, explicitly-optional retrieval accelerator).
Every factor is a cheap, explainable heuristic over the fields already
present on FleetCore decisions/events, so `salience_factors_json` is always
a legible explanation of why a score landed where it did.

`event` is a plain dict shape (not yet a stored row):
  captain_id, kind ('event'|'decision'|'conversation'), category, summary,
  who (list[str]), payload (dict, arbitrary source-specific fields),
  observed_tick (optional), is_imported_history (optional), tags (optional).
"""

from __future__ import annotations

from typing import Any, Optional

FACTOR_WEIGHTS = {
    "novelty": 0.15,
    "danger": 0.15,
    "success_failure": 0.10,
    "surprise": 0.15,
    "social_importance": 0.10,
    "personal_relevance": 0.10,
    "conflict": 0.10,
    "expectation_violation": 0.10,
    "absurdity": 0.05,
}
assert abs(sum(FACTOR_WEIGHTS.values()) - 1.0) < 1e-9

DISCARD_MAX = 0.25
SUMMARIZE_MAX = 0.55
EPISODIC_MAX = 0.80
FORCED_REFLECT_THRESHOLD = 0.70  # a lone conflict/expectation-violation signal this strong forces reflection

NOVELTY_LOOKBACK = 50


def _novelty(event: dict, recent_events: list[dict]) -> float:
    category = event.get("category")
    if not category:
        return 0.3
    window = recent_events[-NOVELTY_LOOKBACK:]
    matches = [item for item in window if item.get("category") == category]
    if not matches:
        return 1.0
    return max(0.0, 1.0 - 0.15 * len(matches))


def _danger(event: dict) -> float:
    payload = event.get("payload") or {}
    if payload.get("posture") == "emergency-separation":
        return 1.0
    distance = payload.get("nearest_distance_m")
    if distance is not None:
        if distance < 300:
            return 1.0
        if distance < 800:
            return 0.5
    text = f"{event.get('category', '')} {event.get('summary', '')}".lower()
    if "collision" in text:
        return 1.0
    return 0.0


def _success_failure(event: dict) -> float:
    payload = event.get("payload") or {}
    outcome = str(payload.get("outcome") or event.get("outcome") or "").lower()
    if outcome in ("success", "accepted"):
        return 0.6
    if outcome in ("failure", "rejected"):
        return 0.85
    return 0.0


def _surprise(event: dict, recent_events: list[dict]) -> float:
    payload = event.get("payload") or {}
    outcome = str(payload.get("outcome", "")).lower()
    if outcome == "rejected":
        peers = [
            item
            for item in recent_events
            if item.get("captain_id") == event.get("captain_id") and (item.get("payload") or {}).get("outcome")
        ]
        if peers:
            accepted_ratio = sum(
                1 for item in peers if str((item.get("payload") or {}).get("outcome", "")).lower() == "accepted"
            ) / len(peers)
            if accepted_ratio > 0.8:
                return 0.9
    if payload.get("category") == "new-contact" and not payload.get("had_lead_in"):
        return 0.5
    return 0.1


def _social_importance(event: dict) -> float:
    who = event.get("who") or []
    if "lieutenant.cgl" in who:
        return 1.0
    if any(str(item).startswith("captain.") for item in who):
        return 0.6
    if event.get("kind") == "conversation":
        return 0.8
    return 0.1


def _personal_relevance(event: dict) -> float:
    payload = event.get("payload") or {}
    vessel_id = payload.get("vessel_id")
    captain_vessel_id = payload.get("captain_vessel_id")
    if vessel_id and captain_vessel_id and vessel_id == captain_vessel_id:
        return 1.0
    if payload.get("captain_id") == event.get("captain_id"):
        return 0.8
    return 0.3


_CONTRADICTION_MARKERS = ("faulty contact data", "was actually", "turned out to be", "not reckless", "reliable after all")


def _conflict(event: dict, active_beliefs: list[dict]) -> float:
    payload = event.get("payload") or {}
    if str(payload.get("outcome", "")).lower() == "rejected":
        return 0.7
    summary = str(event.get("summary", "")).lower()
    for belief in active_beliefs:
        subject = str(belief.get("subject") or "").lower()
        statement = str(belief.get("statement") or "").lower()
        if subject and subject in summary and any(marker in summary for marker in _CONTRADICTION_MARKERS):
            return 0.9
        if subject and subject in summary and statement and statement not in summary:
            # Same subject discussed again with materially different framing
            # is a soft conflict signal even without an explicit correction marker.
            overlap = set(statement.split()) & set(summary.split())
            if len(overlap) < max(1, len(statement.split()) // 3):
                return 0.35
    return 0.0


def _expectation_violation(event: dict) -> float:
    payload = event.get("payload") or {}
    default_posture = payload.get("default_posture")
    posture = payload.get("posture")
    if default_posture and posture and default_posture != posture and posture not in (
        "emergency-separation",
        "recover-formation",
    ):
        return 0.4
    reconsider_at = payload.get("reconsider_at_tick")
    submitted_tick = payload.get("submitted_tick")
    prior_reconsider_at = payload.get("prior_reconsider_at_tick")
    if prior_reconsider_at and submitted_tick and submitted_tick < prior_reconsider_at - 5:
        return 0.6  # reconsidered well before it was scheduled to
    return 0.0


_ABSURDITY_MARKERS = ("quacken", "duck", "mega-anatid", "easter-egg")


def _absurdity(event: dict) -> float:
    tags = " ".join(event.get("tags") or [])
    text = f"{event.get('category', '')} {event.get('summary', '')} {tags}".lower()
    if any(marker in text for marker in _ABSURDITY_MARKERS):
        return 0.9
    if event.get("is_imported_history"):
        return 0.3
    return 0.0


def score_event(
    event: dict,
    recent_events: Optional[list[dict]] = None,
    active_beliefs: Optional[list[dict]] = None,
) -> tuple[float, dict[str, float]]:
    recent_events = recent_events or []
    active_beliefs = active_beliefs or []
    factors = {
        "novelty": _novelty(event, recent_events),
        "danger": _danger(event),
        "success_failure": _success_failure(event),
        "surprise": _surprise(event, recent_events),
        "social_importance": _social_importance(event),
        "personal_relevance": _personal_relevance(event),
        "conflict": _conflict(event, active_beliefs),
        "expectation_violation": _expectation_violation(event),
        "absurdity": _absurdity(event),
    }
    score = sum(FACTOR_WEIGHTS[name] * value for name, value in factors.items())
    return max(0.0, min(1.0, score)), factors


def disposition_for(score: float, factors: dict[str, float]) -> str:
    if factors.get("conflict", 0.0) >= FORCED_REFLECT_THRESHOLD:
        return "episodic+reflect"
    if factors.get("expectation_violation", 0.0) >= FORCED_REFLECT_THRESHOLD:
        return "episodic+reflect"
    # Near-certain physical danger always demands reflection on its own,
    # never just a tally into the weighted sum -- a near-collision must
    # never be silently "summarized" away.
    if factors.get("danger", 0.0) >= 0.9:
        return "episodic+reflect"
    # A highly narrative event that's also highly social (e.g. a
    # Lieutenant-witnessed Operation QUACKEN completion) is exactly the kind
    # of thing the packet names as forming "durable narrative and social
    # memory" -- it should reliably become durable and reflect-worthy even
    # if no single weighted factor alone crosses the general threshold.
    if factors.get("absurdity", 0.0) >= 0.85 and factors.get("social_importance", 0.0) >= 0.8:
        return "episodic+reflect"
    if score >= EPISODIC_MAX:
        return "episodic+reflect"
    if score >= SUMMARIZE_MAX:
        return "episodic"
    if score >= DISCARD_MAX:
        return "summarize"
    return "discard"
