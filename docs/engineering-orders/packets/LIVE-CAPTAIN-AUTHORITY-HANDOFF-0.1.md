# Engineering Packet — Live Captain Authority & Handoff — 0.1

Status: verified complete (scoped subset — see Exclusions and Known
limitations)

## 1. Originating intent

The Admiral authorized "Live Operations Reset — Phase 2": make the Live
Captain doctrine govern actual Claude/Codex operation, and remove the
current handoff bottleneck (task results only reachable by manual clipboard
copy into a chat window), per the packet delivered 2026-08-01.

## 2. Verified starting state

`tools/root-console/` (`server.py`, `codex_daemon.py`, `auth.py`,
`research.py`, `static/`) existed and ran live as `root-console.service`,
but was **entirely untracked in git** — `git ls-files tools/root-console/`
returned nothing before this packet. No handoff, inbox, or dispatch
mechanism existed anywhere in the repo (`grep -rli "handoff|dispatch|inbox"`
across `tools/root-console` and `console` returned no hits). The live
console frontend (`console/index.html`, `console/assets/js/root-console.js`)
already carried substantial **pre-existing uncommitted changes from other
sessions** unrelated to this work (`console/index.html` modified, `.js`
untracked) — `git status --short` at start showed 12 modified and ~15
untracked paths repo-wide, none authored by this session.

Working tree: branch `agent/living-world-intake-v0-1`, in sync with
`origin/agent/living-world-intake-v0-1` (local HEAD verified an ancestor of
remote via `git merge-base --is-ancestor` before any push).

## 3. Objective

Smallest complete operational path: agent executes a bounded task → writes a
structured handoff → Live Captain can inspect it immediately, without
requiring git publication for internal visibility. Publication kept
strictly separate, only when a task explicitly requires it.

## 4. Scope and exclusions

In scope: canonical authority-contract doctrine file; handoff writer/reader
module; handoff inbox at `~/.monad/handoffs/captain_inbox/`; Root Console
API (`GET /api/handoffs`, `GET /api/handoffs/detail`); live SSE broadcast of
new handoffs reusing the existing `CodexDaemon` subscriber mechanism (no new
event system); a Handoffs panel in the live console UI (list, expand,
refresh, publication-state badge, source path).

Excluded (deliberately, not implemented this pass):

- A one-click "Dispatch to Claude / Dispatch to Codex" button that spawns an
  agent subprocess from a web request. This would be a new, remotely
  triggerable code-execution surface on a system with `sudo`/git-push
  access — a materially different risk category from everything else in
  this packet, which is read/inspect-only from the browser's perspective.
  Flagged for the Admiral's explicit call rather than built by inference.
- "Acknowledge handoff" / "Request follow-up" actions and the full
  dispatch/command-path UI (section 7 of the source packet) — not exercised
  by the two validation scenarios in section 8, and adding them now would be
  scope beyond what was verified.
