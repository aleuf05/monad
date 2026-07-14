# Engineering Comms

Validator/router for `docs/engineering-command-schema.md`. Built per the
2026-07-14 implementation directive (see
`logs/captains/2026/2026-07-14_engineering-sealed.md`).

## What it does

`schema.py` takes an `EngineeringMessage` (type, authority, and either
`action`/`target`/`done_criteria` for a command, or a `body` for a
question/status/escalation) and:

- **Validates** it against the schema. Missing required fields, an
  unknown `type`/`authority`/`priority` all raise `ValidationError` with
  the specific missing/invalid field(s) named.
- **Routes** valid messages by type — `command` → `engineering-queue`,
  `question` → `clarification-queue`, `status` → `status-log`,
  `escalation` → `safety-escalation`. Any message with
  `priority="safety"` routes to `safety-escalation` regardless of its
  nominal type.
- **Records** every *accepted* message as one line of an append-only
  JSONL file (`accepted_at`, `destination`, full message). Malformed
  messages are never recorded — `process()` raises instead of writing
  anything, so the record stays a trustworthy trace of what was actually
  accepted, not an attempt log.

This validates and routes message *shape*. It does not execute the work a
command describes — that stays a separate, human-in-the-loop step, same
as everything else in this repo.

## Run the tests

```sh
python3 -m unittest tools/engineering-comms/test_schema.py
```

13 tests: well-formed commands validate/route correctly, malformed
messages are rejected with the right missing fields named (never
recorded), safety-priority messages always route to `safety-escalation`
regardless of type, and the record file is genuinely append-only —
accepted messages persist in order and a later rejected message never
disturbs prior accepted records.

## Example

```python
from schema import EngineeringMessage, process
from pathlib import Path

msg = EngineeringMessage(
    type="command",
    authority="lieutenant",
    action="fix",
    target="tools/world-intake/world_intake.py",
    done_criteria="submission path reaches FleetCore, tests pass",
)
process(msg, Path("data/engineering-comms/record.jsonl"))
```
