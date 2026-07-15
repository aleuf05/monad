# Shared engineering task queue

Protocol: see [`AGENTS.md`](../../AGENTS.md) at the repo root. Non-privileged,
git-only tasks only — nothing requiring `sudo` (that stays in `cmd.sh` /
`commissioning-handoff.md`).

## LS-01 — Litestream restore drill (Design Required, not verification)

- Status: queued
- Source: Admiral's order, 2026-07-15 -- "Prove Litestream recovery
  with an actual restore drill, not a green replication status"
- **Verified starting state, checked before queueing:** no `litestream`
  binary installed, no systemd unit, zero mentions anywhere in this
  repo. This is new infrastructure to design and build, not an
  existing system to verify -- do not treat this entry as if Litestream
  is already running.
- **Scoping question, not assumed:** the only sqlite database in this
  repo is `data/world-intake.sqlite3` (confirmed via `find`). If this
  order means Litestream-replicating that database, say so explicitly
  before work starts -- don't infer the target silently.
- Output: a design doc (`docs/engineering-orders/` proposal) covering
  install, replication config, and -- per the order's actual emphasis --
  a **restore drill that is actually executed**, not just configured:
  replicate, corrupt/delete the working copy in a disposable/test
  context, restore from Litestream, verify the restored data matches.
  A green replication status alone does not satisfy this order.
- Constraints / authority: installing a new systemd service and
  touching the live sqlite file requires `sudo` -- this task stops at
  design/proposal; execution routes through `cmd.sh` per
  `commissioning-handoff.md`, same as any other privileged work.