- Redesign of Root Console or the research system (excluded per the source
  packet's own constraint).
- Committing `console/index.html` / `console/assets/js/root-console.js` as
  part of this packet — see Known limitations.

## 5. Constraints and authority

Authorized by the Admiral's Phase 2 packet, 2026-08-01, under
`docs/doctrine/009-live-captain-authority-contract.md` (this packet's own
first deliverable). Repository-local, reversible implementation; one
production restart of `root-console.service` performed after confirming (via
`journalctl`) no in-flight `/api/turn` conversation was active.

## 6. Acceptance criteria

- A completed task can produce a structured local handoff file without any
  git operation.
- The handoff appears in `GET /api/handoffs` and is fully readable via
  `GET /api/handoffs/detail`.
- The live console surfaces new handoffs within seconds via the existing SSE
  stream, distinguishes local-only from published, and shows the exact
  source path.
- A second task that explicitly requires publication can commit and push,
  and the handoff accurately records commit SHA and push state.
- No existing live functionality (chat, fleet status, research cockpit)
  regressed.

## 7. Tests and rollback

Manual/live verification (no existing automated suite covers this
directory — none was found to run).

Rollback: `git revert` the commit below; the handoff inbox at
`~/.monad/handoffs/captain_inbox/` is additive/local and needs no rollback,
only deletion if desired (human-authorized, since it's operator data).

## 8. Assigned actor

Claude, dispatched directly by the Admiral (not yet through an automated
Live Captain dispatch path, since that path is exactly what section 7 of the
source packet, excluded above, would build).

## 9. Evidence and completion state

- 2026-08-01: Wrote `docs/doctrine/009-live-captain-authority-contract.md`,
  `tools/root-console/handoff.py`.
- 2026-08-01: Added `CodexDaemon.broadcast()` (thin public wrapper over the
  existing `_broadcast`), `watch_handoff_inbox()`, and two `GET` routes to
  `tools/root-console/server.py`. `python3 -m py_compile` clean on all
  touched modules.
- 2026-08-01: Confirmed via `systemctl status` + `journalctl` that no
  `/api/turn` conversation was in flight; restarted `root-console.service`.
  Service came back active; `GET /api/status` correctly 401s unauthenticated.
- 2026-08-01: Logged in with the existing session password, confirmed
  `GET /api/handoffs` returns `{"handoffs": []}` on an empty inbox.
- 2026-08-01: Ran validation scenario 1 — wrote a real handoff
  (`RC-VALIDATE-1`) reporting the canonical active policy files (`CLAUDE.md`
  for Claude, auto-injected by the harness on every read inside this repo;
  `AGENTS.md` for Codex, read by `codex app-server` from its cwd, confirmed
  live via the running process's cwd). Confirmed via `curl` that
  `GET /api/handoffs` and `GET /api/handoffs/detail` both serve it correctly,
  `publicationState: LOCAL_ONLY`, no commit involved.
- 2026-08-01: Confirmed the SSE broadcast live: opened `GET /api/stream`,
  wrote a second test handoff, captured the exact
  `CAPTAIN_HANDOFF_AVAILABLE` event on the stream within 2 seconds (the
  watcher's poll interval), then deleted that throwaway test file.
- 2026-08-01: Added the Handoffs panel to `console/index.html` +
  `console/assets/js/root-console.js` (list, click-to-expand overlay,
  refresh button, `local-only`/`published` badge, timestamp, source path;
  live SSE event triggers an automatic re-poll). Verified live via `curl`
  against `http://192.168.0.100:8080/` and `/assets/js/root-console.js` —
  both 200, both contain the new markup/code (`grep -c handoff` = 28 in
  each). No Caddyfile change was needed — `/root-console-api/*` already
  proxied to this same backend.
- 2026-08-01: Ran validation scenario 2 (this packet file is the "one
  approved documentation file"). Committed
  `docs/doctrine/009-live-captain-authority-contract.md`,
  `tools/root-console/handoff.py`, `tools/root-console/server.py`,
  `tools/root-console/codex_daemon.py`, and this packet file — see commit
  SHA recorded in the corresponding `RC-VALIDATE-2` handoff — and pushed to
  `origin/agent/living-world-intake-v0-1` after a fresh `git fetch`
  confirmed no divergence.

Completion state: verified complete for the scope in section 4; the
dispatch-UI and acknowledge/follow-up actions remain open, by deliberate
exclusion, pending an explicit Admiral decision on the code-execution-surface
question above.

## Known limitations

- `console/index.html` and `console/assets/js/root-console.js` carry
  substantial pre-existing uncommitted changes from other sessions that
  predate and are unrelated to this packet. This packet's UI changes to
  those two files are **live and verified working** (served directly, no
  git tracking required for that), but were deliberately **not committed**
  here — doing so would have swept in unreviewed, unrelated prior work under
  this packet's commit. That reconciliation is the Admiral's/Captain's own
  call, not this packet's to make.
- `tools/root-console/auth.py`, `research.py`, and `static/` remain
  untracked in git, as they were before this packet — only the files this
  packet actually touched were added.
- No automated test suite exists for `tools/root-console/`; verification
  here is manual/live only.
- The full Root Console command-dispatch path (section 7 of the source
  packet) is not built. What exists today is inspection (list/detail) only.
