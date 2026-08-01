"""Research-arc data layer for Root Console Phase 1A (the CAP-ARI cockpit).

Two kinds of record, never blurred:

  - Real packets (CAP-ARI-001, CAP-ARI-002, CAP-ARI-003): parsed straight
    from the canonical archive at
    admiralty/archive/research/autonomous-inquiry/. No Captain
    research-execution backend exists yet, so these always report their
    real archived status (AUTHORIZED_NOT_STARTED) and an empty
    generation history. Commands against them are refused with a clear
    reason instead of being faked into "running."

  - One demonstration arc (CAP-ARI-003-DEMO): a deterministic, in-memory
    step machine used to commission this UI end-to-end, per the packet's
    Section 10 "DETERMINISTIC DEMONSTRATION -- NOT AN EXPERIMENTAL
    RESULT." It walks the same first-test question CAP-ARI-003 assigns
    (Section 6 of that packet), but is deliberately kept at a *separate*
    record id from the real CAP-ARI-003 archive entry -- an earlier
    version of this module reused the bare "CAP-ARI-003" id for the
    mock, which silently shadowed the real canonical packet once one was
    logged to the archive (2026-08-01, via Monad's existing intake
    pipeline, not this daemon). Never collide a mock id with a real one.
    Every record this arc produces is tagged dataMode MOCK (command-
    driven walkthrough) or REPLAY (fixed canned sequence), never LIVE.
    State resets when this process restarts -- it is commissioning data,
    not a persisted experiment record.
"""

from __future__ import annotations

import re
import threading
import time
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ARCHIVE_DIR = REPO_ROOT / "admiralty" / "archive" / "research" / "autonomous-inquiry"

REAL_PACKET_IDS = ["CAP-ARI-001", "CAP-ARI-002", "CAP-ARI-003"]
DEMO_ARC_ID = "CAP-ARI-003-DEMO"
CANONICAL_IDS = ["CAP-ARI-001", "CAP-ARI-002", "CAP-ARI-003"]


class ResearchError(ValueError):
    """A rejected command or lookup -- always safe to show verbatim to the operator."""


def _parse_frontmatter(text: str) -> dict:
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        return {}
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()
    return fields


def _load_real_packet(packet_id: str) -> dict | None:
    path = ARCHIVE_DIR / f"{packet_id}.md"
    if not path.is_file():
        return None
    fields = _parse_frontmatter(path.read_text(encoding="utf-8"))
    return {
        "researchArcId": fields.get("id", packet_id),
        "title": fields.get("title", packet_id),
        "status": fields.get("status", "AUTHORIZED_NOT_STARTED"),
        "primaryQuestion": fields.get("research_question", ""),
        "foundingAssumptions": [],
        "vulnerableClaims": [],
        "permittedActions": [fields["permitted_autonomous_scope"]] if fields.get("permitted_autonomous_scope") else [],
        "prohibitedActions": [fields["prohibited_actions"]] if fields.get("prohibited_actions") else [],
        "generationLimit": 0,
        "currentGeneration": 0,
        "runBudget": 0,
        "runsUsed": 0,
        "stopConditions": [fields["natural_stopping_conditions"]] if fields.get("natural_stopping_conditions") else [],
        "escalationConditions": [],
        "leadingHypothesis": None,
        "strongestAlternative": None,
        "unresolvedQuestion": None,
        "activeExperiment": None,
        "recentGenerations": [],
        "captainAssessment": None,
        "dataMode": "LIVE",
        "sourcePath": str(path.relative_to(REPO_ROOT)),
        "canonical": True,
        "notStartedReason": "No Captain research-execution backend is wired up yet -- this packet is authorized but has not been run. Commands are disabled for real packets in Phase 1A.",
    }


