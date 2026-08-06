"""Authored overrides: explicit developer state edits, always recorded.

The v0 prototype exposes no editing UI, but the data model and this function
support the distinction the packet requires between natural simulation
evolution and direct intervention. Any feature whose cell was touched by an
override is marked `authored_override = True` and that taints its diagnostic
card -- the card must never claim "No authored overrides detected" when one
occurred anywhere in the feature's lineage.
"""

from __future__ import annotations


def apply_override(
    world,
    event_log,
    feature_registry,
    tick: int,
    cell: tuple[int, int],
    field_name: str,
    new_value: float,
    actor: str,
    reason: str,
):
    r, c = cell
    before = world.fields[field_name][r][c]
    world.fields[field_name][r][c] = new_value

    evt = event_log.record(
        tick=tick,
        event_type="override_applied",
        cell=cell,
        inputs={"field": field_name, "actor": actor, "reason": reason},
        caused_by=[],
        result={"before": before, "after": new_value},
        authored_override=True,
    )

    feat = feature_registry.feature_at(cell)
    if feat is not None:
        feature_registry.append_event(feat.feature_id, evt.event_id)
        feature_registry.mark_override(feat.feature_id)

    return evt
