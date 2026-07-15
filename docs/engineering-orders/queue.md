# Shared engineering task queue

Protocol: see [`AGENTS.md`](../../AGENTS.md) at the repo root. Non-privileged,
git-only tasks only — nothing requiring `sudo` (that stays in `cmd.sh` /
`commissioning-handoff.md`).

## FM-01 — Feature Matrix compilation

- Status: done@2026-07-15T13:52:00Z
- Source: Master Packet §21
- Output: `docs/reports/2026-07-15-feature-matrix.md`
- Method: synthesize, don't re-audit — compile from
  `docs/reports/2026-07-15-phase1-sweep-and-corrections.md`, both captain
  issue reports, and `docs/engineering-orders/living-captain-v0.1.md` /
  `-v0.2.md`. One row per feature: requirement source, status, location,
  tests, dependencies, priority, acceptance criteria, owner, verification
  date. Status vocabulary is exactly Master Packet §1's six terms —
  Verified Existing / Existing but Unverified / Required Next / Design
  Required / Deferred / Rejected or Superseded. Every §1-21 section gets a
  row or an explicit "not yet inspected" note.
- Claimed by: claude
- Evidence: commit `2850390`, `docs/reports/2026-07-15-feature-matrix.md`

## AM-01 — Architecture Map

- Status: queued
- Source: Master Packet §21
- Output: `docs/reports/2026-07-15-architecture-map.md`
- Method: map derived from this session's inspected reality, not
  remembered design. The 6 live systemd services and their actual
  dependency edges (fleetcore-serve; world-intake; living-fleet;
  living-fleet-memory + its reflect timer; monad-watchman;
  living-captain-status), Qdrant (6333/6334), Caddy routing (bare-root
  only, `/monad/portainer/*` exception), the toy `toys/` vs `web/toys/`
  split, and the canonical-repo confirmation
  (`/home/cgl/dev/monad` via `WorkingDirectory`). Every edge must trace
  to something actually checked (systemd unit files, live curl checks,
  git history) — no inferred/assumed connections.
- Claimed by: —
- Evidence: —

## GA-01 — Stale/duplicate worktree audit

- Status: queued
- Source: Master Packet §21 ("identify dead, broken, stale, and
  duplicate systems"); flagged but never resolved at the very start of
  this session's sweep
- Output: a section in `docs/reports/2026-07-15-feature-matrix.md` (or
  its own short report if it turns up enough to warrant one)
- Method: `/home/cgl/dev/monad-history-integration`,
  `-issue17-slice-a`, `-issue18-slice-b`, `-slice-g` were confirmed
  early this session to not back any running service (only
  `/home/cgl/dev/monad` does, per every systemd unit's
  `WorkingDirectory`). Determine for each: last commit date, whether
  it's ahead/behind/merged relative to `monad`'s current HEAD, and
  whether it corresponds to an open PR or issue. Same treatment for the
  locked worktree at `.claude/worktrees/scout-screen-mode` (branch
  `worktree-scout-screen-mode`) — check whether that work landed
  already or is still active. **Do not delete or unlock anything** —
  this task is inspection and classification only; removal is a
  separate, explicitly-authorized action.
- Claimed by: —
- Evidence: —

## WM-01 — Watchman scope verification

- Status: queued
- Source: Master Packet §16 ("A Watchman process should inspect disk,
  memory, processes, endpoints, databases, event progress, stale
  services, and failed restarts")
- Output: a section in `docs/reports/2026-07-15-feature-matrix.md`
- Method: `watchman.py` currently defines `disk_status`, `qdrant_health`,
  `git_commit`, `uptime_seconds`, and a heartbeat logger — confirmed by
  reading the file this session. Verify precisely which of §16's named
  checks (memory, processes, endpoints beyond Qdrant, databases beyond
  Qdrant, event progress, stale services, failed restarts) are actually
  implemented vs. absent. Classify using Master Packet §1's vocabulary,
  don't guess from the function names alone — read what each function
  body actually does.
- Claimed by: —
- Evidence: —

## SR-01 — System Reality Report consolidation

- Status: done@2026-07-15T13:46:14Z
- Source: Master Packet §21 (named as its own deliverable, separate
  from the Feature Matrix)
- Output: `docs/reports/2026-07-15-system-reality-report.md`
- Method: this is an index/consolidation task, not new investigation —
  most of the raw material already exists across
  `docs/reports/2026-07-15-phase1-sweep-and-corrections.md` and the two
  captain issue reports. Pull it into the specific shape §21 asks for:
  repository discovery (branches, dirty state, commits), services/ports/
  containers, databases, endpoints, tests/failures, unreachable
  components, stale/duplicate documents (link GA-01's findings once
  done). Where §21 asks for something not yet covered by existing
  reports, mark it "not yet inspected" rather than filling the gap with
  assumption.
- Claimed by: codex
- Evidence: `docs/reports/2026-07-15-system-reality-report.md`

## WO-01 — Watch Officer status (§10)

- Status: queued
- Source: Master Packet §10 (read-only observer agent: may observe
  FleetCore/services/events/alerts/contradictions, draft logs, summarize
  activity, recommend escalation; may not issue commands, modify state,
  restart services, edit canon, suppress alerts, or promote inference to
  fact)
- Output: a section in `docs/reports/2026-07-15-feature-matrix.md`
- Method: confirmed this session — the only occurrence of "Watch
  Officer" anywhere in the codebase is a bare role-name string inside
  `tools/world-intake/world_intake.py`'s `assign_role` predicate check
  (line 90), not an implementation of the component. Classify as
  "Required Next" or "Design Required" (Master Packet §1 vocabulary) —
  not "Existing but Unverified," since there is nothing to verify.
- Claimed by: —
- Evidence: —

## EP-01 — Escort posture / deterministic patrol mapping (§6)

- Status: queued
- Source: Master Packet §6 (candidate deterministic patrol behaviors:
  orbit, screen, follow, intercept, investigate, avoid, escort, maintain
  sector, return)
- Output: a section in `docs/reports/2026-07-15-feature-matrix.md`
- Method: `fleetcore/src/agent.rs` defines a real `EscortPosture` enum
  (`HoldStation`, `AdvanceScreen`, `WidenFlank`, `CoverRear`,
  `InvestigateContact`, `RecoverFormation`, `EmergencySeparation`),
  implemented in `world.rs`. Map each variant against §6's named list
  (e.g. `AdvanceScreen` -> screen, `InvestigateContact` -> investigate)
  and identify which of §6's named behaviors (orbit, follow, intercept,
  maintain sector, return) have no corresponding variant at all, rather
  than assuming the whole section is unimplemented.
- Claimed by: —
- Evidence: —

## CT-01 — Cost tracking status (§17)

- Status: queued
- Source: Master Packet §17 (provider, agent, task, estimated usage,
  direct cost, daily/monthly totals, budget limits, local vs. cloud
  execution, resulting value)
- Output: a section in `docs/reports/2026-07-15-feature-matrix.md`
- Method: confirmed this session — no systemic cost/budget ledger exists
  anywhere in the repo. The only cost-related hits are
  `tools/img2asset/backends/replicate.py`'s per-call Replicate API cost
  parameters, which is a single external-API cost detail, not the
  provider/agent/task ledger §17 describes. Classify as "Required Next"
  or "Design Required," not "Existing but Unverified."
- Claimed by: —
- Evidence: —
