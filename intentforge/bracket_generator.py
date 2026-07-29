"""IntentForge v0.0 -- the one part family this version can actually
generate: a flat plate that mounts a fan to two existing holes, with an
edge keep-out notch and a minimum printable wall thickness.

This is intentionally the whole of v0.0's generative capability. The
concept packet describes a much larger system (arbitrary interfaces,
manufacturing-process-aware checks, revision loops, STEP export,
natural-language intake). None of that is built here. What's here is one
real, working, testable slice of the "purpose -> constraints ->
relationships -> geometry" loop, honestly reported as exactly that.
"""

from __future__ import annotations

import math

from design_intent import EdgeNotch, Envelope, FanMountBracketIntent, Hole, ValidationStatus
from mesh import Mesh, circle_points, extrude_flat_part


class DesignIntentViolation(ValueError):
    """Raised when the contract cannot be satisfied honestly -- e.g. two
    holes overlap, or a hole crowds the boundary below the requested
    minimum wall thickness. The generator refuses rather than silently
    emitting geometry that violates the contract's own constraints."""


def _edge_geometry(envelope: Envelope, edge: str) -> tuple[tuple[float, float], tuple[float, float], tuple[float, float], tuple[float, float]]:
    w, h = envelope.width, envelope.height
    corners = {
        "BL": (-w / 2, -h / 2),
        "BR": (w / 2, -h / 2),
        "TR": (w / 2, h / 2),
        "TL": (-w / 2, h / 2),
    }
    pairs = {"south": ("BL", "BR"), "east": ("BR", "TR"), "north": ("TR", "TL"), "west": ("TL", "BL")}
    if edge not in pairs:
        raise DesignIntentViolation(f"unknown edge {edge!r} -- must be one of {sorted(pairs)}")
    a_key, b_key = pairs[edge]
    a, b = corners[a_key], corners[b_key]
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy)
    tangent = (dx / length, dy / length)
    inward = (-tangent[1], tangent[0])  # left-of-travel = interior, since the outer loop is CCW
    return a, b, tangent, inward


def _notch_path(envelope: Envelope, notch: EdgeNotch) -> list[tuple[float, float]]:
    a, b, tangent, inward = _edge_geometry(envelope, notch.edge)
    mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    p_mid = (mid[0] + tangent[0] * notch.center_offset, mid[1] + tangent[1] * notch.center_offset)
    p_a = (p_mid[0] - tangent[0] * notch.width / 2, p_mid[1] - tangent[1] * notch.width / 2)
    p_b = (p_mid[0] + tangent[0] * notch.width / 2, p_mid[1] + tangent[1] * notch.width / 2)
    p_a_in = (p_a[0] + inward[0] * notch.depth, p_a[1] + inward[1] * notch.depth)
    p_b_in = (p_b[0] + inward[0] * notch.depth, p_b[1] + inward[1] * notch.depth)
    return [p_a, p_a_in, p_b_in, p_b]


def build_outer_with_notch(envelope: Envelope, notch: EdgeNotch | None) -> list[tuple[float, float]]:
    w, h = envelope.width, envelope.height
    corners = {"BL": (-w / 2, -h / 2), "BR": (w / 2, -h / 2), "TR": (w / 2, h / 2), "TL": (-w / 2, h / 2)}
    order = ["BL", "BR", "TR", "TL"]
    edge_of = {("BL", "BR"): "south", ("BR", "TR"): "east", ("TR", "TL"): "north", ("TL", "BL"): "west"}
    loop: list[tuple[float, float]] = []
    for i in range(4):
        a_key, b_key = order[i], order[(i + 1) % 4]
        edge_name = edge_of[(a_key, b_key)]
        loop.append(corners[a_key])
        if notch is not None and notch.edge == edge_name:
            loop.extend(_notch_path(envelope, notch))
    return loop


def _circle_vs_rect_clear(cx: float, cy: float, r: float, rect_min: tuple[float, float], rect_max: tuple[float, float]) -> bool:
    """True if a circle does not intersect an axis-aligned rectangle
    (rect given in the same local frame as cx, cy)."""
    closest_x = max(rect_min[0], min(cx, rect_max[0]))
    closest_y = max(rect_min[1], min(cy, rect_max[1]))
    return math.hypot(cx - closest_x, cy - closest_y) > r


