# FleetCore v1

FleetCore v1 is Monad's deterministic local world prototype.

It is a Rust CLI, not a daemon or backend service. Its job is to prove that the same seed world plus the same ordered event history produces the same final world snapshot.

## Scope

FleetCore v1 models:

- MONAD flagship
- Scout Alpha
- Scout Bravo
- Scout Charlie
- four passive maritime traffic contacts
- active route state
- fixed simulation clock
- append-only event history
- JSON snapshot export

FleetCore v1 does not implement networking, a database, authentication, WebSockets, systemd, rendering, browser UI, weather, collision physics, or autonomous agents.

## Units

- Position: latitude and longitude in decimal degrees.
- Heading, course, and bearing: degrees true, normalized to `0 <= x < 360`.
- Speed: meters per second internally.
- Time: deterministic simulation time derived from seed start time plus integer ticks.

Browser adapters may convert speed to knots or kilometers per hour. FleetCore does not store knots as canonical engine state.

## Run

From the repository root:

```sh
cargo run --manifest-path fleetcore/Cargo.toml -- init
cargo run --manifest-path fleetcore/Cargo.toml -- inspect
cargo run --manifest-path fleetcore/Cargo.toml -- step 30
cargo run --manifest-path fleetcore/Cargo.toml -- snapshot
cargo run --manifest-path fleetcore/Cargo.toml -- replay
```

Default paths:

- seed: `fleetcore/data/seed-world.json`
- runtime world: `data/fleetcore/world.json`
- event log: `data/fleetcore/events.jsonl`
- snapshots: `data/fleetcore/snapshots/`
- checkpoints: `data/fleetcore/checkpoints/`

Use `--state-dir <path>` and `--seed <path>` to override defaults.

## Commands

```text
init
inspect
step <ticks>
run <ticks>
pause
resume
set-time-scale <scale>
set-route <vessel-id> <lat> <lng> [<lat> <lng> ...]
spawn-contact <id> <name> <callsign> <lat> <lng> <course> <speed-mps>
record-watch-event <message>
snapshot [output-path]
replay
```

Each mutating command appends one JSON event, writes `world.json`, writes a checkpoint, and updates `snapshots/snapshot.json`.

## Determinism Proof

Run:

```sh
cargo test --manifest-path fleetcore/Cargo.toml
```

The integration test loads the same seed world, applies the same command sequence, advances the same number of ticks, replays the event log from seed, and asserts that the final JSON snapshots match exactly.

## Browser Boundary

FleetCore exports static JSON snapshots. It does not serve them.

`toys/shared/fleet-state.js` includes a `fromFleetCoreSnapshot()` adapter so future browser instruments can convert a FleetCore snapshot into the current browser-side shared fleet state contract.

## Current Limitations

- Route progression is simple great-circle movement between waypoints.
- Passive contacts hold course indefinitely.
- Checkpoints are written every mutating command for simplicity.
- Replay compares full snapshot JSON rather than a compact hash.
- The CLI uses manual argument parsing while the command surface is still small.
