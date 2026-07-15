# AGENTS.md

Read `CLAUDE.md` first — same repo doctrine applies regardless of which
agent/model is running here (URL/port policy, live-tests-no-staging,
"if the Lt. can't see it, it doesn't exist," security-hardening
posture).

## Shared task queue

Non-privileged, git-only tasks (docs, code changes committable directly
without `sudo`) are coordinated through
[`docs/engineering-orders/queue.md`](docs/engineering-orders/queue.md),
so two agent sessions (e.g. Claude and Codex) working this repo at
different times don't duplicate or silently drop each other's work.

**This queue never covers anything requiring `sudo`.** Privileged work
(service restarts, systemd installs, `/etc/caddy/Caddyfile` changes)
stays exclusively in `/home/cgl/cmd.sh` under
[`docs/commissioning-handoff.md`](docs/commissioning-handoff.md)'s
existing protocol — do not route privileged work through this queue.

### Claim protocol

1. `git pull` before touching the queue file — never claim off a stale
   read.
2. Confirm the task's `Status: queued`. If it isn't, pick a different
   task — do not contest an existing claim.
3. Edit *only* that task's `Status` line to
   `claimed:<agent-name>@<ISO-8601 timestamp>`. Commit that single-line
   change alone, message naming the task ID. Push immediately.
4. If the push is rejected (someone else claimed first), pull, re-read.
   If it's now claimed by the other agent, back off — do not retry the
   same task. Git's fast-forward check is the lock; there is no
   separate lock server.
5. Do the work normally. Only one agent holds a given claim at a time,
   so there is no simultaneous editing of the same task's files.
6. On completion: update `Status: done@<timestamp>`, add
   `Evidence: <commit hash or report path>`, commit, push (same
   pull-first discipline).
7. Never edit another agent's claimed entry without an explicit human
   override. A claim with no commits for an unreasonable stretch gets a
   note added to that entry, not a silent reclaim — resolving a stale
   claim is the Lieutenant's call.

### `blocked-on-human` status

A fourth status, distinct from `queued`/`claimed`/`done`: a task whose
next step requires an answer only a human can give — a missing input
that can't be resolved by inspection, not merely unfinished work (see
`docs/reports/2026-07-15-inadequate-specs.md` for the incident that
produced this). Rules:

- An agent must never claim a `blocked-on-human` entry, and must never
  attempt to resolve the missing input by inference — that is the exact
  failure this status exists to prevent (Doctrine 001, Silent
  Dependency / Confident Wrong Answer).
- An agent may add a `blocked-on-human` entry when it identifies a real
  missing input during other work, same commit discipline as any other
  queue edit.
- Only a human answering the named question converts the entry back to
  `queued` (by editing the entry to state the answer and changing
  `Status` back to `queued`) — an agent does not get to decide the
  blocker is resolved on its own judgment.

### What this does not solve

True simultaneous editing of the *same* files by two agents is not
safe under this protocol — that is what isolated git worktrees are
for (see `.claude/worktrees/` for a live example), and this queue
defers to that rather than replacing it. This queue serializes *who
works on what*; it does not enable concurrent edits to one task.

## Engineering packets

Repository/service-state-changing work with real acceptance criteria
and a rollback path — not lighter synthesis/verification — uses a full
Master Packet §13 packet instead of a `queue.md` task. See
[`docs/engineering-orders/packets/README.md`](docs/engineering-orders/packets/README.md)
for the field format, when to use a packet vs. a queue task, and how a
**refusal** gets its own recorded packet
([`template-refused.md`](docs/engineering-orders/packets/template-refused.md))
rather than disappearing as an unrecorded chat exchange.

Three coordination mechanisms now exist, bounded against each other:
`cmd.sh` (privileged execution only), `queue.md` (non-privileged
lighter tasks), `packets/` (non-privileged state-changing work, or a
refusal of such work). A packet's execution may still route through
`cmd.sh` if it needs `sudo` — the packet records intent/evidence/
completion, `cmd.sh` is how the privileged step actually runs.