def _validate(intent: FanMountBracketIntent, holes: list[Hole]) -> None:
    w, h = intent.envelope.width, intent.envelope.height
    margin = intent.min_wall_thickness

    for hole in holes:
        r = hole.diameter / 2
        if not (-w / 2 + margin + r <= hole.cx <= w / 2 - margin - r):
            raise DesignIntentViolation(
                f"hole '{hole.purpose}' at x={hole.cx} crowds the east/west boundary below the "
                f"{margin}mm minimum wall thickness"
            )
        if not (-h / 2 + margin + r <= hole.cy <= h / 2 - margin - r):
            raise DesignIntentViolation(
                f"hole '{hole.purpose}' at y={hole.cy} crowds the north/south boundary below the "
                f"{margin}mm minimum wall thickness"
            )

    for i in range(len(holes)):
        for j in range(i + 1, len(holes)):
            a, b = holes[i], holes[j]
            dist = math.hypot(a.cx - b.cx, a.cy - b.cy)
            min_dist = a.diameter / 2 + b.diameter / 2 + margin
            if dist < min_dist:
                raise DesignIntentViolation(
                    f"hole '{a.purpose}' and hole '{b.purpose}' overlap or violate the "
                    f"{margin}mm minimum wall thickness between them (center distance {dist:.2f}mm, "
                    f"required {min_dist:.2f}mm)"
                )

    if intent.cable_notch is not None:
        a, b, tangent, inward = _edge_geometry(intent.envelope, intent.cable_notch.edge)
        rect_min = (intent.cable_notch.center_offset - intent.cable_notch.width / 2, 0.0)
        rect_max = (intent.cable_notch.center_offset + intent.cable_notch.width / 2, intent.cable_notch.depth)
        for hole in holes:
            local_s = (hole.cx - a[0]) * tangent[0] + (hole.cy - a[1]) * tangent[1]
            local_d = (hole.cx - a[0]) * inward[0] + (hole.cy - a[1]) * inward[1]
            if not _circle_vs_rect_clear(local_s, local_d, hole.diameter / 2 + margin, rect_min, rect_max):
                raise DesignIntentViolation(
                    f"hole '{hole.purpose}' intersects the '{intent.cable_notch.purpose}' keep-out region"
                )


def generate_fan_mount_bracket(intent: FanMountBracketIntent) -> tuple[Mesh, ValidationStatus, list[str]]:
    warnings = list(intent.assumptions)

    fan_holes = []
    fx, fy = intent.fan_center
    half_spacing = intent.fan_bolt_spacing / 2
    for dx, dy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        fan_holes.append(
            Hole(
                cx=fx + dx * half_spacing,
                cy=fy + dy * half_spacing,
                diameter=intent.fan_bolt_diameter,
                purpose="fan mounting bolt",
            )
        )

    airflow_hole = Hole(cx=fx, cy=fy, diameter=intent.fan_airflow_diameter, purpose="fan airflow opening")

    all_holes = list(intent.existing_holes) + fan_holes + [airflow_hole]

    _validate(intent, all_holes)

    if intent.min_wall_thickness < 1.6:
        warnings.append(
            f"min_wall_thickness ({intent.min_wall_thickness}mm) is below the ~1.6mm commonly cited "
            "as a safe FDM minimum for a 0.4mm nozzle -- printability_estimated is not claimed above that threshold"
        )

    outer = build_outer_with_notch(intent.envelope, intent.cable_notch)
    hole_loops = [circle_points(h.cx, h.cy, h.diameter / 2, n=24, ccw=False) for h in all_holes]

    mesh = extrude_flat_part(outer, hole_loops, intent.envelope.thickness)

    status = ValidationStatus(
        geometry_proposed=True,
        constraints_checked=True,  # overlap / wall-thickness / keep-out checks above actually ran
        printability_estimated=intent.min_wall_thickness >= 1.6 and intent.envelope.thickness >= 1.6,
        # everything else stays False: nothing here simulated, manufactured, physically tested,
        # externally reviewed, or validated for a stated use -- v0.0 has done none of that.
    )

    if not mesh.is_watertight():
        # Should not happen given the construction above -- if it does,
        # that's a real defect, not a case to paper over with a warning.
        raise RuntimeError("generated mesh failed the watertight check -- this is a generator bug, not a warning")

    return mesh, status, warnings
