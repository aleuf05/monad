# Living Fleet V0.1 — Completion Packet

**Program:** Monad

**Status:** Live and sea-trial validated

**Completed:** 2026-07-13

FleetCore remains authoritative. Captains observe, assess, and submit bounded
posture intent; deterministic systems validate and execute movement. There is
no model-to-world mutation path.

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

Run `scripts/install-living-fleet.sh`. It builds both release FleetCore
binaries, runs runtime tests, restarts the existing `fleetcore-serve` unit, and
installs the portless `living-fleet.service`. The public operations surface is
`https://cameronlampley.com/toys/agent-ops/`.

Checkpoints are recovery anchors, not the durable decision log. FleetCore keeps
the newest 120 checkpoints plus the genesis checkpoint; the append-only event
log remains authoritative. `fleetcore replay` first verifies seed-plus-events,
then uses the newest compatible checkpoint plus a non-empty event tail when
historical code evolution makes genesis replay incompatible.

## Sea-trial record

The live trial used the established production services, official FleetCore
commands, normal 1x time, and no substitute server.

- Authority boundary: Bravo attempted to command Alpha at tick 41901. FleetCore
  rejected and durably recorded the decision without a target or consequence.
- Independent fallback: Bravo was disabled at tick 41903. Its intent was
  removed while deterministic escort movement continued. Re-enable produced a
  fresh `widen-flank` decision, accepted at tick 41936 and executed at 41937.
- Fleet pause: inference was paused while all scouts stayed underway under
  deterministic formation logic. Resume produced fresh executed decisions for
  Alpha, Bravo, and Charlie by tick 42001.
- Contact adaptation: `TRIAL CONTACT` was introduced in open water. Alpha
  replaced QUACKEN screening with `investigate-contact`, accepted at tick 52598
  and executed at 52599 with a 650 m stand-off.
- Changing geometry: Monad completed a reversible three-leg dogleg. At tick
  52624 Bravo and Charlie were underway toward newly derived flank and rear
  stations while Alpha maintained contact screening.
- Emergency response: transient close geometry caused Alpha to select
  `emergency-separation`, executed at tick 52633 with a deterministic separation
  target.
- Recovery: Monad returned exactly to its starting position at tick 52642. The
  trial contact was removed, and Alpha resumed QUACKEN screening at tick 52683.
- Replay: a production copy at tick 52699 replayed exactly from checkpoint
  52693 plus seven subsequent events. Living Fleet agent state and all decision
  records also matched genesis replay during the earlier audit.
- Operations: the public Agent Operations page rendered three captain cards,
  accepted results, consequences, pause/disable controls, and no page errors.

The trial contact was removed and the dogleg ended at its exact starting point.
Final state was clock running, time scale 1, agent fleet unpaused, and all three
captains enabled.

## Definition of done

- [x] Alpha, Bravo, and Charlie are persistent independent captains.
- [x] All captains observe the same authoritative FleetCore world.
- [x] Each captain controls only bounded posture intent for its assigned vessel.
- [x] Deterministic systems translate intent into validated movement.
- [x] Accepted decisions, rejections, execution, and consequences are durable,
  visible, and replayable.
- [x] Independent disable and fleet pause preserve safe deterministic behavior.
- [x] Agent Operations exposes state, result, history, and runtime controls.
- [x] A live sea trial demonstrated contact adaptation, turns, emergency
  response, recovery, and formation consequences.
