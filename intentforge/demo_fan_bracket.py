#!/usr/bin/env python3
"""IntentForge v0.0 signature demo -- the packet's own worked example:

    "I need a bracket that mounts a 40 mm fan to these two existing
    holes, avoids this cable, maintains airflow, uses M4 bolts, and can
    be printed flat without supports."

All dimensions below are illustrative placeholders (the packet did not
supply exact numbers), clearly labeled as assumptions in the resulting
report -- not presented as a real customer's measurements.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from bracket_generator import DesignIntentViolation, generate_fan_mount_bracket
from design_intent import EdgeNotch, Envelope, FanMountBracketIntent, Hole
from mesh import write_binary_stl

OUT_DIR = Path(__file__).resolve().parent / "output"


def build_demo_intent() -> FanMountBracketIntent:
    return FanMountBracketIntent(
        purpose="Mount a 40mm fan to two existing panel holes while keeping a nearby cable clear and preserving airflow.",
        envelope=Envelope(width=70.0, height=70.0, thickness=3.0),
        existing_holes=[
            Hole(cx=-25.0, cy=25.0, diameter=4.5, purpose="existing panel mounting hole (M4 clearance)"),
            Hole(cx=25.0, cy=25.0, diameter=4.5, purpose="existing panel mounting hole (M4 clearance)"),
        ],
        fan_center=(0.0, -5.0),
        fan_bolt_spacing=32.0,
        fan_bolt_diameter=4.5,
        fan_airflow_diameter=34.0,
        cable_notch=EdgeNotch(edge="south", center_offset=-22.0, width=10.0, depth=5.0, purpose="cable clearance"),
        min_wall_thickness=3.0,
        acceptance_criteria=[
            "all bolts align with the two existing holes and the fan's four mounting holes",
            "fan airflow opening is unobstructed",
            "cable retains clearance through the notch",
            "part prints flat without supports (uniform thickness, no overhangs by construction)",
        ],
        assumptions=[
            "existing-hole positions, fan center, and envelope size are illustrative placeholders, not a real customer's measurements",
            "32mm bolt spacing is a typical published value for 40mm fans, not verified against one specific datasheet",
            "airflow opening reduced to 34mm (from a first-pass 37mm) after the generator's own overlap check rejected 37mm as leaving under 3mm of material to the bolt holes -- kept here as an honest record of the tool doing its job, not smoothed over",
            "M4 clearance hole taken as 4.5mm diameter",
        ],
    )


def main() -> int:
    intent = build_demo_intent()
    try:
        mesh, status, warnings = generate_fan_mount_bracket(intent)
    except DesignIntentViolation as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stl_path = OUT_DIR / "fan-mount-bracket-v0.stl"
    write_binary_stl(mesh, str(stl_path))
    stl_bytes = stl_path.read_bytes()

    (min_x, min_y, min_z), (max_x, max_y, max_z) = mesh.bounding_box()
    report = {
        "ok": True,
        "part": "fan-mount-bracket",
        "codename": "IntentForge v0.0 (provisional)",
        "purpose": intent.purpose,
        "validation_status": status.as_dict(),
        "warnings": warnings,
        "mesh": {
            "vertex_count": len(mesh.vertices),
            "triangle_count": len(mesh.triangles),
            "watertight": mesh.is_watertight(),
            "bounding_box_mm": {"min": [min_x, min_y, min_z], "max": [max_x, max_y, max_z]},
            "signed_volume_mm3": round(mesh.signed_volume(), 2),
        },
        "output_file": str(stl_path.relative_to(Path(__file__).resolve().parents[1])),
        "output_sha256": hashlib.sha256(stl_bytes).hexdigest(),
        "output_bytes": len(stl_bytes),
        "acceptance_criteria": intent.acceptance_criteria,
        "not_yet_true": [
            "not simulated (no FEA/structural analysis has run)",
            "not manufactured (no physical print has been produced)",
            "not physically tested",
            "not externally reviewed",
            "not validated for any stated use",
        ],
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
