# FleetCore v2

FleetCore is Monad's deterministic world model. It ships two ways to run it:

- **CLI** (`fleetcore`, `src/main.rs`) — the original v1 prototype. One command in, one persisted mutation out. Proves that the same seed world plus the same ordered event history produces the same final world snapshot.
- **Live server** (`fleetcore-serve`, `src/bin/serve.rs`) — v2. Holds the same `World` in memory, ticks it in real time, and serves it live over HTTP/WebSocket so any number of browsers can watch (and, over the socket, command) one canonical world at once.

Both binaries share the same library (`command`, `world`, `vessel`, `clock`, `snapshot`, `persistence`) — the live server does not reimplement simulation logic, it just wraps `World::apply_command` and `World::step` in a tokio runtime instead of a one-shot CLI invocation.

## Scope

FleetCore models:

- MONAD flagship
- Scout Alpha
- Scout Bravo
- Scout Charlie
- four passive maritime traffic contacts
- active route state
- fixed simulation clock
- append-only event history
- JSON snapshot export

FleetCore does not implement a database, authentication, systemd, rendering, weather, collision physics, or autonomous agents. Browser rendering lives entirely in `toys/fleetcore-live/`, which is a thin client — it draws whatever the server sends and holds no simulation state of its own.

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

## Live Server

```sh
cargo run --manifest-path fleetcore/Cargo.toml --bin serve -- --port 4771
```

Flags (all optional): `--port` (default `4771`), `--state-dir`, `--seed`, `--tick-ms` (real milliseconds per simulation tick, default `1000`).

On startup the server loads `--state-dir`'s persisted world, or falls back to the seed if none exists yet, then:

- Ticks the world once per `--tick-ms` while the clock is running, applying `Command::Step { ticks: 1 }` exactly like the CLI's `step` command would.
- Persists `world.json` after every tick, and a numbered checkpoint plus `snapshots/snapshot.json` every 60 ticks (to avoid flooding the checkpoints directory at one-second cadence).
- Broadcasts a fresh `WorldSnapshot` to every connected WebSocket client after each tick or applied command.

Endpoints:

- `GET /snapshot` — current `WorldSnapshot` as JSON (CORS-open, for curl or a plain `fetch()`).
- `GET /ws` — WebSocket. On connect, the server immediately sends `{"type":"snapshot","snapshot":{...}}`. It sends another `snapshot` message after every tick or applied command. A client sends a raw `Command` JSON object (the same tagged shape the CLI commands map to, e.g. `{"type":"pause-clock"}` or `{"type":"set-time-scale","scale":5}`) to mutate the world; the server replies to a bad command with `{"type":"error","message":"..."}` on the broadcast channel rather than closing the connection.

`toys/fleetcore-live/` is the reference browser client for this protocol.

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

The CLI still only exports static JSON snapshots to disk. The live server (`fleetcore-serve`) serves the same `WorldSnapshot` shape over HTTP and WebSocket instead.

`toys/fleetcore-live/` consumes the live server's `WorldSnapshot` directly and does not go through `MonadFleetState`/localStorage. `toys/shared/fleet-state.js` still includes a `fromFleetCoreSnapshot()` adapter for converting a `WorldSnapshot` into the browser-side shared fleet state contract; it remains unused by Fleet Motion, Periscope, and Bridge, which are still independent client-side simulations synced via localStorage. Wiring one of them to FleetCore instead of its own local physics loop is deliberately out of scope here — see "Recommended FleetCore v3 Direction" in the engineering report.

## Current Limitations

- Route progression is simple great-circle movement between waypoints.
- Passive contacts hold course indefinitely.
- CLI checkpoints are written every mutating command; the live server checkpoints every 60 ticks instead to avoid flooding the checkpoints directory at one-second tick cadence.
- Replay compares full snapshot JSON rather than a compact hash.
- The CLI uses manual argument parsing while the command surface is still small.
- The live server holds exactly one `World` per process — no multi-world routing, no auth, no per-client permissions. Any connected client can issue any command.
- `--tick-ms` and the seed's `tick_duration_seconds` are independent knobs; at defaults they're both 1000ms/1s so wall clock and sim clock track 1:1 at `time_scale: 1`, but that's a coincidence of the current seed, not an enforced invariant.
