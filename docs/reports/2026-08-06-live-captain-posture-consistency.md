# Live Captain posture was not consistent between Claude and Codex

**Date:** 2026-08-06. **Asked:** verify Live Captain posture works for Claude
and Codex both, consistently — we will be in Live Captain mode most of the time.

## Finding

It did not. Codex had full Live Captain posture; Claude had none.

`AGENTS.md` — which Codex reads natively — carried the whole posture: mission,
default behavior ("Act."), authority, target discipline, completion criteria,
escalation limits, command presence. Claude Code does not read `AGENTS.md`. It
reads `CLAUDE.md`, and **the repo had no `CLAUDE.md`**: commit `5cc8de5`
renamed it to `OUT_CLAUDE.md` (`R090`) as "the no-CLAUDE.md experiment".

So Claude in this repo loaded only `/home/cgl/CLAUDE.md`, the parent-directory
charter. That file is good and still in force, but it contains zero mention of
Live Captain posture — no integrated station, no "never go idle", no command
presence. Grep: `live captain|doctrine 023|never go idle|chief engineer` →
**3 hits in AGENTS.md, 0 in /home/cgl/CLAUDE.md**.

Two agents, same repo, same Admiral, different postures — and nothing detected
it, because both agents work fine without posture. Just differently.

## Fix

One canonical source, two thin loaders — matching the repo's standing
"one source of truth, don't replicate it" policy:

- **`EDIT-THIS-ONE-FILE.md`** (new, root) — canonical and agent-neutral.
  Body carried over from the old `AGENTS.md` (57 of 59 sentences verbatim; the
  2 changes are the renamed title and `being Codex` → `which model you are`
  for neutrality), plus the integrated station from doctrine 023, the identity
  precondition rescued from `OUT_CLAUDE.md`, and the doctrine 024 research
  subposture.
- **`CLAUDE.md`** (new, root) — identity line + `@EDIT-THIS-ONE-FILE.md`
  import, with a read-it-yourself fallback if the import ever stops inlining.
- **`AGENTS.md`** (rewritten) — identity line + read instruction. Keeps the
  Codex-specific delta: Codex does *not* auto-load `/home/cgl/CLAUDE.md`, so
  it is told where the charter is.

Neither loader restates posture. A copy is a thing that can drift.

## Verification

Both CLIs run headless, asked from loaded context to quote integrated-station
duty #3:

| Embodiment | Carries posture | Source named | Duty #3 |
|---|---|---|---|
| Claude Code | yes | `EDIT-THIS-ONE-FILE.md` via `@import` | verbatim match |
| Codex | yes | `EDIT-THIS-ONE-FILE.md` | verbatim match |

Third embodiment, the live service Captain (`live-captain-bootstrap`, :4778,
own kernel at `tools/live-captain/prompts/captain-kernel.md`) — checked for
regression after the `AGENTS.md` rewrite. Live turn: *"I am the Live Captain
of Project Monad… I hold the integrated Captain's station across command,
engineering, verification, and continuity."* Intact.

## Guard

`scripts/sound-the-ship.sh` check 6. Faults if the canonical file is missing,
if either loader is absent or stops pointing at it, or if a loader grows past
45 lines (a fat loader is a second copy forming). Negative-tested by removing
`CLAUDE.md`: 3 faults, correctly naming "Claude loads no Live Captain posture".

## Live stack state, incidentally verified

Captain is **running**, not paused — `docs/OPERATION-RESUME.md` said paused and
was a day stale; corrected. 57/57 tests pass. All Captain units active, zero
restarts. Turn loop: HTTP 200 in 6.3s with a voice artifact. Codex app-server
alive as a child of the Captain server. Context recompiles per turn, so edits
to `current-bearing.md` land on the next turn without a restart.

One thing to watch: `codex_daemon.py` has `TURN_TIMEOUT_SECONDS = 180`, and the
journal shows a real `CodexError: Codex turn timed out` → HTTP 500 on
2026-08-05 22:02. Not reproduced today; noted, not chased. The recurring
`BrokenPipeError` in the log is SSE clients disconnecting and is benign.
