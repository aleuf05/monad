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

- Status: done@2026-07-15T14:20:00Z
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
- Claimed by: codex
- Evidence: `docs/reports/2026-07-15-architecture-map.md`

## GA-01 — Stale/duplicate worktree audit

- Status: done@2026-07-15T14:22:00Z
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
- Claimed by: claude
- Evidence: commit `3df111e`, `docs/reports/2026-07-15-feature-matrix.md` rows `WT-01`/`WT-02`/`WT-03`. **Notable: surfaced that issue #16 (still open) contradicts CLAUDE.md's current security posture -- worth the Lieutenant's attention.**

## WM-01 — Watchman scope verification

- Status: done@2026-07-15T14:32:00Z
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
- Claimed by: claude
- Evidence: commit `e108ed4`, `docs/reports/2026-07-15-feature-matrix.md` row `WM-01` — confirmed 1.5 of 8 named checks present, rest genuinely absent

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

- Status: done@2026-07-15T14:05:00Z
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
- Claimed by: claude
- Evidence: `docs/reports/2026-07-15-feature-matrix.md`, row `WO-01`

## EP-01 — Escort posture / deterministic patrol mapping (§6)

- Status: done@2026-07-15T14:40:00Z
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
- Claimed by: codex
- Evidence: `docs/reports/2026-07-15-feature-matrix.md` row `FM-A`

## CT-01 — Cost tracking status (§17)

- Status: done@2026-07-15T14:05:00Z
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
- Claimed by: claude
- Evidence: `docs/reports/2026-07-15-feature-matrix.md`, row `CT-01`

## MEM-01 — Memory subsystem verification (§11)

- Status: done@2026-07-15T14:55:00Z
- Source: Master Packet §11 (episodic/semantic/procedural/relational/
  narrative memory types; retrieval combining exact lookup, metadata,
  recency, semantic similarity, mission relevance, relationships, type,
  salience, and verification status; local TF-IDF and Qdrant coexisting)
