#!/usr/bin/env python3
"""Nexus Capture -- Minimal Executable Protocol for Concept-to-Mechanism.

Process:
  raw thought -> consequence generation -> capture -> naming/integration -> topology change -> study capture effect -> new conceptual reality

Minimum Executable Format:
  RAW
  CONSEQUENCES
  MAP CHANGE
  CAPTURE EFFECT
  REALITY EDGE

Core Axioms:
- Spark vs Warp: Spark is the transient cognitive flash; Warp is the durable structural topology.
- Documentation Roles: Memory (record), Measurement (instrument), Construction (instantiate reality).
- Capture Effect: The irreversible observer-system state transition that occurs upon capture.
- Reflexive Documentation & Self-Instantiation: The capture defines and executes its own mechanism.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

SECTIONS = ("RAW", "CONSEQUENCES", "MAP CHANGE", "CAPTURE EFFECT", "REALITY EDGE")

DELEGATE_SLEEP_SPECIMEN = """# Nexus Capture Specimen 001 -- Delegate Sleep

## RAW
"delegate sleep" -- prepare the conditions, hand the state transition to the organism, let the human reap the result.

## CONSEQUENCES
1. Conscious executive ceases active striving and terminates micromanagement loops.
2. Boundary conditions (darkness, quiet, completed handover, zero pending obligations) are established prior to transition.
3. Substrate autonomy: biological restoration and background daemon consolidation operate without intrusive supervision.
4. Removes the self-defeating paradox of trying to "force" rest or background processing.

## MAP CHANGE
Operational topology shifts from active executive forcing to condition-setting and delegated substrate execution. The conscious mind acts as state-preparer and handoff coordinator; the underlying organism acts as the state transition engine.

## CAPTURE EFFECT
Naming the maneuver immediately converts fatigue from a point of frustration into a formal handoff protocol. The observer ceases trying to micromanage background recovery and trusts the delegated state transition.

## REALITY EDGE
Measurable across human rest cycles (reduced sleep latency upon handoff) and computational background workflows (clean async task delegation without polling loops).
"""


class NexusCaptureError(ValueError):
    """Raised when a capture artifact is incomplete or malformed."""


def canonical(obj: Any) -> str:
    """Byte-stable JSON representation."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def compute_digest(data: Dict[str, str]) -> str:
    """SHA-256 digest over the 5 core capture fields."""
    core = {k: data[k] for k in SECTIONS if k in data}
    return "sha256:" + hashlib.sha256(canonical(core).encode("utf-8")).hexdigest()


@dataclass
class NexusCapture:
    raw: str
    consequences: str
    map_change: str
    capture_effect: str
    reality_edge: str
    digest: str = ""

    def __post_init__(self):
        core = {
            "RAW": self.raw.strip(),
            "CONSEQUENCES": self.consequences.strip(),
            "MAP CHANGE": self.map_change.strip(),
            "CAPTURE EFFECT": self.capture_effect.strip(),
            "REALITY EDGE": self.reality_edge.strip(),
        }
        for k, v in core.items():
            if not v:
                raise NexusCaptureError(f"Capture section {k} cannot be empty.")
        calculated = compute_digest(core)
        if self.digest and self.digest != calculated:
            raise NexusCaptureError(
                f"Digest mismatch: payload says {self.digest} but computed {calculated}"
            )
        self.digest = calculated

    def to_dict(self) -> Dict[str, str]:
        return {
            "RAW": self.raw.strip(),
            "CONSEQUENCES": self.consequences.strip(),
            "MAP CHANGE": self.map_change.strip(),
            "CAPTURE EFFECT": self.capture_effect.strip(),
            "REALITY EDGE": self.reality_edge.strip(),
            "DIGEST": self.digest,
        }

    def to_markdown(self, title: Optional[str] = None) -> str:
        t = title or "Nexus Capture"
        return (
            f"# {t}\n\n"
            f"<!-- nexus-capture-digest: {self.digest} -->\n\n"
            f"## RAW\n{self.raw.strip()}\n\n"
            f"## CONSEQUENCES\n{self.consequences.strip()}\n\n"
            f"## MAP CHANGE\n{self.map_change.strip()}\n\n"
            f"## CAPTURE EFFECT\n{self.capture_effect.strip()}\n\n"
            f"## REALITY EDGE\n{self.reality_edge.strip()}\n"
        )

    def to_nexus_envelope(
        self,
        actor: str = "captain.live",
        grant: str = "admiral",
        scope: str = "nexus-capture",
    ) -> Dict[str, Any]:
        """Convert into a 7-field Nexus Composition Envelope."""
        payload = {
            "identity": {"id": actor, "kind": "agent"},
            "intent": {"objective": "transform raw spark into durable operational warp"},
            "authority": {"grant": grant, "scope": scope},
            "capability": {"name": "nexus-capture", "version": "v0.1"},
            "action": {"verb": "capture", "target": self.raw[:64]},
            "result": {
                "status": "integrated",
                "detail": self.map_change[:128],
                "capture_effect": self.capture_effect[:128],
                "reality_edge": self.reality_edge[:128],
            },
        }
        # Evidence digest covers the 6 fields above
        evidence_digest = (
            "sha256:"
            + hashlib.sha256(canonical(payload).encode("utf-8")).hexdigest()
        )
        payload["evidence"] = {
            "refs": [f"capture:{self.digest}"],
            "digest": evidence_digest,
        }
        return payload


