"""Truth-preserving bridge from geometric language to IntentForge v0.0.

The bridge does not parse pixels or prose into dimensions. It produces a
translation proposal, carries unresolved requirements visibly, and compiles
only after a separate measurement-resolution record has been reviewed for an
allowed scope.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from design_intent import EdgeNotch, Envelope, FanMountBracketIntent, Hole


class IntentBridgeError(ValueError):
    """The source record cannot support a truthful translation proposal."""


class UnresolvedIntentError(IntentBridgeError):
    """Executable geometry was requested while requirements remain unresolved."""


REQUIRED_REFERENCES = {"Fan.Face:A", "Panel.Hole:1", "Panel.Hole:2"}
ALLOWED_REVIEW_STATES = {"approved-human", "approved-computational-test"}
PHYSICAL_FALSE_STATES = {
    "simulation_completed": False,
    "prototype_manufactured": False,
    "prototype_tested": False,
    "externally_reviewed": False,
    "validated_for_use": False,
}


@dataclass
class TranslationProposal:
    schema_version: str
    source_episode_id: str
    source_coordinate_space: str | None
    source_entry: dict[str, Any]
    mappings: list[dict[str, Any]] = field(default_factory=list)
    unresolved: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    resolved: dict[str, Any] | None = None
    review_decision: dict[str, Any] | None = None

    @property
    def ready_to_compile(self) -> bool:
        return not self.unresolved and self.resolved is not None and self.review_decision is not None

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "source_episode_id": self.source_episode_id,
            "source_coordinate_space": self.source_coordinate_space,
            "coordinate_boundary": (
                "Source gesture samples are provenance in their declared coordinate space. "
                "They are never interpreted as physical dimensions."
            ),
            "mappings": self.mappings,
            "unresolved": self.unresolved,
            "warnings": self.warnings,
            "review_decision": self.review_decision,
            "ready_to_compile": self.ready_to_compile,
        }


@dataclass
class CompiledIntent:
    intent: FanMountBracketIntent
    feature_trace: list[dict[str, Any]]
    source_episode_id: str
    review_decision: dict[str, Any]
    truth_boundary: dict[str, bool]


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise IntentBridgeError(message)


def _first_entry(export: dict[str, Any]) -> dict[str, Any]:
    _require(export.get("schema_version") == "monad.intentLexiconExport.v0.1", "unsupported lexicon export schema")
    entries = export.get("entries")
    _require(isinstance(entries, list) and len(entries) == 1, "v0.1 requires exactly one lexicon entry")
    entry = entries[0]
    _require(entry.get("schema_version") == "monad.intentLexiconEntry.v0.1", "unsupported lexicon entry schema")
    return entry


def _validate_source(entry: dict[str, Any]) -> dict[str, Any]:
    episode = entry.get("source_episode")
    _require(isinstance(episode, dict), "lexicon entry must embed its complete source episode")
    _require(episode.get("schema_version") == "monad.geometricTeachingEpisode.v0.1", "unsupported teaching episode schema")
    _require(episode.get("id") == entry.get("source_episode_id"), "source episode identifier mismatch")
    _require(episode.get("epistemic_status") == "reviewed-provisional", "teaching episode is not reviewed-provisional")
    review = episode.get("human_review", {})
    _require(review.get("reviewed") is True, "teaching episode lacks explicit human review")
    _require(review.get("universal_claim") is False, "private meaning must not be marked universal")
    references = episode.get("explicit_references")
    _require(isinstance(references, list), "teaching episode references must be a list")
    ref_names = {item.get("ref") for item in references}
    _require(REQUIRED_REFERENCES <= ref_names, "teaching episode lacks required fan or panel references")
    sacred = {item.get("ref") for item in references if item.get("sacred") is True}
    _require(REQUIRED_REFERENCES <= sacred, "required fan and panel references must be explicitly sacred")
    gesture = episode.get("gesture")
    _require(isinstance(gesture, dict) and gesture.get("type") == "keep-out", "a typed keep-out gesture is required")
    _require(len(gesture.get("samples", [])) >= 2, "keep-out gesture requires at least two samples")
    return episode


def _unresolved_requirements() -> list[str]:
    return [
        "physical units",
        "envelope width, height, and thickness",
        "Panel.Hole:1 physical position and diameter",
        "Panel.Hole:2 physical position and diameter",
        "Fan.Face:A physical center, bolt spacing, bolt diameter, and airflow diameter",
        "keep-out physical representation and dimensions",
        "minimum wall thickness and manufacturing assumptions",
        "private phrase disposition for the current generator",
        "translation review decision and scope",
    ]


def propose_fan_bracket_translation(
    export: dict[str, Any],
    resolution: dict[str, Any] | None = None,
) -> TranslationProposal:
    entry = _first_entry(export)
    episode = _validate_source(entry)
    gesture = episode["gesture"]
    proposal = TranslationProposal(
        schema_version="intentforge.intentTranslationProposal.v0.1",
        source_episode_id=episode["id"],
        source_coordinate_space=gesture.get("coordinate_space"),
        source_entry=entry,
        mappings=[
            {
                "source": ["Panel.Hole:1", "Panel.Hole:2"],
                "target": "FanMountBracketIntent.existing_holes",
                "status": "identity-known-dimensions-unresolved",
            },
            {
                "source": ["Fan.Face:A"],
                "target": "fan_center / fan bolt pattern / airflow opening",
                "status": "identity-known-dimensions-unresolved",
            },
            {
                "source": ["gesture:keep-out"],
                "target": "FanMountBracketIntent.cable_notch",
                "status": "intent-known-physical-representation-unresolved",
            },
            {
                "source": [f"lexicon:{entry.get('phrase')}@v{entry.get('version')}"],
                "target": "no supported IntentForge v0.0 field",
                "status": "disposition-required",
            },
        ],
        warnings=[
            "The demo-stage gesture coordinate space is non-physical and cannot supply millimetres.",
            "A reviewed private phrase remains contextual and does not become a generator parameter without a typed supported mapping.",
        ],
    )
    if resolution is None:
        proposal.unresolved = _unresolved_requirements()
        return proposal

    proposal.resolved = _validate_resolution(entry, episode, resolution)
    proposal.review_decision = resolution["review_decision"]
    proposal.mappings = _resolved_mappings(entry, resolution)
    return proposal


def _positive_number(value: Any, field_name: str) -> float:
    _require(isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0, f"{field_name} must be positive")
    return float(value)


def _number(value: Any, field_name: str) -> float:
    _require(isinstance(value, (int, float)) and not isinstance(value, bool), f"{field_name} must be numeric")
    return float(value)


def _validate_resolution(
    entry: dict[str, Any],
    episode: dict[str, Any],
    resolution: dict[str, Any],
) -> dict[str, Any]:
    _require(
        resolution.get("schema_version") == "intentforge.measurementResolution.v0.1",
        "unsupported measurement-resolution schema",
    )
    _require(resolution.get("source_episode_id") == episode.get("id"), "measurement source episode mismatch")
    _require(resolution.get("units") == "mm", "IntentForge v0.0 requires explicit millimetre units")
    envelope = resolution.get("envelope", {})
    for key in ("width", "height", "thickness"):
        _positive_number(envelope.get(key), f"envelope.{key}")

    holes = resolution.get("panel_holes")
    _require(isinstance(holes, list) and len(holes) == 2, "exactly two resolved panel holes are required")
    hole_refs = {hole.get("source_ref") for hole in holes}
    _require(hole_refs == {"Panel.Hole:1", "Panel.Hole:2"}, "resolved panel-hole references do not match source")
    for hole in holes:
        _number(hole.get("cx"), f"{hole.get('source_ref')}.cx")
        _number(hole.get("cy"), f"{hole.get('source_ref')}.cy")
        _positive_number(hole.get("diameter"), f"{hole.get('source_ref')}.diameter")
        _require(bool(hole.get("purpose")), f"{hole.get('source_ref')}.purpose is required")

    fan = resolution.get("fan_interface", {})
    _require(fan.get("source_ref") == "Fan.Face:A", "fan-interface reference does not match source")
    center = fan.get("center")
    _require(isinstance(center, list) and len(center) == 2, "fan center requires two millimetre coordinates")
    _number(center[0], "fan_interface.center[0]")
    _number(center[1], "fan_interface.center[1]")
    for key in ("bolt_spacing", "bolt_diameter", "airflow_diameter"):
        _positive_number(fan.get(key), f"fan_interface.{key}")

    keep_out = resolution.get("keep_out", {})
    _require(keep_out.get("source_gesture_type") == episode["gesture"]["type"], "keep-out source gesture mismatch")
    _require(keep_out.get("representation") == "edge-notch", "v0.1 supports only an explicit edge-notch resolution")
    _require(keep_out.get("edge") in {"north", "south", "east", "west"}, "keep-out edge is invalid")
    _number(keep_out.get("center_offset"), "keep_out.center_offset")
    _positive_number(keep_out.get("width"), "keep_out.width")
    _positive_number(keep_out.get("depth"), "keep_out.depth")
    _require(bool(keep_out.get("purpose")), "keep_out.purpose is required")

    manufacturing = resolution.get("manufacturing", {})
    _positive_number(manufacturing.get("min_wall_thickness"), "manufacturing.min_wall_thickness")
    _require(bool(manufacturing.get("process")), "manufacturing.process is required")

    dispositions = resolution.get("private_meaning_dispositions")
    _require(isinstance(dispositions, list) and len(dispositions) == 1, "exactly one private-meaning disposition is required")
    disposition = dispositions[0]
    _require(disposition.get("phrase") == entry.get("phrase"), "private-meaning phrase mismatch")
    _require(disposition.get("version") == entry.get("version"), "private-meaning version mismatch")
    _require(
        disposition.get("disposition") == "unsupported-not-applicable",
        "IntentForge v0.0 cannot consume the private fit phrase as a numeric field",
    )
    _require(bool(disposition.get("reason")), "private-meaning disposition reason is required")

    decision = resolution.get("review_decision", {})
    _require(decision.get("state") in ALLOWED_REVIEW_STATES, "translation lacks an allowed review decision")
    _require(bool(decision.get("actor")), "translation review actor is required")
    if decision.get("state") == "approved-computational-test":
        _require(decision.get("scope") == "computational-only", "test-fixture approval must remain computational-only")
        _require(decision.get("physical_authority") is False, "test-fixture approval cannot claim physical authority")
    return resolution


def _resolved_mappings(entry: dict[str, Any], resolution: dict[str, Any]) -> list[dict[str, Any]]:
    mappings: list[dict[str, Any]] = []
    for hole in resolution["panel_holes"]:
        mappings.append(
            {
                "source": hole["source_ref"],
                "target": "FanMountBracketIntent.existing_holes",
                "value_source": "measurement-resolution",
                "units": "mm",
                "sacred": True,
                "status": "resolved",
            }
        )
    mappings.extend(
        [
            {
                "source": "Fan.Face:A",
                "target": "fan interface fields",
                "value_source": "measurement-resolution",
                "units": "mm",
                "sacred": True,
                "status": "resolved",
            },
            {
                "source": "gesture:keep-out",
                "target": "cable_notch",
                "value_source": "measurement-resolution; gesture retained as intent provenance only",
                "units": "mm",
                "status": "resolved",
            },
            {
                "source": f"lexicon:{entry['phrase']}@v{entry['version']}",
                "target": None,
                "status": "preserved-unsupported-not-applicable",
                "reason": resolution["private_meaning_dispositions"][0]["reason"],
            },
        ]
    )
    return mappings


def compile_fan_mount_intent(proposal: TranslationProposal) -> CompiledIntent:
    if not proposal.ready_to_compile:
        detail = "; ".join(proposal.unresolved) if proposal.unresolved else "resolution or review is absent"
        raise UnresolvedIntentError(f"translation proposal is not executable: {detail}")
    resolved = proposal.resolved
    assert resolved is not None
    envelope_data = resolved["envelope"]
    fan = resolved["fan_interface"]
    keep_out = resolved["keep_out"]
    manufacturing = resolved["manufacturing"]
    holes = [
        Hole(
            cx=float(item["cx"]),
            cy=float(item["cy"]),
            diameter=float(item["diameter"]),
            purpose=item["purpose"],
        )
        for item in resolved["panel_holes"]
    ]
    assumptions = list(resolved.get("assumptions", []))
    assumptions.extend(
        [
            "translation source is a reviewed-provisional teaching episode",
            "demo-stage gesture samples were preserved as provenance and not converted into physical dimensions",
            "private phrase was explicitly preserved as unsupported/not applicable to the v0.0 generator",
            f"translation authorized only for scope: {proposal.review_decision['scope']}",
        ]
    )
    intent = FanMountBracketIntent(
        purpose=proposal.source_entry["source_episode"]["expression"]["words"],
        envelope=Envelope(
            width=float(envelope_data["width"]),
            height=float(envelope_data["height"]),
            thickness=float(envelope_data["thickness"]),
        ),
        existing_holes=holes,
        fan_center=(float(fan["center"][0]), float(fan["center"][1])),
        fan_bolt_spacing=float(fan["bolt_spacing"]),
        fan_bolt_diameter=float(fan["bolt_diameter"]),
        fan_airflow_diameter=float(fan["airflow_diameter"]),
        cable_notch=EdgeNotch(
            edge=keep_out["edge"],
            center_offset=float(keep_out["center_offset"]),
            width=float(keep_out["width"]),
            depth=float(keep_out["depth"]),
            purpose=keep_out["purpose"],
        ),
        min_wall_thickness=float(manufacturing["min_wall_thickness"]),
        acceptance_criteria=list(resolved.get("acceptance_criteria", [])),
        assumptions=assumptions,
    )
    trace = _feature_trace(proposal, resolved)
    return CompiledIntent(
        intent=intent,
        feature_trace=trace,
        source_episode_id=proposal.source_episode_id,
        review_decision=dict(proposal.review_decision),
        truth_boundary=dict(PHYSICAL_FALSE_STATES),
    )


def _feature_trace(proposal: TranslationProposal, resolution: dict[str, Any]) -> list[dict[str, Any]]:
    entry = proposal.source_entry
    return [
        {
            "feature": "outer plate envelope",
            "intent_source": entry["source_episode"]["expression"]["words"],
            "value_source": "measurement-resolution.envelope",
        },
        *[
            {
                "feature": f"existing mounting hole {index + 1}",
                "intent_source": item["source_ref"],
                "value_source": f"measurement-resolution.panel_holes[{index}]",
                "sacred": True,
            }
            for index, item in enumerate(resolution["panel_holes"])
        ],
        {
            "feature": "fan bolt pattern and airflow opening",
            "intent_source": "Fan.Face:A + PRESERVE_REGION relation",
            "value_source": "measurement-resolution.fan_interface",
            "sacred": True,
        },
        {
            "feature": "cable-clearance edge notch",
            "intent_source": f"{proposal.source_episode_id}:gesture:keep-out",
            "value_source": "measurement-resolution.keep_out",
            "source_samples_are_dimensions": False,
        },
        {
            "feature": "minimum wall thickness",
            "intent_source": "manufacturing assumption",
            "value_source": "measurement-resolution.manufacturing.min_wall_thickness",
        },
        {
            "feature": "private phrase disposition",
            "intent_source": f"{entry['phrase']}@v{entry['version']}",
            "value_source": "measurement-resolution.private_meaning_dispositions",
            "generator_effect": "none",
        },
    ]
