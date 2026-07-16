# Post-Commissioning Closeout

Date: 2026-07-14

Verdict: **COMMISSIONED — CONTROLLED OPERATION AUTHORIZED**

This record supersedes the operational conclusion, but not the historical
contents, of `2026-07-14-captain-issue-report.md`.

## Accepted baseline

- Commissioning timestamp: `2026-07-14T04:40:51Z`
- Accepted revision: `8bcb14b6adfb96d13a4e6a5f22ca4175527b84e1`
- Evidence location:
  `/home/cgl/commissioning/living-world-intake-v0.1-20260714T030430Z`
- Rollback source: the `rollback/` subdirectory and `operator-notes.md` in that
  evidence directory
- Acceptance: proposal-only Living World Intake commissioned; FleetCore,
  World Intake, captain memory, Watchman, and Caddy active at the acceptance
  point

The later repository revision `ad0521b` only added the generated World Intake
SQLite database to `.gitignore`; it is not the commissioned code baseline.

## Evidence verification

The package contains the completion marker, captured commissioning script,
accepted revision pin, pre/post snapshots, pre/post service and journal
records, installer output, loopback and public proposal responses, public
review page, memory summary, Watchman result, unauthorized response, rollback
materials, rollback hashes, and operator notes.

The chronology is coherent:

1. Accepted revision committed at `2026-07-14T04:40:12Z`.
2. Final pre-state capture began at `04:40:31Z`.
3. Installer completed and services activated by `04:40:50Z`.
4. Post-state/API evidence was captured through `04:40:51Z`.
5. `restart.completed` was written last at `2026-07-14T04:40:51Z`.

`sha256sum -c rollback-sha256.txt` passes for every listed rollback artifact.
The successful installer record includes 12 passing World Intake tests, a
release FleetCore build, valid Caddy configuration, active services, and the
installed public review location. The proposal responses captured through the
loopback and public routes are byte-identical.

The evidence is sufficient to reconstruct the proposal-only acceptance
decision. It is not a complete standalone archive of all intake state: the raw
source and intake SQLite database remain in the pinned repository fixture and
live additive database, not in the evidence directory.

## Evidence caveats

- `failure.txt` records an earlier failed attempt at `04:38:48Z`. It is stale,
  predates the final successful run, and must not be read as the final verdict.
- Repeated attempts left five rollback checkpoints. The final pre-state world,
  command log, binary, Caddyfile, and newest checkpoint form the relevant
  rollback set, but no single checkpoint is labeled authoritative.
- The rollback hashes pass, but rollback itself was not exercised.
- No pre-existing World Intake or Watchman unit was present, so there are no
  unit-file backups for those newly installed services.
- The service evidence is a point-in-time sample roughly three seconds after
  activation, not soak evidence.

No evidence file was rewritten or removed during closeout.

## Control confirmation

The commissioned database contained 40 pending assertions: 10 identity, 9
assignment, 9 location, 9 claim, 1 request, 1 permission, and 1 flavor. It
contained no compiled commands or recorded intake canon events. FleetCore canon
collections were logically unchanged across the pre/post snapshots.

Each proposal card carries source identity/hash/timestamp, supporting excerpt,
assertion identity, conflict information, individual-approval indication,
command preview, and provenance. Review decisions compile proposals but report
`canon_mutated: false` and `awaiting-fleetcore-submission`; FleetCore remains the
canon owner. Experimental proposals are distinguishable by pending assertion
state and the absence of a FleetCore canon event.

Unauthorized public adjudication returned HTTP 401 with `Captain review
authentication required`. Capabilities remain unverified, authorization
requests remain pending, and no reactor-start event was created.

Replay, persistence, provenance, idempotency, and compensating corrections are
covered by automated tests and the accepted revision. This commissioning run
intentionally did not approve a live proposal, so accepted-command provenance,
committed-canon restart persistence, and compensating replay were not exercised
against production state.

## Residual risks and hardening

### Direct FleetCore command authority

The acceptance log says FleetCore command authority is granted to every
connection and requires no token. World Intake review authentication therefore
does not establish end-to-end authentication for a caller that can reach
FleetCore `/command`. Domain validation and canon provenance checks still
apply, and the service was not changed during closeout.

Disposition: Command must decide and document the intended network and
authentication boundary before routine live canon approval. Do not describe
the direct FleetCore command path as authenticated until evidence supports it.

### Captain-memory reflection atomicity

SQLite WAL and restart tests strongly support safety, but no deterministic kill
landed inside the critical multi-row reflection write.

Disposition: retain as hardening work. Run fault injection only on disposable
copies, require each reflection to be wholly present or absent, and fail on
partial fragments or inconsistent rows. Do not reopen the completed sprint.

### Host degraded state

`fwupd` units cause host-level degraded status. Monad services are healthy.
This is host-maintenance noise; no firmware services were modified.

### Historical watch logs

Old limitations remain preserved as historical truth. Add resolution notes
only when an operator could otherwise mistake a historical limitation for
current state.

## Final disposition

The earlier **HOLD FOR COMMISSIONING** finding is superseded. The commissioned
baseline is identifiable, inspectable, and restorable from hashed artifacts.
Routine proposal review may proceed under Captain control, subject to the
direct FleetCore authority caveat above. Issue #6 remains design work and is
not authorized for implementation by this closeout.
