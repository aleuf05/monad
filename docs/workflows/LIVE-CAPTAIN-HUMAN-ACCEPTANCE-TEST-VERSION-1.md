# Live Captain Human Acceptance Test — Version 1

Status: Active test procedure

Authority: Admiral / Lt. cgl

Recorded: 2026-07-28

## Purpose

Provide the human operator with a short, repeatable test proving that Live
Captain launches, holds a natural conversation, shuts down cleanly, and
recovers conversational context after restart.

This procedure tests the real operator experience, not merely unit-level
implementation details.

## Preconditions

- Run the test at the normal Granite workstation.
- `/home/cgl/captain.sh` exists and is executable.
- Granite has network access to the Gemini API.
- The protected Gemini environment file is present.
- Never paste or type the API key into Live Captain.

## Procedure

### 1. Launch

Run:

```bash
/home/cgl/captain.sh
```

Confirm that the opening display shows:

- `Project Monad — Live Captain — Version 1`
- `Captain online`
- Gemini as the active provider
- a session identifier
- local usage information

### 2. Natural conversation

Send one ordinary natural-language message that will be easy to recognize
later.

Confirm that:

- the reply addresses the operator appropriately;
- the reply is coherent and grounded;
- the interface remains responsive;
- updated usage information appears.

Do not include credentials, secrets, or sensitive records in the test
message.

### 3. Clean shutdown

Enter:

```text
/quit
```

Confirm that the Captain reports a clean stand-down and returns control to
the terminal.

### 4. Restart

Run again:

```bash
/home/cgl/captain.sh
```

Confirm that the displayed session identifier matches the earlier launch.

### 5. Continuity check

Ask the Captain what was discussed immediately before the restart.

Confirm that the answer:

- refers accurately to the earlier exchange;
- does not invent events or actions;
- is grounded in the stored transcript.

Then enter `/quit`.

## Pass criteria

The human acceptance test passes only when:

1. both launches succeed;
2. Gemini is visibly identified;
3. one real reply is received;
4. shutdown is clean;
5. the session identifier survives restart;
6. the prior exchange is recalled accurately;
7. usage accounting remains visible;
8. no API key or secret appears in the interface.

## Failure report

If anything fails, preserve the exact visible error and report:

- which numbered step failed;
- the displayed error text;
- whether the terminal returned normally;
- whether the session identifier changed;
- whether any reply was recorded.

Do not delete the transcript or usage state while diagnosing a failure.

## Improvement rule

Future whole-number versions should extend this procedure only when the
operator experience gains a new observable capability. Each added check must
remain short, human-performable, and tied to a clear pass/fail result.

Automated tests supplement this procedure but do not replace the human
acceptance test.