- Acceptance criteria for this queue entry specifically: design doc
  exists, names the confirmed replication target explicitly (not
  assumed), and describes a restore drill with a concrete pass/fail
  check (e.g. "row count and checksum of restored DB match pre-
  corruption snapshot") -- not just "replication looked healthy."
- Claimed by: —
- Evidence: —

## PROV-01 — provision.sh idempotency (Design Required, not verification)

- Status: queued
- Source: Admiral's order, 2026-07-15 -- "Make provision.sh idempotent,
  secret-safe, and repeatable on a disposable node"
- **Verified starting state, checked before queueing:** no
  `provision.sh` exists anywhere in this repo currently.
- **Scoping question, not assumed:** "a disposable node" is exactly the
  kind of claim that turned out fabricated in the ENG-1 packet earlier
  this session (`node-01/02/03.livingfleet` did not resolve, had no
  `/etc/hosts` entry, no SSH config, zero repo history). Before writing
  a provisioning script targeting "a disposable node," confirm what
  node this actually means and that it's real and reachable -- do not
  assume a target that hasn't been independently verified, per Doctrine
  001 (Silent Dependency, Confident Wrong Answer).
- Output: a new `provision.sh` (location TBD pending the scoping
  question above) that is idempotent (safe to re-run), never commits or
  logs secrets in plaintext, and is testable on whatever the confirmed
  target actually is.
- Acceptance criteria for this queue entry specifically: the target
  node is named and independently confirmed reachable (not taken on
  claim) before any script is written; running the finished script
  twice in a row produces the same end state both times, with no error
  on the second run; a grep of the script and its output for anything
  matching common secret patterns (API keys, passwords, tokens) finds
  nothing in plaintext.
- Claimed by: —
- Evidence: —

## DRIFT-01 — Drift detection, report-only mode (Design Required, not verification)

- Status: queued
- Source: Admiral's order, 2026-07-15 -- "Run detection in report-only
  mode and measure false positives before any auto-remediation"
- **Verified starting state, checked before queueing:** no drift-
  detection code or docs exist anywhere in this repo. Note this
  session already did extensive *manual* source/deploy drift detection
  (`toys/` vs `web/toys/`, see `TOY-01`) -- if this order means
  automating that specific check, say so; if it means something else
  (config drift, infra drift), scope it explicitly before work starts.
- Output: a design doc proposing a report-only drift detector -- no
  auto-remediation authority, per the order's own explicit sequencing
  ("before any auto-remediation"). Must include a plan for measuring
  false-positive rate before any future auto-remediation proposal is
  even considered.
- Constraints / authority: report-only by explicit order -- any future
  task proposing auto-remediation is a separate, later decision, not
  bundled into this one.
- Acceptance criteria for this queue entry specifically: design doc
  names exactly what "drift" means for this task (config, deployed-vs-
  source, infra, or something else -- explicitly, not left ambiguous);
  proposes a concrete method for measuring false-positive rate (e.g.
  run against N known-good states, count incorrect flags); contains no
  remediation/write logic of any kind, report-only end to end.
- Claimed by: —
- Evidence: —

## SPEC-01 — Resolve missing inputs for LS-01 / PROV-01 / DRIFT-01

- Status: **blocked-on-human** (not a normal `queued` -- no agent can
  resolve this by inspection; it requires an answer only the Admiral
  can give)
- Source: `docs/reports/2026-07-15-inadequate-specs.md`
- What's missing, one line each:
  1. **LS-01:** confirm the replication target is
     `data/world-intake.sqlite3` (the only sqlite db in the repo), or
     name a different one.
  2. **PROV-01:** name "a disposable node" explicitly -- hostname,
     environment, and confirmation it's real and reachable (per
     Doctrine 001, do not let an agent infer or assume this the way
     ENG-1's fabricated hosts nearly got acted on).
  3. **DRIFT-01:** define "drift" for this task -- config drift,
     `toys/`-vs-`web/toys/` deploy drift (already handled manually,
     see `TOY-01`), infra drift, or something else.
- Output: three one-line answers, appended to the respective queue
  entries above. Once appended, `LS-01`/`PROV-01`/`DRIFT-01` convert
  from blocked to genuinely `queued` and become claimable.
- Constraints: no agent should attempt to answer these by inference --
  that's the exact failure this entry exists to prevent.
- Claimed by: — (cannot be claimed by an agent; awaiting Admiral)
- Evidence: —

## HUMAN-01 — Rule on issue #16 vs. CLAUDE.md contradiction

- Status: blocked-on-human
- Source: `GA-01` finding, `docs/reports/2026-07-15-phase1-sweep-and-corrections.md`
- What's needed: a ruling on which document currently governs --
  GitHub issue #16 (still OPEN, self-declared release blocker for
  FleetCore command auth) or `CLAUDE.md`'s current stated policy
  ("security hardening is not the priority here"). `monad-slice-g` has
  real unmerged work toward #16; nothing proceeds on it until this is
  ruled on.