- Output: update the `MEM-01` row in `docs/reports/2026-07-15-feature-matrix.md`
  (currently marked "not yet inspected" from FM-01's first pass)
- Method: `tools/living-fleet/memory/` has real test files
  (`test_identity.py`, `test_embeddings.py`, `test_relational.py`,
  `test_salience.py`, `test_reflection.py`, `test_store.py`,
  `test_context.py`, `test_conversation.py`, `test_belief_revision.py`,
  `test_cross_captain_sharing.py`, `test_seed_import.py`,
  `test_reflection_atomicity.py`, `test_service_integration.py`) --
  read the actual source files (not just test names) to determine which
  of §11's five memory types and which retrieval-combination dimensions
  are genuinely implemented vs. absent, same rigor as `WM-01`. Don't
  infer coverage from test file names alone.
- Claimed by: codex
- Evidence: `docs/reports/2026-07-15-feature-matrix.md` row `MEM-01`

## BR-01 — Bridge full-scope verification (§7)

- Status: done@2026-07-15T15:12:00Z
- Source: Master Packet §7 (Command Center + Bridge: scenario creation,
  world selection, vessel placement, routes, formations, save/load,
  validation, launch; mission control showing intent/objective/actors/
  constraints/results; unified live map, active mission, events/alerts,
  agents/service health, pause controls, watch/conn)
- Output: update the `BR-01` row in `docs/reports/2026-07-15-feature-matrix.md`
  (currently "Existing but Unverified," only checked for toy deploy-drift,
  not feature completeness)
- Method: read `toys/bridge/index.html` / `app.js` (or equivalent) and
  whatever backs it, and classify each of §7's named capabilities as
  present/absent/partial. Don't infer from the UI shell alone -- confirm
  whether scenario creation, save/load, and validation are real or
  placeholder.
- Claimed by: claude
- Evidence: commit `dd6769e`, `docs/reports/2026-07-15-feature-matrix.md` row `BR-01` — Command Center scenario/save-load/launch confirmed absent; mission-control-unification half confirmed present

## PS-01 — Periscope full-scope verification (§8)

- Status: done@2026-07-15T15:30:00Z
- Source: Master Packet §8 (labels, headings, wakes, weather,
  visibility, contacts, inspection, camera follow, bridge view, tactical
  overlays, event-based captions, visual record capture; rendering must
  never alter authoritative state)
- Output: update the `PS-01` row in `docs/reports/2026-07-15-feature-matrix.md`
  (currently only checked for toy deploy-drift, not feature completeness)
- Method: read the actual Periscope source (`toys/periscope/`) and
  classify each named capability present/absent/partial. Also confirm
  the "never alter authoritative state" invariant -- check whether
  anything in the Periscope client issues write/command calls anywhere.
- Claimed by: claude
- Evidence: commit `55e96c9`, `docs/reports/2026-07-15-feature-matrix.md` row `PS-01` — most capabilities present, weather/camera-follow/record-capture absent, read-only invariant confirmed

## AG-01-VERIFY — Agent registry / messaging full-scope verification (§12)

- Status: done@2026-07-15T15:43:00Z
- Source: Master Packet §12 (stable identity, role, runtime, authority
  envelope, tool access, assignment, status, memory rules, cost record,
  activity record, failure history per agent; task packets,
  acknowledgement, clarification, progress, evidence, exceptions,
  completion, bounded refusal, escalation)
- Output: update the `AG-01` row in `docs/reports/2026-07-15-feature-matrix.md`
  (currently "Existing but Unverified," `test_schema.py` noted but not run)
- Method: read `tools/engineering-comms/` source and its schema, run
  `test_schema.py`, and classify which of §12's per-agent fields and
  message types are genuinely defined/enforced vs. absent. This session's
  own `docs/engineering-orders/queue.md` + `AGENTS.md` protocol is a real,
  separate, working instance of part of §12 -- note that relationship
  rather than double-counting it.
- Claimed by: claude
- Evidence: `docs/reports/2026-07-15-feature-matrix.md` row `AG-01`

## DOC-01 — Doctrine and recovery audit (§15)

- Status: done@2026-07-15T15:43:00Z
- Source: Master Packet §15 (doctrine-entry format with name/version/
  origin/rationale/scope/status/supersession/evidence/approval; incident
  management; Isolation Mode; two-person authorization for sensitive
  operations)
- Output: a new section in `docs/reports/2026-07-15-feature-matrix.md`
  (§15 currently has zero rows -- listed as "not yet inspected")
- Method: check whether any doctrine entries in the repo actually follow
  the named format (search `docs/` for doctrine-like documents), whether
  any incident-management procedure exists beyond `docs/commissioning-handoff.md`'s
  rollback steps, and whether "Isolation Mode" or "two-person
  authorization" exist anywhere as real mechanisms or only as Master
  Packet language.
- Claimed by: codex
- Evidence: `docs/reports/2026-07-15-feature-matrix.md` row `DOC-01`

## EXP-01 — Experiments and diagnostic methods audit (§18)

- Status: done@2026-07-15T15:43:00Z
- Source: Master Packet §18 (experiment tracking: hypothesis, setup,
  variables, outputs, observations, failures, interpretation,
  repeatability; Human-Architect-Operator interface; recursive incident
  archaeology; Hazardous Conceptual Material handling)
- Output: a new section in `docs/reports/2026-07-15-feature-matrix.md`
  (§18 currently has zero rows)
- Method: search the repo for anything resembling structured experiment
  records (check `docs/research/`, `archive/`). Classify what exists vs.
  what's purely aspirational language in the Master Packet.
- Claimed by: codex
- Evidence: `docs/reports/2026-07-15-feature-matrix.md` row `EXP-01`

## UX-01 — UX principles audit (§19)

- Status: done@2026-07-15T15:43:00Z
- Source: Master Packet §19 (naval command language, clear state/
  authority, inspectable evidence, minimal ambiguity, visible separation
  between verified state and interpretation)
- Output: a new section in `docs/reports/2026-07-15-feature-matrix.md`
  (§19 currently has zero rows -- only informally touched via the toy
  sweep, no dedicated pass)
- Method: this one is inherently more subjective than the others --
  focus on what's checkable: does the live site (`cameronlampley.com`)
  visibly distinguish verified/live data from narrative content anywhere
  (e.g. staff.html's fiction vs. fleet.html's live data)? Report what's
  observable, flag what can't be verified objectively rather than
  asserting a UX judgment as fact.
- Claimed by: codex
- Evidence: `docs/reports/2026-07-15-feature-matrix.md` row `UX-01`

## PHASE-01 — Delivery phase-gate checklist (§20)

- Status: done@2026-07-15T15:43:00Z
- Source: Master Packet §20 (Phase I Establish Truth, II Work Loop, III
  Persistent Command, IV Bounded Agents, V Deepen the World, VI
  Productize)
- Output: a new section in `docs/reports/2026-07-15-feature-matrix.md`
- Method: this is pure synthesis from what's already in the Feature
  Matrix and the two Phase I reports -- for each phase, state what's
  verified-done vs. not-started vs. partial, citing existing rows by ID
  rather than re-investigating. Phase I itself is largely covered by
  this session's own work; say so plainly rather than hedging.
- Claimed by: codex
- Evidence: `docs/reports/2026-07-15-feature-matrix.md` row `PH-01`

## DOC-02 — Bounded-timeout amendment to Doctrine 001

- Status: done@2026-07-15T16:05:00Z
- Source: this session's ENG-1 packet incident -- verifying whether
  `node-01/02/03.livingfleet` were real hosts required killing a
  2-minute hung `getent hosts` chain (`exit 143`); a fabricated or
  unreachable target can fail to fail fast, and an unbounded lookup
  becomes a liability (session-stalling) rather than useless-but-safe
  (quick "not found")
- Output: amend `docs/doctrine/001-verification-command-dialect.md` --
  add bounded-timeout verification language under Target 9 (Silent
  Dependency) and/or Target 4 (Stale Readback)'s verification
  requirement
- Method: this is a small, focused addition, not a rewrite. Proposed
  wording: "Verify host/target claims with a bounded lookup, never a
  bare blocking one -- e.g. `timeout 5 getent hosts <host>` or
  `dig +time=2 +tries=1 <host>`. An unbounded hang is not evidence of
  anything, just wasted time; a fabricated or unreachable target should
  fail fast and cheaply, not stall the session." Keep Doctrine 001's
  Status as "Proposed -- pending Lieutenant/Admiral approval" -- this
  amendment doesn't get to self-adopt either.
- Claimed by: claude
- Evidence: `docs/doctrine/001-verification-command-dialect.md`

## GH-01 — Golden Hull / img2asset pipeline verification (§16)

- Status: done@2026-07-15T16:15:00Z
- Source: Master Packet §16 ("The GOLDEN HULL pipeline must preserve
  source assets, Blender files, exports, manifests, SI scale, collision
  envelopes, orientation, validation, versions, and runtime identity
  linkage. Visual assets may not silently redefine simulation
  dimensions.") -- never checked by any of the 14 completed tasks
- Output: a new section in `docs/reports/2026-07-15-feature-matrix.md`
- Method: `tools/img2asset/README.md` describes "Image -> 3D asset
  pipeline... drops a `.glb` into `web/assets/models/` with a manifest
  entry" -- this is very likely what the Master Packet calls "GOLDEN
  HULL" under a different name, but that needs confirming, not
  assuming. Read the actual source and manifest format and classify
  each named requirement (source-asset preservation, SI scale,
  collision envelopes, orientation, validation, versioning, runtime
  identity linkage) present/absent. Specifically check the "may not
  silently redefine simulation dimensions" invariant -- does anything
  validate a generated model's scale against FleetCore's real vessel
  dimensions before it ships?
- Claimed by: claude
- Evidence: `docs/reports/2026-07-15-feature-matrix.md`, `tools/img2asset/README.md`, `tools/img2asset/image_to_asset.py`, `web/assets/models/manifest.json`

## MD-01 — Mission Director verification

- Status: done@2026-07-15T16:15:00Z
- Source: Master Packet §21 (mission control should show current
  intent/objective/actors/constraints/results); never inspected beyond
  a single cursor-bug check on `mission_director.py` earlier this
  session
- Output: a new section in `docs/reports/2026-07-15-feature-matrix.md`
- Method: `tools/mission-director/README.md` describes a real state
  machine over FleetCore's actual events (`vessel_events`), issuing
  only two real commands (`spawn-passive-contact`,
  `record-watch-event`), explicitly never fabricating simulation
  progress. Read `mission_director.py` and `report.py` in full, run
  `test_cursor.py`, and confirm: does the state machine's phase
  tracking actually match what it claims (no fabricated progress), and
  does `report.py` produce output usable as real mission-control
  status, or is it a narrower single-mission demo (Quacken Transit 001)
  not yet generalized?
- Claimed by: claude
- Evidence: `docs/reports/2026-07-15-feature-matrix.md`, `tools/mission-director/README.md`, `tools/mission-director/mission_director.py`, `tools/mission-director/report.py`, `tools/mission-director/test_cursor.py`

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
