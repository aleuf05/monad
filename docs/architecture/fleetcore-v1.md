# FleetCore v1 Architecture

FleetCore v1 is the first working implementation of Monad's canonical stateful world model.

The v1 objective is narrow:

```text
same seed + same event history + same ticks = same snapshot
```

It is local, deterministic, file-backed, and inspectable.

## What FleetCore v1 Is

- Rust CLI prototype.
- Deterministic fixed-timestep world model.
- Local file persistence.
- JSON snapshot exporter.
- Replay validation tool.

## What FleetCore v1 Is Not

- daemon,
- HTTP server,
- WebSocket server,
- database-backed service,
- cloud system,
- browser renderer,
- global traffic simulator,
- agent runtime.

## Runtime Layout

Source:

```text
fleetcore/
  Cargo.toml
  src/
  data/seed-world.json
  tests/
```

Default runtime files:

```text
data/fleetcore/
  world.json
  events.jsonl
  snapshots/
    snapshot.json
  checkpoints/
    checkpoint-tick-0000000000.json
```

The runtime directory is ignored by Git. The seed world is tracked.

## Module Responsibilities

`clock.rs`:
Owns tick count, tick duration, time scale, pause state, and deterministic simulation timestamp formatting.

`vessel.rs`:
Defines positions, vessel kinds, vessel statuses, and the core vessel shape.

`route.rs`:
Provides deterministic geographic distance, bearing, and point-at-distance helpers.

`command.rs`:
Defines replayable commands.

`event.rs`:
Defines append-only event records.

`world.rs`:
Applies commands, advances ticks, moves vessels, and replays events.

`persistence.rs`:
Loads seed/current worlds, writes world files, appends events, writes checkpoints, and exports snapshots.

`snapshot.rs`:
Creates browser-facing JSON snapshots.

`main.rs`:
Provides the local CLI.

## Entity Model

Each vessel has:

- `id`
- `name`
- `callsign`
- `kind`
- `position`
- `course`
- `speed_mps`
- `status`
- `route`
- `last_update`

Kinds:

- `flagship`
- `scout`
- `passive-traffic`

The v1 model is intentionally explicit. It does not use a speculative entity-component system yet.

## Commands

Implemented commands:

- `SetRoute`
- `PauseClock`
- `ResumeClock`
- `SetTimeScale`
- `SpawnPassiveContact`
- `RecordWatchEvent`
- `Step`

The CLI exposes these commands as direct local operations. Every mutating command is serialized into the event log.

## Tick Model

FleetCore v1 advances integer fixed ticks.

- Default tick duration: 1 simulated second.
- `time_scale` advances multiple deterministic ticks per requested step.
- Pause prevents tick advancement.
- Simulation timestamps are derived from seed `start_unix_seconds` plus tick count.
- Wall-clock time is not used for world evolution.

## Persistence Model

FleetCore v1 writes:

- current world snapshot to `world.json`,
- events to `events.jsonl`,
- checkpoints to `checkpoints/`,
- browser-facing snapshot to `snapshots/snapshot.json`.

No database is involved.

## Browser Boundary

FleetCore v1 exports files only. Browser instruments do not call FleetCore directly.

The shared browser helper at `toys/shared/fleet-state.js` can convert a FleetCore snapshot into the browser-side shared fleet state shape through `MonadFleetState.fromFleetCoreSnapshot(snapshot)`.

## Recommended v2 Direction

FleetCore v2 should remain local and deterministic, but can add:

- stable snapshot hash,
- richer command validation,
- route rejection events,
- separate checkpoint cadence,
- optional static fixture export into `toys/`,
- more robust CLI argument handling.

Do not add a daemon or HTTP API until file-contract integration has been exercised by the browser instruments.
