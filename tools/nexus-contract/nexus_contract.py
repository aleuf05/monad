#!/usr/bin/env python3
"""Nexus Composition Contract -- minimal executable envelope (NEXUS-LUNCH-001).

The contract is one seven-field envelope:

    Identity -> Intent -> Authority -> Capability -> Action -> Result -> Evidence

read as a chain: who acted, what they meant to do, what permitted it, what
was invoked, what happened, what came of it, and what reconstructs the whole
thing afterwards.

This module is deliberately *only* the envelope plus two adapters. It is not
a bus, a router, or a store -- Monad already has those, and this experiment
reuses them rather than growing a parallel subsystem:

  Component A  tools/engineering-comms/schema.py  -- a dataclass message
      validator with its own authority vocabulary (lieutenant/captain/
      admiral/engineering). It knows nothing about Nexus.
  Component B  tools/mission-bus/mission_bus.py   -- an append-only SQLite
      record with immutability enforced by triggers. It knows nothing about
      Nexus either, and stores events, not envelopes.

The two share no code and no data representation. The conformance test in
test_nexus_contract.py sends an envelope from A to B and requires B to
reconstruct all seven fields from its own storage alone. That is the whole
claim: the envelope survives a representation change intact.

The evidence field carries a digest over the other six. A receiver that
recomputes the digest and gets the same value has verified the chain it
reconstructed is the chain that was sent -- so "evidence" is a check the
code performs, not a label the document wears.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "monad.nexus.v0.1"

ROOT = Path(__file__).resolve().parents[2]

#: The composition contract, in order. The order is part of the contract:
#: each field is only meaningful given the ones before it.
FIELDS = ("identity", "intent", "authority", "capability", "action", "result", "evidence")

#: Minimum keys each field must carry to be reconstructable by a receiver
#: that has never seen the sender. Anything beyond these is passed through
#: untouched -- the contract fixes a floor, not a ceiling.
REQUIRED_KEYS = {
    "identity": ("id", "kind"),
    "intent": ("objective",),
    "authority": ("grant", "scope"),
    "capability": ("name", "version"),
    "action": ("verb", "target"),
    "result": ("status", "detail"),
    "evidence": ("refs", "digest"),
}

#: The four questions the success condition names, and the fields that
#: answer each. Kept as data so chain() cannot drift from the docstring.
CHAIN = {
    "requested": ("identity", "intent"),
    "permitted": ("authority",),
    "performed": ("capability", "action"),
    "observed": ("result", "evidence"),
}


class NexusError(ValueError):
    """A malformed or unverifiable envelope. Never swallowed: a receiver
    that cannot verify an envelope must reject it, not act on a guess."""


def canonical(obj: Any) -> str:
    """One byte-stable JSON spelling, so a digest computed by the sender and
    a digest computed by the receiver are comparable at all."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def digest_of(payload: dict) -> str:
    """Digest over the first six fields -- everything the evidence attests
    to. Evidence cannot cover itself, so it is excluded by construction."""
    covered = {k: payload[k] for k in FIELDS[:-1] if k in payload}
    return "sha256:" + hashlib.sha256(canonical(covered).encode()).hexdigest()