def list_packets() -> dict:
    packets = []
    present_ids = set()
    for packet_id in REAL_PACKET_IDS:
        record = _load_real_packet(packet_id)
        if record:
            packets.append(record)
            present_ids.add(packet_id)
    demo = DEMO_ARC.snapshot()
    demo["canonical"] = False
    demo["relatedCanonicalId"] = "CAP-ARI-003" if "CAP-ARI-003" in present_ids else None
    packets.append(demo)
    # Report any canonical id that was expected (per the engineering packet)
    # but has no archive record yet -- never silently invent it.
    missing_canonical = [cid for cid in CANONICAL_IDS if cid not in present_ids]
    return {"packets": packets, "missingCanonicalIds": missing_canonical}


def get_arc(arc_id: str) -> dict:
    if arc_id == DEMO_ARC_ID:
        return DEMO_ARC.snapshot()
    record = _load_real_packet(arc_id)
    if not record:
        raise ResearchError(f"unknown research packet: {arc_id}")
    return record


def get_events(arc_id: str) -> list[dict]:
    if arc_id == DEMO_ARC_ID:
        return DEMO_ARC.events()
    record = _load_real_packet(arc_id)
    if not record:
        raise ResearchError(f"unknown research packet: {arc_id}")
    return []


def get_replay(arc_id: str) -> list[dict]:
    if arc_id != DEMO_ARC_ID:
        raise ResearchError("deterministic replay is only available for the CAP-ARI-003 demonstration arc")
    return _replay_frames()


def run_command(arc_id: str, command: str) -> dict:
    if arc_id != DEMO_ARC_ID:
        raise ResearchError(
            "no Captain research-execution backend is wired up for real packets yet -- "
            f"{arc_id} cannot be started, paused, or stopped from Phase 1A"
        )
    return DEMO_ARC.command(command)


# ---------------------------------------------------------------------------
# Deterministic demonstration arc (CAP-ARI-003)
# ---------------------------------------------------------------------------

PRIMARY_QUESTION = (
    "Does increasing self-model causal authority improve recovery from a hidden "
    "internal mechanism shift, and is any observed advantage distinct from "
    "ordinary policy adaptation?"
)


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _event(event_type: str, summary: str, **refs) -> dict:
    return {
        "eventId": uuid.uuid4().hex[:12],
        "timestamp": _now(),
        "type": event_type,
        "summary": summary,
        "refs": refs,
    }


