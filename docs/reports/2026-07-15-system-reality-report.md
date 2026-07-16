# System Reality Report

Date: 2026-07-15

Prepared for: Captain / Lieutenant

Scope: repository discovery, live services, ports, storage, endpoints, tests,
unreachable components, and stale or duplicate records. This is a consolidation
report, not a new commissioning or implementation record.

## Repository Discovery

- Repository root: `/home/cgl/dev/monad`
- Branch: `agent/living-world-intake-v0-1`
- HEAD: `6c179f5` `Claim SR-01`
- Remote: synchronized with `origin/agent/living-world-intake-v0-1`
- Working tree: clean at the time of this report

Claim coordination is active through `docs/engineering-orders/queue.md`. The
SR-01 claim was recorded and pushed before this report was assembled.

## Live Services and Ports

The following services are active:

- `fleetcore-serve`
- `world-intake`
- `living-fleet`
- `living-fleet-memory`
- `living-fleet-memory-reflect.timer`
- `monad-watchman`
- `living-captain-status`
- `caddy`

Verified listeners:

| Port | Listener | Notes |
|---|---|---|
| 80 | Caddy | public HTTP |
| 443 | Caddy | public HTTPS |
| 4771 | `fleetcore-serve` | loopback FleetCore snapshot/command server |
| 4772 | `living-fleet-memory` | loopback memory inspector |
| 4773 | `world-intake` | loopback intake API |
| 4774 | `living-captain-status` | loopback Captain status API |

Verified endpoints:

- `http://127.0.0.1:4771/snapshot` -> 200
- `http://127.0.0.1:4773/proposals?status=pending` -> 200
- `http://127.0.0.1:4774/status` -> 200
- `https://cameronlampley.com/` -> 200

## Storage and Databases

Observed durable state locations:

- `data/fleetcore/`
  - `world.json`
  - `events.jsonl`
  - `checkpoints/`
  - `snapshots/snapshot.json`
- `data/living-fleet/`
  - `runtime.json`
  - `memory.db`
- `data/world-intake.sqlite3`
- `data/living-captain/`
  - `state.json`
  - `actions.jsonl`

Current repository evidence and earlier verification reports together show:

- FleetCore event history is bounded in live state and remains replayable from
  `events.jsonl`.
- World Intake is SQLite-backed and keeps source / assertion / adjudication /
  canon history separate.
- Living Captain persists its state and action log under `data/living-captain/`
  and exposes a read-only status surface at `127.0.0.1:4774`.

## Containers

No container inventory was confirmed for this report.

- `docker ps` could not be queried from this session because access to the
  Docker socket was denied.
- `podman` is not installed on this host.

This leaves the container boundary unverified in practice, even though the
service and port boundary is clear.

## Tests and Verification Record

No destructive tests were run for this consolidation pass. The report is built
from earlier verified records and the live endpoint checks above.

The active verification record in the repo currently includes:

- `docs/reports/2026-07-15-phase1-sweep-and-corrections.md`
  - confirms issue #6 is live and deployed
  - confirms issue #13 is live and deployed
  - confirms Living Captain wake-sequence scope is deliberate and partial by
    design
  - records the `fleetcore-live` cursor fix and the bridge source sync
- `docs/reports/2026-07-14-captain-issue-report.md`
  - historical HOLD report, now superseded by the commissioning closeout
- `docs/reports/2026-07-14-post-commissioning-closeout.md`
  - records the commissioned baseline, evidence set, and residual risks
- `docs/reports/2026-07-15-feature-matrix.md`
  - compiles the current §1-21 status map

Relevant test outcomes already recorded there:

- World Intake: 12/12 tests pass
- Living Fleet and captain-memory: 30/30 tests pass
- Living Captain: 9/9 tests pass
- FleetCore formatting, clippy, integration, replay, persistence, canon, and
  wire-contract tests pass

## Unreachable or Not Yet Fully Inspected

The following were not fully inspected in this consolidation pass:

- container runtime inventory, due lack of Docker socket access
- any deeper classification of stale or duplicate worktrees beyond the earlier
  partial audit recorded in the feature matrix
- any subsystem not already covered by the phase sweep and issue reports

## Stale or Duplicate Records

No records were deleted. Historical documents remain in place with resolution
notes where needed.

Notable record relationships:

- `docs/reports/2026-07-14-captain-issue-report.md` is historical and is
  superseded by `docs/reports/2026-07-14-post-commissioning-closeout.md`
  without being rewritten out of existence.
- `docs/reports/2026-07-15-phase1-sweep-and-corrections.md` corrects earlier
  misclassification of issue #6 and issue #13 as pending.
- `docs/engineering-orders/living-captain-v0.1.md` and
  `docs/engineering-orders/living-captain-v0.2.md` are intentionally sequenced;
  v0.2 does not replace v0.1, it extends the spine with custody and spend
  boundary checks.
- `docs/engineering-orders/queue.md` is live coordination state for non-
  privileged work and is used by the current claim protocol.

## Short Verdict

The repo is in a good operational shape:

- the live services needed for the current slice are up
- the public site and the internal loopback APIs respond normally
- the relevant reports and matrices are present and internally consistent
- the main remaining blind spot in this pass is container inventory

The campaign can proceed from here without additional discovery on the core
web/service path.
