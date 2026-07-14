# Captain Issue Report

Date: 2026-07-14

Prepared for: Captain

Scope: Monad post-reboot, Living Fleet Effort B, and Living World Intake V0.1

## Executive status

The code and public static surfaces are integrated, tested, merged, and clean.
Living World Intake is not yet operational because its privileged commissioning
package has not been executed. No prose has mutated FleetCore canon and no
intake proposal has been automatically approved.

## Action required from the Lieutenant

Run:

```sh
/home/cgl/cmd.sh
```

The package is pinned to the current clean commit. It captures rollback
evidence, restarts FleetCore on the canon-aware binary, activates the memory
latency fix, installs the authenticated World Intake API and Caddy route,
installs Watchman, verifies public and loopback paths, proves unauthorized
adjudication is rejected, archives itself, and flushes the live handoff.

## Active engineering issue

### FleetCore vessel-event history grows without a bound

GitHub: [Issue #6](https://github.com/aleuf05/monad/issues/6)

Observed evidence:

- More than 160,000 vessel events in the persisted world during the latest audit.
- `world.json` approximately 29 MB and rewritten every simulation tick.
- `data/fleetcore` approximately 3.1 GB across current state and retained
  checkpoints.
- The complete event array is also included in live snapshots and WebSocket
  broadcasts.

Impact: no current correctness failure, but storage, serialization, per-tick
write amplification, and network cost grow continuously.

Recommended design: preserve complete append-only event history separately,
while bounding the recent event tail embedded in current state, checkpoints,
and live snapshots. Confirm consumer requirements before changing the wire
contract. Do not fold this into the commissioning rollout.

## Codex follow-up queue

- [Issue #13: Verify Living World Intake after privileged commissioning](https://github.com/aleuf05/monad/issues/13)
  is explicitly blocked on the Lieutenant-run handoff. It defines service,
  authentication, idempotency, provenance, and safe live-command checks.
- [Issue #14: Prove captain-memory reflection crash atomicity](https://github.com/aleuf05/monad/issues/14)
  tracks the remaining scratch-only fault-injection evidence gap. It must never
  run destructive tests against the production memory database.

## Commissioning gate

The installed `fleetcore-serve` process predates the new canon command family.
The on-disk release binary is current, but the service must be restarted by the
privileged handoff. Until then:

- live FleetCore rejects `apply-canon-change` as an unknown command;
- `world-intake.service` is not installed/running;
- `/world-intake-api/*` is not active through Caddy;
- the public review page remains safely in non-canonical demo mode;
- the optimized captain-memory inspector has not been restarted;
- Watchman is not installed as a persistent service.

This is an activation gate, not an unresolved code defect.

## Resolved findings

- Original intake sources are immutable and byte-preserved.
- Nine recruits, roles, Deck 7 stations, claimed capabilities, requests,
  permissions, identity ambiguity, and flavor are separated.
- Capabilities enter canon unverified.
- Vance's scram assignment does not grant scram authority.
- Reactor startup remains a pending authorization attached to
  `vessel.monad`; no reactor-start event is created.
- Ambiguous aliases require an explicit Captain link decision and existing
  entity ID; bare approval fails closed.
- The extracted alias text is compiled correctly.
- Approved proposals compile to FleetCore's typed command path with complete
  provenance.
- Retries are idempotent; restart/replay and compensating corrections retain
  history.
- Bridge's stale public Watchbook sidebar link now opens Ship's Log.
- `web/status/fleet.json` is confirmed active as Fleet Command's separate
  static physical-fleet roster, not dead data.
- Shared-workspace collision procedures now require isolated worktrees for
  concurrent engineering sessions.

## Validation record

- 12/12 World Intake acceptance tests pass.
- 30/30 Living Fleet and captain-memory tests pass.
- FleetCore formatting and Clippy with warnings denied pass.
- All FleetCore integration, replay, persistence, canon, and wire-contract
  tests pass.
- Public Bridge and World Intake pages return HTTP 200.
- Watchman's unprivileged probe reports disk OK and Qdrant healthy.
- Repository and GitHub PR state are clean; all implementation PRs are merged.

## Deferred evidence gaps

- Captain-memory crash-mid-write safety is strongly supported by SQLite WAL
  behavior and restart tests, but a kill landing inside a multi-row reflection
  write was not directly observed. No corruption or partial write has been
  seen.
- `fwupd` services leave systemd reporting `degraded`; Monad services are
  healthy and firmware maintenance is outside this engineering scope.
- Older watch logs contain historical limitations that have since been fixed.
  They remain unchanged as historical records unless a later resolution note
  is necessary.

## Captain recommendation

Execute the pinned commissioning package, verify its completion marker and
evidence directory, then treat Issue #6 as the next engineering design task.
Do not approve live intake proposals until commissioning verification is green.

Current readiness: **HOLD FOR COMMISSIONING**.