@dataclass
class NexusEnvelope:
    identity: dict
    intent: dict
    authority: dict
    capability: dict
    action: dict
    result: dict
    evidence: dict = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION

    # -- construction ----------------------------------------------------

    @classmethod
    def sealed(cls, **fields) -> "NexusEnvelope":
        """Build an envelope and stamp its evidence digest. `evidence` may
        be supplied with refs; the digest is always computed here, never
        accepted from the caller -- a self-declared digest proves nothing."""
        evidence = dict(fields.pop("evidence", None) or {})
        evidence.setdefault("refs", [])
        env = cls(evidence=evidence, **fields)
        env.evidence["digest"] = digest_of(asdict(env))
        env.validate()
        return env

    # -- contract --------------------------------------------------------

    def validate(self) -> None:
        payload = asdict(self)
        if self.schema_version != SCHEMA_VERSION:
            raise NexusError(f"unknown schema_version {self.schema_version!r}")
        for name in FIELDS:
            value = payload.get(name)
            if not isinstance(value, dict) or not value:
                raise NexusError(f"field {name!r} missing or not a non-empty object")
            # Presence, not truthiness. An empty evidence.refs list is a
            # legitimate statement ("no external references"); a missing one
            # is not. Only None and blank strings count as absent.
            missing = [
                k for k in REQUIRED_KEYS[name]
                if k not in value
                or value[k] is None
                or (isinstance(value[k], str) and not value[k].strip())
            ]
            if missing:
                raise NexusError(f"field {name!r} missing required key(s): {', '.join(missing)}")

    def verify(self) -> None:
        """validate() plus the digest check. This is what a receiving side
        calls: it answers "is this the envelope that was sent", which
        validate() alone cannot."""
        self.validate()
        expected = digest_of(asdict(self))
        if self.evidence["digest"] != expected:
            raise NexusError(
                f"evidence digest mismatch: envelope says {self.evidence['digest']}, "
                f"contents hash to {expected}"
            )

    def chain(self) -> dict:
        """The reconstructed chain: requested -> permitted -> performed ->
        observed. Reading this is how a receiver answers the seven
        questions without knowing anything about the sender."""
        payload = asdict(self)
        return {stage: {f: payload[f] for f in fields} for stage, fields in CHAIN.items()}

    # -- wire ------------------------------------------------------------

    def to_wire(self) -> str:
        return canonical(asdict(self))

    @classmethod
    def from_wire(cls, blob: str) -> "NexusEnvelope":
        try:
            payload = json.loads(blob)
        except json.JSONDecodeError as exc:
            raise NexusError(f"envelope is not valid JSON: {exc}") from exc
        if not isinstance(payload, dict):
            raise NexusError("envelope must be a JSON object")
        unknown = set(payload) - set(FIELDS) - {"schema_version"}
        if unknown:
            raise NexusError(f"unknown envelope field(s): {', '.join(sorted(unknown))}")
        missing = [f for f in FIELDS if f not in payload]
        if missing:
            raise NexusError(f"envelope missing field(s): {', '.join(missing)}")
        env = cls(**payload)
        env.verify()
        return env


# ---------------------------------------------------------------------------
# Component A adapter: engineering-comms EngineeringMessage -> envelope.
# ---------------------------------------------------------------------------

def _load(name: str, path: Path):
    """Load a sibling tool by path, once.

    Two details, both load-bearing:

    - Registered in sys.modules *before* exec_module, because @dataclass
      resolves its annotations through sys.modules[cls.__module__] and gets
      None for an unregistered spec-loaded module (mission_bus.py hit this
      too, and says so).
    - Cached, because re-executing a module mints fresh class objects each
      time. A caller doing `except engcomms.ValidationError` would then fail
      to catch the ValidationError we just raised -- same name, different
      class. Exception identity has to be stable across calls.
    """
    cached = sys.modules.get(name)
    if cached is not None:
        return cached
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_engineering_comms():
    return _load("nexus_engcomms_schema", ROOT / "tools" / "engineering-comms" / "schema.py")


def load_mission_bus():
    return _load("nexus_mission_bus", ROOT / "tools" / "mission-bus" / "mission_bus.py")


def from_engineering_message(msg, *, actor: str, capability: str, version: str,
                             status: str, detail: str, refs: list[str] | None = None) -> NexusEnvelope:
    """Component A's native message -> Nexus envelope.

    engineering-comms validates the message on its own terms first. Its
    authority vocabulary carries straight into the Authority field, which is
    the point: Nexus does not invent a permission model, it transports the
    one the sending component already had.
    """
    engcomms = load_engineering_comms()
    engcomms.validate(msg)  # raises ValidationError; a bad message never becomes an envelope
    return NexusEnvelope.sealed(
        identity={"id": actor, "kind": "agent"},
        intent={"objective": msg.done_criteria or msg.body or "", "context": msg.context},
        authority={"grant": msg.authority, "scope": engcomms.route(msg),
                   "constraints": msg.constraints},
        capability={"name": capability, "version": version},
        action={"verb": msg.action or msg.type, "target": msg.target or "n/a"},
        result={"status": status, "detail": detail},
        evidence={"refs": list(refs or [])},
    )


