#!/usr/bin/env python3
"""First living integration pulse: language evidence -> proposal -> geometry.

This is a computational fixture, not a physical design authorization. It first
demonstrates refusal without measurements, then applies a separate synthetic
millimetre resolution record and generates the inherited fan-bracket geometry
with a complete feature-to-intent trace.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from bracket_generator import generate_fan_mount_bracket
from intent_bridge import (
    UnresolvedIntentError,
    compile_fan_mount_intent,
    propose_fan_bracket_translation,
)
from mesh import write_binary_stl


ROOT = Path(__file__).resolve().parent
FIXTURES = ROOT / "fixtures"
OUTPUT = ROOT / "output" / "fan-mount-bracket-integrated-v0.1.stl"
REPORT_OUTPUT = ROOT / "output" / "fan-mount-bracket-integrated-v0.1.json"


def load_json(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def run() -> dict:
    language_export = load_json("fan-bracket-language-export-v0.1.json")
    measurement_resolution = load_json("fan-bracket-measurements-v0.1.json")

    unresolved_proposal = propose_fan_bracket_translation(language_export)
    refusal = None
    try:
        compile_fan_mount_intent(unresolved_proposal)
    except UnresolvedIntentError as exc:
        refusal = str(exc)
    if refusal is None:
        raise RuntimeError("bridge incorrectly compiled unresolved language evidence")

    resolved_proposal = propose_fan_bracket_translation(language_export, measurement_resolution)
    compiled = compile_fan_mount_intent(resolved_proposal)
    mesh, validation, warnings = generate_fan_mount_bracket(compiled.intent)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    write_binary_stl(mesh, str(OUTPUT))
    output_bytes = OUTPUT.read_bytes()
    validation_dict = validation.as_dict()
    for state, expected in compiled.truth_boundary.items():
        if validation_dict[state] is not expected:
            raise RuntimeError(f"truth boundary violated: {state}={validation_dict[state]!r}")

    return {
        "schema_version": "intentforge.integratedDesignReport.v0.1",
        "pulse_status": "verified-computational-chain",
        "living_integration_complete": False,
        "source_episode_id": compiled.source_episode_id,
        "unresolved_proposal": {
            "compile_refused": True,
            "reason": refusal,
            "requirements": unresolved_proposal.unresolved,
        },
        "resolved_translation": resolved_proposal.as_dict(),
        "review_decision": compiled.review_decision,
        "feature_trace": compiled.feature_trace,
        "geometry": {
            "output_file": str(OUTPUT.relative_to(ROOT.parent)),
            "sha256": hashlib.sha256(output_bytes).hexdigest(),
            "bytes": len(output_bytes),
            "vertices": len(mesh.vertices),
            "triangles": len(mesh.triangles),
            "watertight": mesh.is_watertight(),
            "signed_volume_mm3": round(mesh.signed_volume(), 2),
        },
        "validation_status": validation_dict,
        "warnings": warnings,
        "not_yet_true": [
            "living integration is not complete",
            "private fit language has no executable v0.0 generator field",
            "not simulated",
            "not manufactured",
            "not physically tested",
            "not externally reviewed",
            "not validated for use",
        ],
    }


def main() -> int:
    report = run()
    rendered = json.dumps(report, indent=2) + "\n"
    REPORT_OUTPUT.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
