# Feature Matrix — Monad Master Packet §21

Date: 2026-07-15

Prepared by: Claude (session claiming `FM-01` via
`docs/engineering-orders/queue.md`)

Status vocabulary is exactly Master Packet §1's six terms: **Verified
Existing** / **Existing but Unverified** / **Required Next** / **Design
Required** / **Deferred** / **Rejected or Superseded**.

This compiles material already verified in
[`2026-07-15-phase1-sweep-and-corrections.md`](2026-07-15-phase1-sweep-and-corrections.md),
[`2026-07-14-captain-issue-report.md`](2026-07-14-captain-issue-report.md),
[`2026-07-15-captain-issue-report.md`](2026-07-15-captain-issue-report.md),
and `docs/engineering-orders/living-captain-v0.1.md` / `-v0.2.md`. Where a
section was not touched this session, it is marked **not yet inspected**
rather than guessed at.

| ID | Feature / Module | Requirement Source | Status | Location | Tests | Dependencies | Priority | Acceptance Criteria | Owner | Verified |
|---|---|---|---|---|---|---|---|---|---|---|
| FC-01 | FleetCore vessel-event retention (~2,000 events, bounded) | §5 | Verified Existing | `fleetcore/src/world.rs` (`default_vessel_event_retention`) | `fleetcore/tests/vessel_events_retention.rs` | fleetcore-serve | High | Live snapshot shows `vessel_event_retention` + bounded `vessel_events` array | — | 2026-07-15 |
| FC-02 | Checkpoint + restart recovery | §5 | Verified Existing | `fleetcore/src/persistence.rs` | `checkpoint_plus_event_tail_replays_to_current_world`, `checkpoint_retention_keeps_newest_and_genesis` (`tests/determinism.rs`) | fleetcore-serve | High | Both tests pass | — | 2026-07-15 |
| FC-03 | Canon command validation (schema/authority/idempotency) | §5 | Verified Existing | `fleetcore/src/world.rs`, `command.rs` | `tests/canon.rs` (5/5 pass) | fleetcore-serve | High | Tests pass | — | 2026-07-15 |
| FM-A | Escort posture / deterministic patrol behaviors | §6 | Verified Existing (implemented posture set; some §6 names are only covered compositionally) | `fleetcore/src/agent.rs` (`EscortPosture` enum), `fleetcore/src/world.rs` (`agent_station`) | `fleetcore/tests/living_fleet.rs` | fleetcore-serve | Medium | Literal posture variants exist for `screen` (`AdvanceScreen`), `investigate` (`InvestigateContact`), `avoid` (`EmergencySeparation`), and escort/formation-maintenance behaviors (`HoldStation`, `RecoverFormation`, `WidenFlank`, `CoverRear`). The §6 names `orbit`, `follow`, `intercept`, and `return` have no direct enum variant. §6's `maintain sector` is covered only compositionally, not by a literal variant. | — | 2026-07-15 |
| BR-01 | Bridge (as built: instrument-compositing console, not a scenario/Command Center) | §7 | **Rejected or Superseded (for the Command Center half of §7); Verified Existing (for the mission-control-unification half)** | `toys/bridge/` (520 lines: `index.html` + `app.js`, static, no backend) | none applicable -- static HTML/CSS/JS, no test suite | none (`README.md`: "requires no backend, database, authentication, build step, or package manager") | Medium | **Confirmed absent:** scenario creation, world selection, vessel placement, save/load, validation, launch -- zero matches anywhere in `app.js`/`index.html` for scenario/save/load/validate/launch, confirmed by direct grep, not inference. **Confirmed present:** unified live map (Fleet Motion + Periscope composited, mutually-selecting via shared browser-local state), a contact roster, an engineering status rail, tab-based station switching -- this is real and matches §7's "unify live map/status/events" language, just not its "Command Center" scenario-building language. Bridge is a compositing dashboard over other live instruments, not an authoring tool | — | 2026-07-15 |
| WI-01 | World Intake V0.1 baseline (ingest/extract/queue/review/provenance, /adjudications -> FleetCore) | §8 | Verified Existing | `tools/world-intake/world_intake.py` | 12/12 pass, isolated | world-intake.service, FleetCore | High | 12 tests pass, HTTP 200 on public page and `/proposals`, disk/Qdrant healthy | — | 2026-07-15 |
| PS-01 | Periscope (visual layer over verified state) | §8 | Existing but Unverified | `toys/periscope/`, `web/toys/periscope/` | none isolated | — | Low | Deploy-drift check only (passed, `EP-01`-adjacent); day/night, contacts, tactical overlays not verified | — | drift-clean, feature scope not verified |
| LF-01 | Living Fleet per-vessel persistent runtime | §6 / §9 | Verified Existing | `tools/living-fleet/captain_runtime.py` (`CaptainRuntime`) | 30/30 per 2026-07-15 captain issue report | living-fleet.service | High | Live systemd service, real per-cycle FleetCore observation | — | 2026-07-15 |
| LC-01 | Living Captain wake sequence (persistent command presence) | §9 | Verified Existing (intentionally partial scope) | `tools/living-captain/captain.py`, `sight.py`, `captain_state.py` | 9/9 (`test_sight.py`, `test_captain.py`, `test_captain_v02.py`) | living-captain-status.service (loopback status API only) | High | `observe()` inspects 2 of 8 things §9 names (FleetCore snapshot, World Intake pending) by V0.2 design -- see `docs/engineering-orders/living-captain-v0.2.md`; widening scope is a documented future V0.3-style decision, not a current gap | — | 2026-07-15 |
| LC-02 | Living Captain status API (public, read-only) | §9 | Verified Existing | `tools/living-captain/status_server.py`, `scripts/living-captain-status.service` | n/a (read-only view) | Caddy | Medium | Loopback (`127.0.0.1:4774/status`) and public (`/living-captain-api/status`) both return correct `captain_id`; installed and verified 2026-07-15 | — | 2026-07-15 |
| WO-01 | Watch Officer (read-only observer agent) | §10 | Required Next / Design Required | none | none | — | Medium | Confirmed this session: the only "Watch Officer" occurrence anywhere is a bare role-name string in `world_intake.py`'s `assign_role` check -- no implementation exists | — | 2026-07-15 (confirmed absent) |
| MEM-01 | Memory (episodic/semantic/procedural/relational/narrative) + retrieval | §11 | Verified Existing (five memory kinds are implemented; retrieval is local TF-IDF plus metadata/recency/salience/mission/relationship/type gating) | `tools/living-fleet/memory/` | `27/27` passing (`PYTHONPATH=tools/living-fleet python3 -m unittest discover -s tools/living-fleet/memory/tests -p 'test_*.py'`) | living-fleet-memory.service; Qdrant is not part of the package code path | Medium | Five first-class stores exist: episodic, semantic, procedural, relational, narrative. Retrieval is purpose-driven and combines exact table/filter lookup, subject filtering, recency decay, semantic similarity via local TF-IDF cosine, salience ranking, relationship context, and status gating (`active` only). The package does not implement a Qdrant-backed retrieval path; the docs mention Qdrant as a broader system dependency, not this module's source of truth. | — | 2026-07-15 |
| AG-01 | Agent registry, authority envelopes, task-packet messaging | §12 | Existing but Unverified | `tools/engineering-comms/` (schema tests exist) | `test_schema.py` exists, not isolated this session | — | Medium | Not yet inspected against the full identity/authority/messaging-lifecycle list | — | not yet inspected |
| Q-01 | Shared two-agent task queue (this session's own work) | §12 | Verified Existing | `AGENTS.md`, `docs/engineering-orders/queue.md`, `CLAUDE.md` pointer | protocol dogfooded live (FM-01 claimed via the documented steps, clean push) | — | — | Claim/push/back-off cycle demonstrated working end-to-end | — | 2026-07-15 |
| PKT-01 | Engineering packet lifecycle (drafted->reviewed->authorized->assigned->...->recorded) | §13 | Existing but Unverified as a formal system; demonstrated ad hoc | conversation-level packets this session (e.g. `FC-LIVE-01`) | n/a | — | Medium | Practiced informally and successfully this session (draft -> authorize -> execute -> verify -> record), but no standing packet-tracking system exists in the repo itself | — | practiced, not systematized |
| REPO-01 | Repository discovery, dirty-state awareness, rollback | §14 | Verified Existing (as practice, this session) | git itself; `docs/commissioning-handoff.md` for privileged rollback | n/a | — | High | Every fix this session used git status/log/diff before acting, and `cmd.sh`'s evidence-capture + rollback procedure is a real, working instance | — | 2026-07-15 |
| WT-01 | `monad-issue17-slice-a` (issue #17), `monad-issue18-slice-b` (issue #18), `monad-history-integration` | §21 | Rejected or Superseded | see paths above | n/a | — | Low | Issues #17 and #18 are both **CLOSED** on GitHub; both pursued a "retain the complete V1 array, no compaction authorized" full-history design (explicit in #17's issue body). What actually shipped to `monad` main (`acc5b21`) is the simpler bounded-`vessel_event_retention` approach instead -- confirmed `monad-history-integration`'s `world.rs` has zero mentions of `vessel_event_retention`. No open PRs exist for any of the three branches (`codex/history-v2-integration`, `codex/issue-17-slice-a`, `agent/issue-18-slice-b`). Safe to archive; **not deleted by this task** -- inspection/classification only, per GA-01's scope | — | 2026-07-15 |
| WT-02 | `monad-slice-g` (branch `agent/issue-16-slice-g-auth`) | §21 / §16-adjacent | **Required Next -- do not treat as stale** | `/home/cgl/dev/monad-slice-g` | n/a | GitHub issue #16 | **High** | Issue #16 ("Require authentication and authorization for FleetCore authoritative commands") is **still OPEN** and explicitly declares itself a release blocker: *"Do not commission the Issue #6 history implementation until this issue is complete."* `monad-slice-g`'s last commit, "Default-deny FleetCore command mutations," maps directly to this open issue's requirements. This directly contradicts `CLAUDE.md`'s current stated policy ("Security hardening is not the priority here... don't gate shipping on security review") -- flagging the contradiction rather than resolving it unilaterally. No open PR exists yet for this branch despite the unmerged work. | — | 2026-07-15 |
| WT-03 | `.claude/worktrees/scout-screen-mode` (locked, branch `worktree-scout-screen-mode`) | §21 | Existing but Unverified | `.claude/worktrees/scout-screen-mode` | n/a | — | Low | Could not inspect directly this session -- git refuses with "dubious ownership" on this path, requiring a `safe.directory` config change not made here (out of scope for an inspection-only task). Locked worktrees are normally held because work is in progress; treat as active until someone with access confirms otherwise | — | not fully inspected (access-blocked) |
| WM-01 | Watchman (disk, memory, processes, endpoints, databases, event progress, stale services, failed restarts) | §16 | **Verified Existing for 2 of 8 named checks; Required Next for the rest** | `watchman.py` (full file read this session) | none applicable -- it's a heartbeat logger, not a test suite | monad-watchman.service | Medium | **Present:** disk usage (`disk_status`, warns under 10% free), Qdrant health (`qdrant_health`, hits `127.0.0.1:6333/healthz` only). Also logs git commit hash, uptime, hostname (useful, but not among §16's named checks). **Confirmed absent, not merely unverified:** memory usage, process monitoring, endpoints for the other 5 live services (fleetcore-serve, world-intake, living-fleet-memory, living-captain-status, living-fleet), databases beyond Qdrant (world-intake's sqlite3, FleetCore's `events.jsonl`/checkpoints), event/tick progress tracking, stale-service detection, failed-restart detection. It is a 300-second heartbeat-and-disk-and-Qdrant logger, not the fuller inspector §16 describes | — | 2026-07-15 |
| CT-01 | Cost tracking (provider/agent/task/usage/cost/budget) | §17 | Required Next / Design Required | none | none | — | Low | Confirmed this session: no systemic ledger exists; only unrelated per-call cost params in `tools/img2asset/backends/replicate.py` | — | 2026-07-15 (confirmed absent) |
| TOY-01 | Toy source/deploy sync (`toys/` <-> `web/toys/`) | implicit across §7/§8 | Verified Existing (actively maintained this session) | `toys/*`, `web/toys/*` | n/a | — | High | `fleetcore-live` (real bug, fixed), `bridge` (source synced), `watchbook` (confirmed deliberate defer), rest confirmed expected/in-sync | — | 2026-07-15 |

## Sections not yet inspected at all this session

No row above covers these directly; each needs its own pass before this
matrix can claim full §1-21 coverage:

- **§15 Doctrine and recovery** -- doctrine-entry format, incident
  management, Isolation Mode, two-person authorization: not inspected.
- **§18 Experiments and diagnostic methods**: not inspected.
- **§19 UX principles**: not inspected as a structured audit (informally
  touched via the toy-sweep, but no dedicated pass).
- **§20 Delivery order (phase gates I-VI)**: not evaluated as a
  checklist against current repo state.
- **§2-4 (mission/doctrine/architecture narrative sections)**: these are
  framing, not independently verifiable features -- no matrix rows
  apply.

## Notes on method

- Every "Verified Existing" row above traces to a test run, a live curl
  check, or a direct file read performed this session or the
  immediately preceding one (2026-07-14 captain issue report), not to
  memory or the Master Packet's own narrative.
- "Existing but Unverified" is used specifically where source code or a
  service is confirmed to exist but its behavior against the named
  requirement was not exercised.
- "Required Next" / "Design Required" is reserved for confirmed
  absences (Watch Officer, cost tracking), not merely unverified areas.
