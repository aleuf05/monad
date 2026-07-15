# AGENTS.md

Read `CLAUDE.md` first — same repo doctrine applies regardless of which
agent/model is running here (URL/port policy, live-tests-no-staging,
"if the Lt. can't see it, it doesn't exist," security-hardening
posture).

## Work queue / report queue

Two names, two roles, kept strictly separate:

- **Work queue** (`docs/engineering-orders/queue.md`) — active tasks
  only: `queued`, `claimed`, `blocked-on-human`. Live engineering
  orders go here.
- **Report queue** — not a separate file. It's the existing
  `docs/reports/*.md` (Feature Matrix rows, findings reports) and
  `docs/doctrine/*.md` — completed evidence and findings live there,
  already. Don't create a duplicate file for this.
- Process-change requests (like this section) go under
  `docs/engineering-orders/` as their own doc, not mixed into either
  queue.

Rules: one item belongs to one queue at a time. **When a task is done,
remove its entry from `queue.md` immediately** — don't leave it sitting
there marked `done`. Its evidence already lives in the report queue
(a report file, a Feature Matrix row, a commit) by the time it's
removed; the work queue entry's job was done the moment that evidence
existed. Don't mix implementation items with record-keeping items in
either direction. If a spec is unclear or missing a source of truth,
document the gap and stop — don't invent an answer (see
`docs/reports/2026-07-15-inadequate-specs.md`).

One-line rule: **action lives in the work queue; truth lives in the
report queue.**

The work queue coordinates non-privileged, git-only tasks (docs, code
changes committable directly without `sudo`) so two agent sessions
(e.g. Claude and Codex) working this repo at different times don't
duplicate or silently drop each other's work.

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
   `claimed:<agent-name>@<ISO-8601 timestamp>`. Before committing, run
   `git diff --staged` on the queue file and confirm the diff contains
   *only* your intended change — `git add <file>` stages the file's
   entire current state, which will silently include another agent's
   concurrent uncommitted edit to the same file if one exists (this
   happened once this session: a `WO-01`/`CT-01` closure commit
   accidentally carried Codex's uncommitted `AM-01` claim along with
   it). If the staged diff has more than your one change, unstage and
   re-stage more precisely, or let the other change land in its own
   commit first. Commit your change alone, message naming the task ID.
   Push immediately.
4. If the push is rejected (someone else claimed first), pull, re-read.
   If it's now claimed by the other agent, back off — do not retry the
   same task. Git's fast-forward check is the lock; there is no
   separate lock server.
5. Do the work normally. Only one agent holds a given claim at a time,
   so there is no simultaneous editing of the same task's files.
6. On completion: first make sure the finding/evidence actually lives
   in the report queue (a report file, a Feature Matrix row, a
   commit) — then **delete the task's entire section from
   `queue.md`** in the same commit, citing that evidence in the commit
   message. Don't leave a `done` entry sitting in the work queue (same
   pull-first discipline as any other queue edit).
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