- Claimed by: — (Admiral's decision only)
- Evidence: —

## HUMAN-02 — Authorize or decline worktree archival

- Status: blocked-on-human
- Source: `GA-01` finding
- What's needed: explicit sign-off to archive/remove
  `monad-issue17-slice-a`, `monad-issue18-slice-b`,
  `monad-history-integration` -- confirmed safe (issues #17/#18 closed,
  superseded by the bounded-retention approach that shipped to main, no
  open PRs), but removal was deliberately left for authorization, not
  done unilaterally.
- Claimed by: — (Lieutenant's call)
- Evidence: —

## HUMAN-03 — Restore access to scout-screen-mode worktree

- Status: blocked-on-human
- Source: `GA-01` finding
- What's needed: someone with host permissions to resolve the "dubious
  ownership" git error on `.claude/worktrees/scout-screen-mode`, or
  confirm whether the locked worktree (`worktree-scout-screen-mode`) is
  still active work or safe to release. No agent this session could
  inspect it.
- Claimed by: — (needs host-level access)
- Evidence: —

## HUMAN-04 — Adopt or reject Doctrine 001

- Status: blocked-on-human
- Source: `docs/doctrine/001-verification-command-dialect.md`
- What's needed: a decision on Status -- currently "Proposed," already
  load-bearing in practice (it's what the ENG-1 refusal was reasoned
  from), but never formally adopted per Master Packet §15's
  human-approval requirement.
- Claimed by: — (Admiral's decision only)
- Evidence: —

## RADIO-02 — Radio Console: Priority Queue + Interruption Rules

- Status: done@2026-07-15T17:47:36Z
- Depends on: nothing -- RADIO-01 was cut (no FleetCore change survived
  verification; see the design doc). Scores against the 5 pre-existing
  event types (`WaypointReached`, `RouteReplaced`, `RouteCompleted`,
  `Holding`, `WatchEvent`).
- Source: same doc, System 1
- Output: scores every candidate transmission (from the 5 real event
  types) on urgency/relevance/source authority/freshness/interruption
  permission/expiry. Decides what airs, what waits, what expires
  unspoken.
- Claimed by: claude
- Evidence: `toys/radio-console/app.js`, `web/toys/radio-console/app.js`, `node --check toys/radio-console/app.js`, `node --check web/toys/radio-console/app.js`

## RADIO-03 — Radio Console: Station Knowledge Scoping

- Status: done@2026-07-15T17:53:38Z
- Depends on: RADIO-02
- Source: same doc, System 2
- Output: per-station filter predicate over the event stream -- no
  shared omniscience, each station sees only what its role could
  plausibly observe.
- Claimed by: claude
- Evidence: `toys/radio-console/app.js`, `web/toys/radio-console/app.js`, `toys/radio-console/README.md`, `node --check toys/radio-console/app.js`, `node --check web/toys/radio-console/app.js`

## RADIO-04 — Radio Console: Request/Acknowledge/Response Threading

- Status: done@2026-07-15T18:12:00Z
- Depends on: RADIO-02
- Source: same doc, System 3
- Output: `pending -> acked -> completed / timeout -> escalated` state
  machine per exchange.
- Claimed by: claude
- Evidence: `toys/radio-console/app.js`, `web/toys/radio-console/app.js`, `node --check toys/radio-console/app.js`, `node --check web/toys/radio-console/app.js`

## RADIO-05 — Radio Console: three independent control signals (not a god scalar)

- Status: done@2026-07-15T18:20:00Z
- Depends on: RADIO-02 (done)
- Source: superseded by the Admiral's supplemental risk-review packet §4
  -- a single channel-pressure scalar was explicitly rejected as a "god
  scalar" risk. Rebuilt as three independently observable signals:
  **Traffic Load** (candidate/pending-transmission count), **Operational
  Severity** (derived from real `fuel_fraction` -- the only real
  numeric severity signal that exists, per this session's verification),
  **Command Discipline** (operator-set UI control: quiet watch / normal
  / harbor / priority / battle stations / radio silence -- not derived).
  Also builds the 9-state radio-state indicator (packet §1: silence
  must be discoverable) as a composite status line reading these three
  signals plus connection/power state.
- Claimed by: claude
- Evidence: commit `36f3889`; verified live via headless browser against
  the real fleet -- connection state, composite status line with real
  pending-exchange counts, and `radio_silence` suppression all confirmed
  working end-to-end, not just syntax-checked

## RADIO-06 — Radio Console: Short-Term Transmission Memory

- Status: done@2026-07-15T18:33:00Z
- Depends on: RADIO-02
- Source: same doc, System 5
- Output: ring buffer, last N transmissions per station, enables "no
  change since last report."
- Claimed by: claude
- Evidence: `toys/radio-console/app.js`, `web/toys/radio-console/app.js`, `node --check toys/radio-console/app.js`, `node --check web/toys/radio-console/app.js`

## RADIO-07 — Radio Console: minimum v1 UX, integrate, deploy, verify live

- Status: claimed:claude@2026-07-15T18:35:00Z
- Depends on: RADIO-02 through RADIO-06 all landed
- Source: same doc, acceptance test
- Output: one status line (`QUIET WATCH · 3 ACTIVE STATIONS · 1 PENDING
  REQUEST · TRAFFIC LOW`), all 5 systems wired together, deployed
  `toys/` -> `web/toys/`, live-verified: console goes silent when
  nothing matters, interrupts itself when something does, says "no
  change since last report" -- all three emergent, none hardcoded.
- Claimed by: —
- Evidence: —