# ---------------------------------------------------------------------------
# Component B adapter: envelope <-> mission-bus append-only record.
#
# B does not store the envelope. It stores three events in its own schema,
# the way it stores everything else. Reconstruction folds the event log back
# into an envelope -- which is the actual test, since a stored blob would
# prove only that SQLite can hold a string.
# ---------------------------------------------------------------------------

#: event_type -> the envelope fields that event carries.
EVENT_MAP = (
    ("mission_created", ("identity", "intent", "authority")),
    ("capability_invoked", ("capability", "action")),
    ("result_observed", ("result", "evidence")),
)


def deposit(record, env: NexusEnvelope) -> list[str]:
    """Write an envelope into Component B's append-only record, split across
    its own event types. Returns the event IDs, in order."""
    env.verify()  # never record something we could not verify on receipt
    payload = asdict(env)
    ids = []
    for event_type, fields in EVENT_MAP:
        body = {f: payload[f] for f in fields}
        if event_type == "mission_created":
            # mission_bus.Record.status() reads this key off the first event.
            body["status"] = "created"
        ids.append(record.append(event_type, body))
    return ids


def reconstruct(record) -> NexusEnvelope:
    """Rebuild the envelope from Component B's stored events alone.

    Nothing from the sender is consulted -- only what B wrote down. If this
    returns a verifying envelope, the contract held across the representation
    change.
    """
    payload: dict[str, Any] = {"schema_version": SCHEMA_VERSION}
    wanted = {event_type: fields for event_type, fields in EVENT_MAP}
    for event in record.events():
        fields = wanted.get(event["event_type"])
        if not fields:
            continue
        for f in fields:
            if f in event["payload"]:
                payload[f] = event["payload"][f]
    missing = [f for f in FIELDS if f not in payload]
    if missing:
        raise NexusError(f"record does not reconstruct field(s): {', '.join(missing)}")
    env = NexusEnvelope(**payload)
    env.verify()
    return env


# ---------------------------------------------------------------------------
# Demonstration: A -> wire -> B -> reconstruction, as a single callable run.
# ---------------------------------------------------------------------------

def demo(db_path: Path) -> dict:
    """One end-to-end exchange. Returns a JSON-able evidence record of it."""
    engcomms = load_engineering_comms()
    mb = load_mission_bus()

    message = engcomms.EngineeringMessage(
        type="command",
        authority="admiral",
        action="scaffold",
        target="tools/nexus-contract/nexus_contract.py",
        done_criteria="Seven-field envelope crosses two components and reconstructs.",
        context="NEXUS-LUNCH-001",
        constraints="Additive, local, reversible. No deployment.",
    )
    sent = from_engineering_message(
        message,
        actor="captain.claude",
        capability="nexus-contract",
        version="v0.1",
        status="succeeded",
        detail="Envelope sealed by Component A and handed to the wire.",
        refs=["tools/nexus-contract/test_nexus_contract.py"],
    )

    wire = sent.to_wire()
    received = NexusEnvelope.from_wire(wire)

    record = mb.Record(db_path, mission_id="mission.nexus-lunch-001",
                       correlation_id="run.nexus-lunch-001")
    event_ids = deposit(record, received)
    rebuilt = reconstruct(record)

    return {
        "experiment": "NEXUS-LUNCH-001",
        "schema_version": SCHEMA_VERSION,
        "component_a": "tools/engineering-comms/schema.py",
        "component_b": "tools/mission-bus/mission_bus.py",
        "input_message": asdict(message),
        "envelope_sent": asdict(sent),
        "wire_bytes": len(wire),
        "event_ids": event_ids,
        "stored_event_types": [e["event_type"] for e in record.events()],
        "envelope_reconstructed": asdict(rebuilt),
        "digest_sent": sent.evidence["digest"],
        "digest_reconstructed": rebuilt.evidence["digest"],
        "identical": asdict(sent) == asdict(rebuilt),
        "chain": rebuilt.chain(),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Nexus Composition Contract conformance demo")
    ap.add_argument("--db", type=Path, default=ROOT / "data" / "nexus-contract" / "demo.sqlite3",
                    help="append-only record to write the exchange into")
    args = ap.parse_args()
    out = demo(args.db)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["identical"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