class _DemoArc:
    """Command-driven step machine for CAP-ARI-003 -- see module docstring."""

    def __init__(self):
        self._lock = threading.RLock()
        self._reset()

    def _reset(self):
        self.step = 0
        self.paused = False
        self.stopped = False
        self.returned = False
        self.event_log: list[dict] = [
            _event("research_arc_started", f"{DEMO_ARC_ID} loaded. Awaiting Admiral authorization to start.", researchArcId=DEMO_ARC_ID)
        ]
        self.generations: list[dict] = []
        self.leading_hypothesis = None
        self.strongest_alternative = None
        self.unresolved_question = None
        self.active_experiment = None
        self.assessment = None
        self.runs_used = 0

    def snapshot(self) -> dict:
        with self._lock:
            if self.stopped:
                status = "TERMINATED"
            elif self.returned:
                status = "AWAITING_ADMIRAL"
            elif self.paused:
                status = "PAUSED"
            elif self.step == 0:
                status = "AUTHORIZED_NOT_STARTED"
            elif self.step == 1:
                status = "READY"
            elif self.step in (2, 3, 4, 5):
                status = "RUNNING"
            else:
                status = "AWAITING_ADMIRAL"
            return {
                "researchArcId": DEMO_ARC_ID,
                "title": "Bounded Automated Science Loop (Phase 1A demo)",
                "status": status,
                "primaryQuestion": PRIMARY_QUESTION,
                "foundingAssumptions": [
                    "Recovery from a hidden internal mechanism shift is measurable within the existing Monad-0 organism harness.",
                ],
                "vulnerableClaims": [
                    "Any observed recovery advantage is caused by self-modeling rather than ordinary policy adaptation.",
                ],
                "permittedActions": [
                    "Design and run matched-condition experiments, compare integrated vs. ablated self-model conditions, revise hypotheses across generations, continue to a natural stopping point.",
                ],
                "prohibitedActions": [
                    "Declare a closure claim from a single pilot; modify Monad-0 experiment logic; make LLM calls inside the research organism; continue past budget without Admiral review.",
                ],
                "generationLimit": 5,
                "currentGeneration": len(self.generations),
                "runBudget": 50,
                "runsUsed": self.runs_used,
                "stopConditions": [
                    "Recovery-advantage result is ambiguous across two generations.",
                    "Generation or run budget exhausted.",
                    "Evidence is sufficient to recommend a larger pilot.",
                ],
                "escalationConditions": [
                    "Unexpected divergence between integrated and ablated conditions beyond modeled variance.",
                ],
                "leadingHypothesis": self.leading_hypothesis,
                "strongestAlternative": self.strongest_alternative,
                "unresolvedQuestion": self.unresolved_question,
                "activeExperiment": self.active_experiment,
                "recentGenerations": list(self.generations),
                "captainAssessment": self.assessment,
                "dataMode": "MOCK",
                "sourcePath": None,
                "canonical": False,
                "notStartedReason": None if self.step > 0 else "Awaiting Admiral authorization (Start authorized arc).",
            }

    def events(self) -> list[dict]:
        with self._lock:
            return list(self.event_log)

    def command(self, command: str) -> dict:
        with self._lock:
            handler = {
                "start": self._start,
                "pause": self._pause,
                "resume": self._resume,
                "stop": self._stop,
                "return_control": self._return_control,
                "approve_next_experiment": self._advance,
                "request_summary": self._request_summary,
                "export_packet": self._export_packet,
            }.get(command)
            if handler is None:
                raise ResearchError(f"unknown command: {command}")
            return handler()

    def _guard_active(self):
        if self.stopped:
            raise ResearchError("arc is terminated; nothing further can run")

    def _start(self) -> dict:
        self._guard_active()
        if self.step != 0:
            raise ResearchError("arc already started")
        self._advance_to(1)
        self._advance_to(2)
        return {"ok": True, "status": self.snapshot()["status"]}

    def _pause(self) -> dict:
        self._guard_active()
        if self.step == 0:
            raise ResearchError("arc has not started yet")
        if self.paused:
            raise ResearchError("arc is already paused")
        self.paused = True
        self.event_log.append(_event("admiral_review_requested", "Paused after current safe step by Admiral command."))
        return {"ok": True, "status": "PAUSED"}

    def _resume(self) -> dict:
        self._guard_active()
        if not self.paused:
            raise ResearchError("arc is not paused")
        self.paused = False
        self.event_log.append(_event("research_arc_started", "Resumed by Admiral command."))
        return {"ok": True, "status": self.snapshot()["status"]}

    def _stop(self) -> dict:
        if self.stopped:
            raise ResearchError("arc is already terminated")
        self.stopped = True
        self.event_log.append(_event("stopping_condition_reached", "Arc stopped by Admiral command."))
        return {"ok": True, "status": "TERMINATED"}

    def _return_control(self) -> dict:
        self._guard_active()
        self.paused = False
        self.returned = True
        self.event_log.append(_event("admiral_review_requested", "Control returned to Admiral by command."))
        return {"ok": True, "status": "AWAITING_ADMIRAL"}

    def _advance(self) -> dict:
        self._guard_active()
        if self.paused:
            raise ResearchError("arc is paused; resume before advancing")
        if self.step == 0:
            raise ResearchError("arc has not started yet")
        if self.step >= 6:
            raise ResearchError("no further experiments; arc is awaiting Admiral review")
        self._advance_to(self.step + 1)
        return {"ok": True, "status": self.snapshot()["status"]}

    def _request_summary(self) -> dict:
        if self.assessment:
            return self.assessment
        if not self.generations:
            return {
                "observation": "No generations have completed yet.",
                "interpretation": "Insufficient evidence for an assessment.",
                "confidence": "LOW",
                "alternative": "N/A",
                "evidenceRefs": [],
                "recommendedAction": "Start the arc and run at least one generation.",
            }
        latest = self.generations[-1]
        return {
            "observation": latest["result"],
            "interpretation": latest["interpretation"],
            "confidence": latest["confidence"],
            "alternative": latest["strongestAlternative"],
            "evidenceRefs": [g["generationId"] for g in self.generations],
            "recommendedAction": "Continue to the next generation." if self.step < 6 else "Awaiting Admiral decision.",
        }

    def _export_packet(self) -> dict:
        snapshot = self.snapshot()
        return {
            "researchArcId": DEMO_ARC_ID,
            "exportedAt": _now(),
            "atNaturalStoppingPoint": self.step >= 6,
            "status": snapshot["status"],
            "primaryQuestion": PRIMARY_QUESTION,
            "generations": snapshot["recentGenerations"],
            "leadingHypothesis": snapshot["leadingHypothesis"],
            "strongestAlternative": snapshot["strongestAlternative"],
            "unresolvedQuestion": snapshot["unresolvedQuestion"],
            "captainAssessment": snapshot["captainAssessment"],
            "recommendation": (
                "Run a larger pilot with additional seeds before treating this as a closure claim."
                if self.step >= 6
                else "Arc has not reached a natural stopping point; export is interim."
            ),
            "dataMode": "MOCK",
        }

    def _advance_to(self, step: int) -> None:
        if step == 1:
            self.event_log.append(_event("research_arc_started", "Arc authorized and initialized by Admiral; Captain beginning inquiry."))
        elif step == 2:
            self.active_experiment = {
                "experimentId": "CAP-ARI-003-G1-E1",
                "title": "Integrated vs. decorative self-model recovery",
                "status": "RUNNING",
                "purpose": "Compare recovery speed after a hidden internal mechanism shift between integrated and decorative self-model conditions.",
                "condition": "integrated self-model (causally active)",
                "control": "decorative self-model (non-causal)",
                "seed": 1001,
                "progress": 0,
                "startedAt": _now(),
            }
            self.event_log.append(_event("generation_created", "Generation 1: compare integrated vs. decorative self-model conditions.", generationId="G1"))
            self.event_log.append(_event("experiment_launched", "Experiment CAP-ARI-003-G1-E1 launched.", experimentId="CAP-ARI-003-G1-E1"))
        elif step == 3:
            self.active_experiment = {**self.active_experiment, "status": "COMPLETE", "progress": 100}
            self.runs_used += 7
            self.leading_hypothesis = "Integrated self-model improves recovery after a hidden internal mechanism shift."
            self.strongest_alternative = "The advantage is fully explained by ordinary policy adaptation, not causal self-modeling."
            self.generations.append({
                "generationId": "G1",
                "parentGenerationId": None,
                "question": PRIMARY_QUESTION,
                "hypothesis": self.leading_hypothesis,
                "strongestAlternative": self.strongest_alternative,
                "experiment": "CAP-ARI-003-G1-E1",
                "result": "Integrated organism recovered faster than the decorative-mirror control.",
                "interpretation": "Evidence is consistent with a causal self-model benefit, but direct policy adaptation remains a plausible confound.",
                "confidence": "LOW",
                "decision": "Run a second generation isolating causal influence from policy-update capacity.",
                "createdAt": _now(),
            })
            self.active_experiment = None
            self.event_log.append(_event("run_completed", "Generation 1 runs complete.", generationId="G1"))
            self.event_log.append(_event("control_compared", "Control comparison complete: recovery advantage observed, but confound not yet ruled out.", generationId="G1"))
        elif step == 4:
            self.active_experiment = {
                "experimentId": "CAP-ARI-003-G2-E1",
                "title": "Causal self-model ablation",
                "status": "RUNNING",
                "purpose": "Disable causal self-model influence while retaining equivalent policy-update capacity, isolating the Generation 1 confound.",
                "condition": "self-model causally disabled, policy-update capacity preserved",
                "control": "Generation 1 integrated condition",
                "seed": 1002,
                "progress": 0,
                "startedAt": _now(),
            }
            self.event_log.append(_event("generation_created", "Generation 2: disable causal self-model influence while retaining equivalent policy-update capacity.", generationId="G2"))
            self.event_log.append(_event("experiment_launched", "Experiment CAP-ARI-003-G2-E1 launched.", experimentId="CAP-ARI-003-G2-E1"))
        elif step == 5:
            self.active_experiment = {**self.active_experiment, "status": "COMPLETE", "progress": 100}
            self.runs_used += 7
            self.leading_hypothesis = "Causally active self-modeling contributes to recovery beyond ordinary policy adaptation."
            self.strongest_alternative = "The remaining advantage could still reflect an unmodeled capacity difference between conditions, not self-modeling per se."
            self.unresolved_question = "Does the effect replicate with a larger pilot and additional seeds, and does it hold under a stricter ablation of policy-update capacity?"
            self.generations.append({
                "generationId": "G2",
                "parentGenerationId": "G1",
                "question": PRIMARY_QUESTION,
                "hypothesis": self.leading_hypothesis,
                "strongestAlternative": self.strongest_alternative,
                "experiment": "CAP-ARI-003-G2-E1",
                "result": "Recovery advantage disappeared when causal self-model influence was disabled.",
                "interpretation": "Supports a role for causally active self-modeling distinct from ordinary policy adaptation, but the sample size is insufficient for a closure claim.",
                "confidence": "MEDIUM",
                "decision": "Stop and return to Admiral -- next step requires a larger pilot with additional seeds.",
                "createdAt": _now(),
            })
            self.active_experiment = None
            self.event_log.append(_event("run_completed", "Generation 2 runs complete.", generationId="G2"))
            self.event_log.append(_event("hypothesis_strengthened", "Recovery advantage disappears under ablation -- strengthens the causal self-model hypothesis over the policy-adaptation alternative.", generationId="G2"))
        elif step == 6:
            self.returned = True
            self.assessment = {
                "observation": "Recovery advantage present under the integrated self-model condition, absent under causal ablation with equivalent policy-update capacity.",
                "interpretation": "Causally active self-modeling appears to contribute to recovery from a hidden internal mechanism shift, distinct from ordinary policy adaptation.",
                "confidence": "MEDIUM",
                "alternative": "An unmodeled capacity difference between conditions, rather than self-modeling per se, could still account for the result.",
                "evidenceRefs": ["G1", "G2", "CAP-ARI-003-G1-E1", "CAP-ARI-003-G2-E1"],
                "recommendedAction": "Run a larger pilot with additional seeds before treating this as a closure claim.",
            }
            self.event_log.append(_event("stopping_condition_reached", "Natural stopping point reached: next step requires a larger pilot and additional seeds."))
            self.event_log.append(_event("admiral_review_requested", "Captain requests Admiral review before further generations."))
        self.step = step


DEMO_ARC = _DemoArc()

_replay_frames_cache: list[dict] | None = None


def _replay_frames() -> list[dict]:
    """(event, arcSnapshotAfterEvent) pairs for Mode 2 deterministic replay.

    Built by stepping a *fresh, throwaway* _DemoArc through the identical
    script the command rail uses (via the same _advance_to transitions),
    so replay can never drift from what "Start" + "Approve next
    experiment" actually produce in Mode 1/command-driven MOCK use. This
    instance is never the shared DEMO_ARC singleton and is discarded
    after building the frame list -- replaying never touches live command
    state.
    """
    global _replay_frames_cache
    if _replay_frames_cache is not None:
        return _replay_frames_cache
    arc = _DemoArc()
    frames = [{"event": e, "arc": arc.snapshot()} for e in arc.event_log]
    for step in range(1, 7):
        before = len(arc.event_log)
        arc._advance_to(step)  # noqa: SLF001 -- intentional reuse of the same module's step machine, not an external privacy violation
        for e in arc.event_log[before:]:
            frame = dict(e)
            snapshot = arc.snapshot()
            frames.append({"event": frame, "arc": snapshot})
    _replay_frames_cache = frames
    return frames
