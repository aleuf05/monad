# Living Fleet V0.1

## Authoritative seam

Living Fleet adds intent above FleetCore's existing deterministic movement,
not a second simulation:

```text
WorldSnapshot -> captain provider -> SubmitEscortIntent
              -> FleetCore validation -> deterministic station target
              -> advance_vessel -> persisted decision + consequence
```

Captains never submit `set-route`. `fleetcore/src/agent.rs` defines the bounded
posture vocabulary; `World::apply_command` validates assignment, enablement,
fleet pause, freshness, text limits, reconsideration horizon, and investigation
target. Accepted and rejected domain decisions both become ordinary replayable
FleetCore command events and durable `agent_decisions` records.

## Postures

- `hold-station`: ordinary loose formation station.
- `advance-screen`: station 1,800 m ahead of Monad.
- `widen-flank`: station 2,200 m abeam.
- `cover-rear`: station 1,600 m astern.
- `investigate-contact`: 650 m observation stand-off from a current passive contact.
- `recover-formation`: tight formation station.
- `emergency-separation`: deterministic target 2,500 m away from the nearest vessel.

Every derived target is checked against FleetCore geography. A target on known
land becomes `recover-formation`. Existing `advance_vessel` remains the sole
movement implementation.

## Runtime

`tools/living-fleet/captain_runtime.py` is one shared process for all three
captains. Each cycle reads FleetCore, refreshes the snapshot before each
decision, submits structured intent through `POST /command`, and persists a
small operational memory under `data/living-fleet/`.

The default `doctrine-fallback-v1` provider gives Alpha forward/contact logic,
Bravo flank logic, and Charlie rear-integrity logic. An external provider may be
connected with `MONAD_CAPTAIN_PROVIDER_COMMAND`; it receives JSON on stdin and
must return a bounded decision as JSON on stdout. Timeout, process failure,
invalid JSON, or invalid posture automatically falls back to doctrine.

## Operations and failure behavior

`Agent Operations` reads the same WebSocket snapshot as other instruments. It
shows enablement, posture, objective, assessment, provider/runtime state, last
result, consequence, and recent accepted/rejected history. Its controls use
FleetCore commands to disable a captain independently or pause all agent intent.

If the runtime stops, an intent expires at `reconsider_at_tick`; FleetCore then
resumes the existing deterministic `escort_mode` for that vessel. Disabling a
captain removes its current intent immediately. No inference outage stops the
world clock or deterministic movement.

## Deployment

Run `scripts/install-living-fleet.sh`. It builds the release FleetCore server,
runs runtime tests, restarts the existing `fleetcore-serve` unit, and installs
the portless `living-fleet.service`. The public operations surface is
`https://cameronlampley.com/toys/agent-ops/`.
