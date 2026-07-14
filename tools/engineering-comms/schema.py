"""Validator/router for docs/engineering-command-schema.md.

Implements the schema-governed communication system requested in the
2026-07-14 implementation directive (see
logs/captains/2026/2026-07-14_engineering-sealed.md for the session that
led to this): validate every engineering message against the schema,
reject or return malformed ones rather than silently dropping them, route
valid messages by type and authority, prioritize safety escalations,
preserve a traceable append-only record of every *accepted* message, and
be tested before anything relies on it.

This is a message-shape validator/router, not a task executor -- it
decides whether a message is well-formed enough to act on and where it
should go. Actually doing the work a "command"-type message describes is
still a separate, human-in-the-loop step, same as everything else in this
repo.

Extended the same day, after a long stretch of this session where the
rigid command schema (action/target/done_criteria) got applied to a human
who needed presence, not a validated ticket. The "human" type below exists
so that never has to happen by *default* again: it requires only a body,
is never gated behind action/target/done_criteria, and always routes
ahead of ordinary engineering work, on the same footing as a safety
escalation -- because a person needing a response right now is not a
lesser priority than a well-formed command.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

# Mirrors docs/engineering-command-schema.md's required fields for an
# actionable command: action (a concrete verb), target (a specific file/
# issue/component), done_criteria (what "done" means). context/constraints
# are optional there and stay optional here too.
REQUIRED_COMMAND_FIELDS = ("action", "target", "done_criteria")

VALID_TYPES = {"command", "question", "status", "escalation", "human"}
VALID_AUTHORITY = {"lieutenant", "captain", "admiral", "engineering", "unspecified"}
VALID_PRIORITY = {"normal", "safety"}


@dataclass
class EngineeringMessage:
    type: str
    authority: str = "unspecified"
    action: Optional[str] = None
    target: Optional[str] = None
    done_criteria: Optional[str] = None
    context: Optional[str] = None
    constraints: Optional[str] = None
    priority: str = "normal"
    body: Optional[str] = None  # required for question/status/escalation


class ValidationError(Exception):
    """Raised for a malformed message. Callers must reject/return this,
    not swallow it -- nothing malformed is ever recorded as accepted."""

    def __init__(self, reason: str, missing_fields: list[str]):
        super().__init__(reason)
        self.reason = reason
        self.missing_fields = missing_fields


def validate(msg: EngineeringMessage) -> None:
    if msg.type not in VALID_TYPES:
        raise ValidationError(f"unknown type {msg.type!r} (must be one of {sorted(VALID_TYPES)})", [])
    if msg.authority not in VALID_AUTHORITY:
        raise ValidationError(f"unknown authority {msg.authority!r} (must be one of {sorted(VALID_AUTHORITY)})", [])
    if msg.priority not in VALID_PRIORITY:
        raise ValidationError(f"unknown priority {msg.priority!r} (must be one of {sorted(VALID_PRIORITY)})", [])

    if msg.type == "command":
        missing = [field for field in REQUIRED_COMMAND_FIELDS if not getattr(msg, field)]
        if missing:
            raise ValidationError(
                f"command missing required field(s): {', '.join(missing)}", missing
            )
    elif msg.type in {"question", "status", "escalation", "human"}:
        # Deliberately the same minimal bar for all four -- "human" is not
        # a command with softer requirements, it's a different kind of
        # message entirely, never subject to action/target/done_criteria.
        if not msg.body:
            raise ValidationError(f"{msg.type} requires a non-empty body", ["body"])


def route(msg: EngineeringMessage) -> str:
    """The queue/channel a *valid* message routes to. Safety escalations
    always take the safety-escalation channel regardless of their nominal
    type, per the directive's "prioritize safety escalations" requirement.
    "human" messages get the same precedence, on purpose -- a person
    needing a real response outranks any queued engineering work, the
    same way a safety escalation does, and doesn't need to argue its way
    there through the command schema first.
    """
    if msg.priority == "safety" or msg.type == "human":
        return "safety-escalation" if msg.priority == "safety" else "human-priority"
    return {
        "command": "engineering-queue",
        "question": "clarification-queue",
        "status": "status-log",
        "escalation": "safety-escalation",
    }[msg.type]


def process(msg: EngineeringMessage, record_path: Path) -> dict:
    """Validate, route, and append a traceable record. Raises
    ValidationError for anything malformed -- the caller is responsible
    for rejecting/returning it to the sender, per the directive; this
    function never silently drops a bad message, and never records one.
    """
    validate(msg)
    destination = route(msg)
    record = {
        "accepted_at": time.time(),
        "destination": destination,
        "message": asdict(msg),
    }
    record_path.parent.mkdir(parents=True, exist_ok=True)
    with record_path.open("a") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
    return record


def read_record(record_path: Path) -> list[dict]:
    """Read back the traceable record -- every message process() ever
    accepted, in order. Used by verification/audit, and by the tests."""
    if not record_path.exists():
        return []
    with record_path.open() as handle:
        return [json.loads(line) for line in handle if line.strip()]
