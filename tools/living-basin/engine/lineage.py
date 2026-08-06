"""Deterministic, template-based causal-lineage summaries.

No LLM and no free text generation: every line is produced by filling a
fixed template with values pulled directly from a stored Event's `inputs` /
`result` fields. If a value isn't in the event record, it cannot appear in
the summary.
"""

from __future__ import annotations

_NODE_LABELS = {
    "rain_started": "Weather Node",
    "saturation_exceeded": "Hydrology Node",
    "root_loss": "Flora Node",
    "cohesion_degraded": "Soil Node",
    "trail_formed": "Herbivore Node",
    "grazed_patch_formed": "Herbivore Node",
    "pool_formed": "Hydrology Node",
    "gully_formed": "Erosion Node",
    "override_applied": "Authored Override",
}


def _line(event) -> str:
    label = _NODE_LABELS.get(event.event_type, "Node")
    i = event.inputs
    if event.event_type == "rain_started":
        text = f"Rainfall began at {i.get('rainfall_mm_per_hour')}mm/hr for {i.get('duration_ticks')} ticks"
    elif event.event_type == "saturation_exceeded":
        text = f"Local saturation exceeded {round(i.get('soil_saturation', 0) * 100)}%"
    elif event.event_type == "root_loss":
        text = f"Root density fell to {i.get('root_density')}"
    elif event.event_type == "cohesion_degraded":
        text = f"Organic cohesion degraded to {i.get('soil_cohesion')}"
    elif event.event_type == "trail_formed":
        text = f"Trail intensity reached {i.get('trail_intensity')} from repeated passage"
    elif event.event_type == "grazed_patch_formed":
        text = f"Grazing pressure reached {i.get('grazing_pressure')}"
    elif event.event_type == "pool_formed":
        text = f"Standing water reached {i.get('surface_water')}mm and persisted"
    elif event.event_type == "gully_formed":
        text = (
            f"Erosion depth reached {i.get('erosion_depth')} "
            f"(runoff {i.get('runoff')}, cohesion {i.get('soil_cohesion')}, "
            f"slope {i.get('local_slope')})"
        )
    elif event.event_type == "override_applied":
        text = f"Field '{i.get('field')}' set to {event.result.get('after')} by {i.get('actor')}: {i.get('reason')}"
    else:
        text = event.event_type
    return f"{label}: {text}"


def build_lineage_lines(event_log, event_id: str) -> list[str]:
    """Returns the ordered, numbered lineage lines for a feature's genesis
    (or any) event, oldest cause first, ending with the event itself."""
    chain = event_log.lineage(event_id)
    lines = []
    for idx, evt in enumerate(chain, start=1):
        lines.append(f"{idx}. {_line(evt)}")
    return lines


def diagnostic_card(event_log, feature) -> dict:
    """Assembles the full diagnostic-card payload for a feature: every
    displayed field is either copied from the Feature record or derived by
    walking `causal_event_ids` through the EventLog -- nothing here is
    computed from current world state directly.
    """
    genesis_id = feature.causal_event_ids[0]
    genesis_evt = event_log.get(genesis_id)
    lineage_lines = build_lineage_lines(event_log, genesis_id)

    has_override = feature.authored_override or any(
        event_log.get(eid) and event_log.get(eid).authored_override
        for eid in feature.causal_event_ids
    )

    return {
        "feature_id": feature.feature_id,
        "feature_type": feature.feature_type,
        "cells": feature.cells,
        "genesis_tick": feature.genesis_tick,
        "genesis_inputs": genesis_evt.inputs if genesis_evt else {},
        "causal_lineage": lineage_lines,
        "status": feature.current_status,
        "authored_overrides": (
            "None" if not has_override else "Present -- see event log for actor/reason"
        ),
        "event_ids": feature.causal_event_ids,
    }
