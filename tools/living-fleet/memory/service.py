"""MemoryService: the single stable, Runtime-facing API for Effort B.
Everything else in this package (salience, identity, context, reflection,
store) is an implementation detail behind this class.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from . import context as context_module
from . import identity, reflection, salience, store
from .models import ID_COLUMNS, FLEET_SCOPE, RecordResult, new_id, now


class MemoryService:
    def __init__(self, db_path: str | Path, captains: list[dict], reflection_provider=None):
        self.conn = store.connect(db_path)
        self.captains = {captain["captain_id"]: captain for captain in captains}
        self.reflection_provider = reflection_provider or reflection.build_default_reflection_provider()
        for captain_id, info in self.captains.items():
            identity.ensure_identity(self.conn, captain_id, info.get("role", ""))

    def close(self) -> None:
        self.conn.close()

    # -- internal helpers --------------------------------------------------

    def _recent_events(self, captain_id: str, limit: int = 50) -> list[dict]:
        rows = store.fetch_sql(
            self.conn,
            "events",
            "SELECT * FROM events WHERE captain_id = ? ORDER BY recorded_at DESC LIMIT ?",
            (captain_id, limit),
        )
        return list(reversed(rows))

    def _active_beliefs(self, captain_id: str) -> list[dict]:
        return [row for row in store.fetch_by(self.conn, "semantic_beliefs", captain_id=captain_id) if row["status"] == "active"]

    def _ingest(
        self,
        captain_id: str,
        *,
        kind: str,
        category: str,
        summary: str,
        occurred_at: str,
        observed_tick: Optional[int],
        who: Optional[list[str]],
        payload: Optional[dict],
        source: str,
        tags: Optional[list[str]] = None,
        interpretation: Optional[str] = None,
        certainty: float = 1.0,
        is_imported_history: bool = False,
        fleet: bool = False,
        references_episodic_id: Optional[str] = None,
    ) -> RecordResult:
        who = who or []
        payload = payload or {}
        event_shape = {
            "captain_id": captain_id,
            "kind": kind,
            "category": category,
            "summary": summary,
            "who": who,
            "payload": payload,
            "observed_tick": observed_tick,
            "is_imported_history": is_imported_history,
            "tags": tags or [],
        }
        recent = self._recent_events(captain_id)
        active_beliefs = self._active_beliefs(captain_id)
        score, factors = salience.score_event(event_shape, recent, active_beliefs)
        disposition = salience.disposition_for(score, factors)
        at = now()
        event_id = new_id("evt")
        scope_id = FLEET_SCOPE if fleet else captain_id

        # events.episodic_id and episodic_memories.source_event_id reference
        # each other, so neither insert can go first with both columns
        # populated. Insert the event row with episodic_id left null, insert
        # the episodic row referencing the now-real event_id, then backfill
        # the event row's episodic_id.
        store.insert(
            self.conn,
            "events",
            {
                "event_id": event_id,
                "captain_id": captain_id,
                "kind": kind,
                "category": category,
                "occurred_at": occurred_at,
                "observed_tick": observed_tick,
                "recorded_at": at,
                "who_json": who,
                "summary": summary,
                "payload_json": payload,
                "source": source,
                "salience_score": score,
                "salience_factors_json": factors,
                "disposition": disposition,
                "episodic_id": None,
            },
        )

        episodic_id = None
        if disposition != "discard":
            episodic_id = new_id("epi")
            evidence = [{"event_id": event_id}]
            if references_episodic_id:
                evidence.append({"episodic_id": references_episodic_id})
            store.insert(
                self.conn,
                "episodic_memories",
                {
                    "episodic_id": episodic_id,
                    "captain_id": scope_id,
                    "source_event_id": event_id,
                    "occurred_at": occurred_at,
                    "who_json": who,
                    "what": summary,
                    "outcome": payload.get("outcome"),
                    "evidence_json": evidence,
                    "certainty": certainty,
                    "interpretation": interpretation,
                    "interpretation_history_json": [],
                    "salience_score": score,
                    "strength": 0.3 if disposition == "summarize" else min(1.0, 0.5 + score),
                    "tags_json": tags or [],
                    "influenced_decisions_json": [],
                    "is_imported_history": int(is_imported_history),
                    "embedding_json": None,
                    "created_at": at,
                    "updated_at": at,
                },
            )
            store.update(self.conn, "events", event_id, {"episodic_id": episodic_id})

        reflection_triggered = False
        reflection_id = None
        if disposition == "episodic+reflect":
            reflection_reason = "conflicting-memories" if factors.get("conflict", 0) >= 0.7 else "high-salience-event"
            result = self.trigger_reflection(captain_id, reason=reflection_reason)
            reflection_triggered = True
            reflection_id = result["reflection_id"]

        return RecordResult(
            event_id=event_id,
            disposition=disposition,
            salience_score=score,
            episodic_id=episodic_id,
            reflection_triggered=reflection_triggered,
            reflection_id=reflection_id,
        )

    # -- public API ----------------------------------------------------------

    def record_event(
        self,
        captain_id: str,
        *,
        category: str,
        summary: str,
        occurred_at: str,
        observed_tick: Optional[int] = None,
        who: Optional[list[str]] = None,
        payload: Optional[dict] = None,
        source: str = "fleetcore-snapshot",
        tags: Optional[list[str]] = None,
        interpretation: Optional[str] = None,
        certainty: float = 1.0,
        is_imported_history: bool = False,
        fleet: bool = False,
        references_episodic_id: Optional[str] = None,
    ) -> dict[str, Any]:
        result = self._ingest(
            captain_id,
            kind="event",
            category=category,
            summary=summary,
            occurred_at=occurred_at,
            observed_tick=observed_tick,
            who=who,
            payload=payload,
            source=source,
            tags=tags,
            interpretation=interpretation,
            certainty=certainty,
            is_imported_history=is_imported_history,
            fleet=fleet,
            references_episodic_id=references_episodic_id,
        )
        return result.to_dict()

    def record_decision(self, captain_id: str, decision_record: dict, *, interpretation: Optional[str] = None) -> dict[str, Any]:
        captain_info = self.captains.get(captain_id, {})
        payload = dict(decision_record)
        payload.setdefault("captain_vessel_id", captain_info.get("vessel_id"))
        payload.setdefault("default_posture", captain_info.get("default_posture"))
        posture = decision_record.get("posture", "unknown")
        outcome = decision_record.get("outcome", "unknown")
        summary = f"Posture {posture} was {outcome}: {decision_record.get('result', '')}".strip()
        result = self._ingest(
            captain_id,
            kind="decision",
            category=f"decision-{posture}",
            summary=summary,
            occurred_at=decision_record.get("sim_time") or "",
            observed_tick=decision_record.get("observed_tick"),
            who=[captain_id],
            payload=payload,
            source="fleetcore-decision",
            tags=[posture],
            interpretation=interpretation,
        )
        return result.to_dict()

    def record_conversation(
        self,
        captain_id: str,
        *,
        with_id: str,
        occurred_at: str,
        transcript: str,
        summary: Optional[str] = None,
        payload: Optional[dict] = None,
    ) -> dict[str, Any]:
        merged_payload = dict(payload or {})
        merged_payload["transcript"] = transcript
        merged_payload["with_id"] = with_id
        source = "lieutenant-conversation" if with_id == "lieutenant.cgl" else "conversation"
        result = self._ingest(
            captain_id,
            kind="conversation",
            category="conversation",
            summary=summary or transcript.strip().splitlines()[0][:200] if transcript.strip() else "(empty transcript)",
            occurred_at=occurred_at,
            observed_tick=None,
            who=[captain_id, with_id],
            payload=merged_payload,
            source=source,
            tags=["conversation"],
        )
        return result.to_dict()

    def request_context(self, captain_id: str, *, purpose: str, subject: Optional[str] = None, max_items: int = 8) -> dict[str, Any]:
        return context_module.request_context(self.conn, captain_id, purpose=purpose, subject=subject, max_items=max_items)

    def request_relationship_context(self, captain_id: str, other_id: str) -> dict[str, Any]:
        return context_module.request_relationship_context(self.conn, captain_id, other_id)

    def trigger_reflection(self, captain_id: str, *, reason: str, period_start: Optional[str] = None, period_end: Optional[str] = None) -> dict[str, Any]:
        evidence = reflection.gather_reflection_evidence(self.conn, captain_id, period_start, period_end)
        try:
            content = self.reflection_provider.reflect(captain_id, reason, evidence)
            provider_name = self.reflection_provider.name
        except Exception:
            fallback = reflection.HeuristicReflectionProvider()
            content = fallback.reflect(captain_id, reason, evidence)
            provider_name = fallback.name
        return reflection.apply_reflection(
            self.conn,
            captain_id,
            reason=reason,
            content=content,
            provider_name=provider_name,
            evidence=evidence,
            period_start=period_start,
            period_end=period_end,
        )

    def inspect_memory(self, captain_id: str, *, table: Optional[str] = None, query: Optional[str] = None, limit: int = 50) -> list[dict]:
        tables = [table] if table else list(ID_COLUMNS.keys())
        results = []
        for table_name in tables:
            for row in store.fetch_by(self.conn, table_name, captain_id=captain_id):
                tagged = dict(row)
                tagged["_table"] = table_name
                if query:
                    haystack = " ".join(str(value) for value in row.values()).lower()
                    if query.lower() not in haystack:
                        continue
                results.append(tagged)
        results.sort(key=lambda row: row.get("updated_at") or row.get("created_at") or row.get("recorded_at") or 0, reverse=True)
        return results[:limit]

    def correct_or_retract(
        self,
        captain_id: str,
        *,
        target_table: str,
        target_id: str,
        action: str,
        reason: str,
        corrected_fields: Optional[dict] = None,
        requested_by: str = "operator",
    ) -> dict[str, Any]:
        before = store.fetch_one(self.conn, target_table, target_id)
        if target_table == "identity_traits" and action == "correct" and corrected_fields:
            after = identity.apply_correction(self.conn, captain_id, corrected_fields, reason)
        elif action == "retract":
            status_field = "status" if before and "status" in before else None
            if status_field:
                store.update(self.conn, target_table, target_id, {status_field: "retracted"})
            after = store.fetch_one(self.conn, target_table, target_id)
        elif action == "correct":
            store.update(self.conn, target_table, target_id, corrected_fields or {})
            after = store.fetch_one(self.conn, target_table, target_id)
        else:
            raise ValueError(f"unsupported correction action: {action!r}")

        store.insert(
            self.conn,
            "corrections",
            {
                "correction_id": new_id("cor"),
                "captain_id": captain_id,
                "target_table": target_table,
                "target_id": target_id,
                "action": action,
                "reason": reason,
                "before_json": before,
                "after_json": after,
                "requested_by": requested_by,
                "created_at": now(),
            },
        )
        return after
