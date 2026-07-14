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

Flags (all optional): `--port` (default `4771`), `--state-dir`, `--seed`, `--tick-ms` (real milliseconds per simulation tick, default `1000`), `--command-token <token>` (grants command authority to whoever presents this token; omit it and the server is fully read-only — see Command Authority below), `--bind-all` (bind `0.0.0.0` instead of the loopback-only default; only do this once a reverse proxy/TLS/auth story is actually in place), `--vessel-event-retention <N>` (how many of the newest `vessel_events` to keep in `World`/`world.json`/checkpoints/live snapshots, default `2000` — GitHub issue #6; full history stays durable in `events.jsonl` regardless, see `docs/architecture/vessel-events-retention-investigation.md`).

On startup the server loads `--state-dir`'s persisted world, or falls back to the seed if none exists yet, then:

- Ticks the world once per `--tick-ms` while the clock is running, applying `Command::Step { ticks: 1 }` exactly like the CLI's `step` command would.
- Persists `world.json` after every tick, and a numbered checkpoint plus `snapshots/snapshot.json` every 60 ticks (to avoid flooding the checkpoints directory at one-second cadence).
- Broadcasts a fresh `WorldSnapshot` to every connected WebSocket client after each tick or applied command.

Endpoints — full contract, payload shapes, and error responses are in `docs/architecture/fleetcore-api.md`:

- `GET /snapshot` — current `WorldSnapshot` as JSON. No auth, CORS-open.
- `POST /command` — apply a `Command` (JSON body, same tagged shape the CLI commands map to). Requires `Authorization: Bearer <token>`.
- `GET /ws` — WebSocket. Optional `?token=<token>` on the connect URL grants command authority for that connection. On connect the server sends `{"type":"connected","command_authority":true|false}` then the current `{"type":"snapshot","snapshot":{...}}`, then another `snapshot` message after every subsequent tick or applied command from any client. An authorized connection can send a raw `Command` JSON object to mutate the world; an unauthorized one gets `{"type":"error","message":"..."}` back instead.

### Command Authority

Read-only by default: with no `--command-token` set, every write from every transport is rejected, unconditionally. Set `--command-token <token>` to grant write access to whoever presents it (`Authorization: Bearer <token>` over HTTP, `?token=<token>` on the WebSocket connect URL). There is no per-token scoping yet — a valid token grants unrestricted authority over the whole `Command` surface, not a subset, and this world is shared, so holding the token affects every connected instrument and visitor, not just the caller.

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
- The live server holds exactly one `World` per process — no multi-world routing. The `--command-token` gate (see Command Authority above) is all-or-nothing: no per-client permissions, no scoping to a subset of commands, no rate limiting, and no way to revoke a token short of restarting the process with a new one.
- `--tick-ms` and the seed's `tick_duration_seconds` are independent knobs; at defaults they're both 1000ms/1s so wall clock and sim clock track 1:1 at `time_scale: 1`, but that's a coincidence of the current seed, not an enforced invariant.