def parse_capture_markdown(text: str) -> NexusCapture:
    """Parse text containing the 5 minimum executable sections."""
    # Look for optional embedded digest tag
    digest_match = re.search(r"<!--\s*nexus-capture-digest:\s*(sha256:[a-f0-9]+)\s*-->", text)
    claimed_digest = digest_match.group(1) if digest_match else ""

    # Normalize headers
    # Match headers like ## RAW, # RAW, RAW:, **RAW**
    pattern = re.compile(
        r"^(?:#{1,3}\s*|\*{2}|)?(RAW|CONSEQUENCES|MAP CHANGE|CAPTURE EFFECT|REALITY EDGE)(?:\*{2}|:)?\s*$",
        re.IGNORECASE | re.MULTILINE,
    )
    matches = list(pattern.finditer(text))
    if not matches:
        raise NexusCaptureError("No valid Nexus Capture sections found in text.")

    found_sections: Dict[str, str] = {}
    for i, match in enumerate(matches):
        sec_name = match.group(1).upper()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[start:end].strip()
        found_sections[sec_name] = content

    missing = [s for s in SECTIONS if s not in found_sections or not found_sections[s]]
    if missing:
        raise NexusCaptureError(f"Missing required capture sections: {', '.join(missing)}")

    return NexusCapture(
        raw=found_sections["RAW"],
        consequences=found_sections["CONSEQUENCES"],
        map_change=found_sections["MAP CHANGE"],
        capture_effect=found_sections["CAPTURE EFFECT"],
        reality_edge=found_sections["REALITY EDGE"],
        digest=claimed_digest,
    )


def process_raw_thought(raw: str, consequences: str, map_change: str, capture_effect: str, reality_edge: str) -> NexusCapture:
    """Execute the full 7-step sequence into an instantiated capture object."""
    return NexusCapture(
        raw=raw,
        consequences=consequences,
        map_change=map_change,
        capture_effect=capture_effect,
        reality_edge=reality_edge,
    )


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Nexus Capture Runner & Validator")
    parser.add_argument("--validate", type=Path, help="Validate a capture markdown file")
    parser.add_argument("--specimen", action="store_true", help="Print the 'delegate sleep' specimen")
    parser.add_argument("--envelope", action="store_true", help="Print the 7-field Nexus Envelope for specimen or file")
    parser.add_argument("--check", action="store_true", help="Self-check the capture protocol and specimen")
    args = parser.parse_args(argv)

    if args.specimen:
        print(DELEGATE_SLEEP_SPECIMEN)
        return 0

    if args.check:
        cap = parse_capture_markdown(DELEGATE_SLEEP_SPECIMEN)
        env = cap.to_nexus_envelope()
        print(f"OK: Specimen parsed and verified. Digest: {cap.digest}")
        print(f"OK: Envelope sealed. Evidence digest: {env['evidence']['digest']}")
        return 0

    if args.validate:
        if not args.validate.exists():
            print(f"Error: file {args.validate} does not exist.", file=sys.stderr)
            return 1
        content = args.validate.read_text(encoding="utf-8")
        try:
            cap = parse_capture_markdown(content)
            if args.envelope:
                print(json.dumps(cap.to_nexus_envelope(), indent=2))
            else:
                print(f"VALID: {args.validate} conforms to Nexus Capture schema.")
                print(f"Digest: {cap.digest}")
            return 0
        except NexusCaptureError as e:
            print(f"INVALID: {e}", file=sys.stderr)
            return 1

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
