# Shared engineering task queue

Protocol: see [`AGENTS.md`](../../AGENTS.md) at the repo root. Non-privileged,
git-only tasks only — nothing requiring `sudo` (that stays in `cmd.sh` /
`commissioning-handoff.md`).

## ISSUES-01 — Current failure modes, report-only

- Status: queued
- Source: repo scan and queue review, 2026-07-15
- Output: a short report naming the concrete failure modes still visible in
  the repo state, limited to the radio-console degradation cases, the
  intentionally narrow drift boundary, and the human-gated queue blockers.
- Constraints: report-only, no remediation/write logic, no speculation.
- Claimed by: —
- Evidence: `docs/reports/2026-07-15-current-failure-modes.md`

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

- Status: done@2026-07-15T18:43:00Z
- Depends on: RADIO-02 through RADIO-06 all landed
- Source: same doc, acceptance test
- Output: one status line (`QUIET WATCH · 3 ACTIVE STATIONS · 1 PENDING
  REQUEST · TRAFFIC LOW`), all 5 systems wired together, deployed
  `toys/` -> `web/toys/`, live-verified: console goes silent when
  nothing matters, interrupts itself when something does, says "no
  change since last report" -- all three emergent, none hardcoded.
- Claimed by: claude
- Evidence: `toys/radio-console/app.js`, `web/toys/radio-console/app.js`, `node --check toys/radio-console/app.js`, `node --check web/toys/radio-console/app.js`, VM smoke harness confirming `QUIET WATCH · 3 STATIONS ACTIVE · 1 PENDING REQUEST · TRAFFIC LOW · NO CHANGE SINCE LAST REPORT`.
  **Follow-up fix, commit `9783648`:** a full acceptance-test pass caught
  `quiet_watch` showing `PREPARING REPORT` instead of suppressing
  routine traffic -- it was a label with no actual enforcement. Fixed
  (`isSuppressedByDiscipline()`, shared by the transmission gate and the
  status line so they can't drift apart) and re-verified live: all three
  acceptance criteria confirmed in one final pass across
  normal/quiet_watch/radio_silence/powered-off, including a genuine,
  non-hardcoded `NO CHANGE SINCE LAST REPORT` appearing on a repeat
  Bridge report.
