# FleetCore Simulation Model

FleetCore should use a deterministic fixed-timestep simulation model with explicit snapshots and an append-only event log.

The model should be simple enough to audit and strict enough to replay.

## Core Principle

FleetCore should not ask "what frame is the browser rendering?"

FleetCore should ask:

```text
What world tick is authoritative?
```

Rendering frames are presentation. Simulation ticks are truth.

## Recommended Clock Model

Use a fixed timestep.

Recommended initial values:

- tick unit: integer tick index,
- tick duration: 1 simulated second,
- wall-clock mode: configurable,
- time scale: `0`, `1`, `10`, `100`, or other bounded values,
- authoritative simulation time: derived from seed time plus tick count.

Example:

```json
{
  "tick": 1200,
  "tickDurationMs": 1000,
  "simTime": "2026-07-10T20:20:00Z",
  "timeScale": 10,
  "clockState": "running"
}
```

Do not store simulation truth as floating wall-clock deltas. Store integer ticks and derive time.

## Pause

Pause should stop tick advancement. It should not prevent commands from being accepted.

When paused:

- current tick remains stable,
- accepted commands are logged,
- commands that affect future behavior apply at the next tick unless defined as immediate metadata changes,
- snapshots remain available.

This matches current browser expectations: instruments can still inspect or prepare state while movement is stopped.

## Accelerated Time

Accelerated time should advance multiple fixed ticks per wall-clock interval. It should not change the tick size.

Bad model:

```text
tick once with delta = 100 seconds
```

Preferred model:

```text
run 100 one-second ticks
```

This preserves deterministic behavior and reduces hidden differences between normal and accelerated simulation.

FleetCore may later batch ticks internally for performance, but the externally meaningful result should match sequential fixed ticks.

## Replay

Replay should be a first-class capability.

Inputs:

- seed world snapshot,
- ordered event log,
- target tick.

Output:

- deterministic world snapshot at target tick,
- validation hash,
- optional replay diagnostics.

Replay should not require a browser.

## Save And Load

Save/load should use checkpoint snapshots plus events after the checkpoint.

Load sequence:

1. Read latest valid checkpoint at or before requested tick.
2. Verify checkpoint schema and checksum.
3. Read events after checkpoint.
4. Replay events to requested tick.
5. Emit recovered snapshot.

This supports fast startup without giving up auditability.

## Deterministic Restart

FleetCore should be able to shut down and restart without changing world state.

Required metadata:

- world ID,
- seed ID,
- schema versions,
- tick duration,
- last committed tick,
- last checkpoint tick,
- event log sequence number,
- deterministic algorithm version,
- random seed if randomness is used.

Randomness should be avoided in the first implementation. When randomness is needed, use a seeded deterministic generator and record the seed.

## Movement Model

Initial vessel movement should stay deliberately simple:

- position,
- heading,
- course,
- speed,
- route waypoint queue,
- fixed-tick advancement,
- arrival radius,
- route status.

Do not introduce full maritime physics in FleetCore Mk I.

Fleet Motion's current browser motion is useful as product feel, but FleetCore's first responsibility is reproducible truth. Presentation smoothing belongs in browser instruments unless the smoothed state is explicitly part of the canonical world.

## Route Engine

The route engine should validate and advance route intent.

Initial route responsibilities:

- accept route commands,
- store active route,
- advance along route legs,
- detect leg arrival,
- reject obviously invalid route segments,
- emit route events.

Future responsibilities:

- port approaches,
- harbor channels,
- restricted waters,
- route cost,
- agent-proposed route review.

Keep route policy separate from rendering. A route is not a polyline style.

## Event Model

Events should be append-only and deterministic.

Event examples:

- `WorldCreated`
- `ClockPaused`
- `ClockResumed`
- `TimeScaleChanged`
- `EntityCreated`
- `RouteAssigned`
- `RouteLegCompleted`
- `VesselArrived`
- `ContactSpawned`
- `WatchEventRecorded`

Each event should include:

- event ID,
- tick,
- sequence number,
- type,
- actor,
- payload,
- schema version,
- previous event hash or log segment hash if audit chaining is desired.

## Snapshot Model

Snapshots are read models of current truth.

Recommended JSON shape:

```json
{
  "schemaVersion": "monad.worldSnapshot.v1",
  "worldId": "monad.local",
  "tick": 1200,
  "simTime": "2026-07-10T20:20:00Z",
  "clock": {
    "state": "running",
    "timeScale": 10,
    "tickDurationMs": 1000
  },
  "entities": [],
  "routes": [],
  "recentEvents": []
}
```

Snapshots should be stable enough for browsers to consume directly and explicit enough for future agents to inspect.

## Persistence Strategy

Recommended persistence for Mk I:

- snapshots: JSON files,
- event log: JSON Lines,
- checkpoint cadence: every 1000 ticks or every significant command burst,
- manifest: small JSON file pointing to latest complete checkpoint and event log segment.

Why JSON first:

- easy to inspect,
- easy for browsers to consume,
- low tooling burden,
- good for architecture validation.

Future formats:

- MessagePack or CBOR for compact local snapshots,
- SQLite for indexed event queries,
- PostgreSQL only if multi-user service needs justify it.

Do not start with a database. FleetCore's first risk is model clarity, not storage scale.

## Recovery Strategy

FleetCore should write durable state in this order:

1. Append event.
2. Flush event log.
3. Apply event to in-memory world.
4. Periodically write checkpoint to temporary file.
5. Verify checkpoint.
6. Atomically rename checkpoint into place.
7. Update manifest.

On recovery:

- ignore incomplete temporary checkpoints,
- use the latest manifest-backed checkpoint,
- replay events after checkpoint,
- verify final tick and hash.

## Reproducibility Tests

The future FleetCore implementation should include deterministic replay tests:

1. Seed world.
2. Apply command sequence.
3. Run N ticks.
4. Save snapshot hash.
5. Restart from seed plus events.
6. Replay to N.
7. Assert identical snapshot hash.

This test is more important than UI tests for FleetCore because FleetCore's mission is truth.

## Recommended Model

FleetCore should use:

- integer fixed ticks,
- explicit pause and time-scale state,
- append-only event log,
- periodic JSON checkpoints,
- deterministic replay,
- JSON snapshots for browsers,
- no browser rendering logic,
- no database in the first implementation.

This is the smallest model that can become durable without becoming overbuilt.
