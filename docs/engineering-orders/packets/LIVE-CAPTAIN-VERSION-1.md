# Engineering Packet — Live Captain — Version 1

Status: verified complete

## 1. Originating intent

The Admiral authorized Codex to implement a functional, local terminal
Captain on Granite with persistent conversation, Gemini inference, a
replaceable provider boundary, and no operational tools.

## 2. Verified starting state

`tools/living-captain/` already held the earlier persistence, sight, custody,
and restart prototype. `data/living-captain/` was already the ignored runtime
state location. Python 3.12 and standard-library `sqlite3` were present.
`GEMINI_API_KEY` was not exported into the inspecting process, while the
protected `/home/cgl/.config/monad/gemini.env` existed with mode 0600.

The repository working tree contained unrelated pre-existing modifications
and untracked work. This implementation is confined to the files named in
this packet.

## 3. Objective

Provide a one-command local terminal conversation in which the Admiral can
talk to a grounded Captain, stop the process, restart it, and continue from
the durable transcript.

## 4. Scope and exclusions

In scope: terminal UI, local prompt, append-only transcript, persistent
session identity, Gemini adapter, provider protocol, context bounds, usage
ledger, clean shutdown, safe errors, tests, and operator documentation.

Excluded: shell, tools, arbitrary file access, public listener, deployment,
services, background work, voice, vector memory, multiple agents, and canon
mutation.

## 5. Constraints and authority

The Admiral granted implementation authority. The API key must come only from
the process environment and must never be printed, logged, serialized, or
committed. Runtime writes are restricted by the CLI to
`data/living-captain/`. The application opens no listening socket.

## 6. Acceptance criteria

The client launches locally, names Gemini visibly, records both sides of the
conversation, preserves the active session across restart, answers using
bounded stored context, shuts down cleanly, blocks at its persistent usage
ceiling, handles API failure without inventing a reply, exposes no tool or
shell interface, and leaves the key absent from output and local records.

## 7. Tests and rollback

Offline suite:

```text
python3 -m unittest discover -s tools/living-captain -p 'test_*.py' -v
```

Rollback is removal of the new Version 1 modules, prompt, tests,
documentation, and `/home/cgl/captain.sh`. Runtime transcript removal is a
separate human-authorized action because it destroys operator data.

## 8. Assigned actor

Commander Codex is primary implementer. Claude may review but has no write
authority under this packet.

## 9. Evidence and completion state

- 2026-07-28: packet authorized and implementation begun.
- 2026-07-28: 19 Living Captain tests passed offline.
- 2026-07-28: the first live request failed safely when Google rejected the
  retired `gemini-2.5-flash-lite` model with HTTP 404. The client recorded no
  invented reply and retained the request against its conservative ceiling.
- 2026-07-28: the adapter moved to Google's current stable
  `gemini-3.5-flash-lite` model, using minimal thinking and no deprecated
  sampling parameter.
- 2026-07-28: a real Gemini turn succeeded, visibly identified the provider,
  returned the Captain role boundary, recorded usage, and shut down cleanly.
- 2026-07-28: a fresh process retained the same session identifier and
  accurately answered what the prior exchange contained using the stored
  transcript.
- 2026-07-28: the final runtime record contained five entries in expected
  role order. Three attempts were persistently counted with a conservative
  reserved estimate of $0.009265.
- 2026-07-28: exact-key scanning found no Gemini key in transcript, state,
  usage, or logs. All four runtime files were mode 0600.
- 2026-07-28: no Live Captain process remained after clean shutdown.

Completion state: verified complete and recorded.
