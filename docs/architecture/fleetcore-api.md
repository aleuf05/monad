# FleetCore Live API

This is the contract for `fleetcore-serve` (`fleetcore/src/bin/serve.rs`), written for anyone building a new bridge instrument against it. The guiding question from Sprint.md applies: a future instrument should be able to connect to FleetCore without knowing how FleetCore works internally. Everything below is the interface; the simulation logic behind it (`World`, `Command`, `fleetcore/src/world.rs`) is not something a toy author needs to read.

FleetCore's CLI (`fleetcore`, `src/main.rs`) and its data files (seed/world/events/checkpoints/snapshot JSON on disk) are a separate, older contract — see `fleetcore-data-contract.md`. This document covers only the live server.

## Transports

Two ways in, both accepting and producing the same JSON shapes:

- **Plain JSON over HTTP** — `GET /snapshot` and `POST /command`. Stateless, one request in, one response out. Use this if your instrument just wants to read state occasionally or issue a single command, and doesn't need to be told about changes as they happen.
- **WebSocket** — `GET /ws`. Stateful, push-based: the server sends a fresh snapshot after every tick or applied command, so every connected instrument observes the same world without polling. Use this if your instrument wants to render live, the way `toys/fleetcore-live/` does.

Both transports read from and write to the same in-memory `World`. A command applied over HTTP shows up in every WebSocket client's next broadcast, and vice versa.

## Command Authority

**Read-only by default.** `GET /snapshot` requires nothing and always works. Every write path — `POST /command` and any command sent over `/ws` — requires the server to have been started with `--command-token <token>`, and the caller to present that exact token. With no `--command-token` configured, every write from every transport is rejected, unconditionally, regardless of what a caller presents.

This is deliberate, not a placeholder for "add auth later": Sprint.md's acceptance criteria explicitly required "read-only default for toys; explicit grant required for command authority," because this world is shared — one write affects every connected instrument and every other visitor, not just the caller. Treat holding the token as equivalent to holding operational control of the fleet for everyone currently watching.

- **HTTP:** send `Authorization: Bearer <token>` on `POST /command`. Missing or wrong token → `401`.
- **WebSocket:** pass `?token=<token>` on the `/ws` connect URL. A connection without the right token still receives every broadcast (reads are always open) but any command it sends gets an `error` message back instead of being applied.

There is currently no per-token scoping — a valid token grants unrestricted command authority (pause, resume, set-route, spawn-contact, everything in `Command`), not a subset. If you need finer-grained permissions, that's a real gap to design, not something to work around client-side.

## HTTP Endpoints

### `GET /snapshot`

No auth. Returns the current `WorldSnapshot` as JSON (see Payload Shapes below). CORS-open (`Access-Control-Allow-Origin: *`) so any origin can read it.

```sh
curl http://localhost:4771/snapshot
```

### `POST /command`

Requires `Authorization: Bearer <token>`. Body is a raw `Command` JSON object (see Command Shapes below).

```sh
curl -X POST http://localhost:4771/command \
  -H "Authorization: Bearer <token>" \
  -d '{"type":"set-time-scale","scale":5}'
```

Responses:
- `200` — command applied, body is the new `WorldSnapshot`.
- `401` — missing or wrong token, body is `{"error": "missing or invalid command token"}`.
- `400` — body wasn't valid `Command` JSON, body is `{"error": "invalid command: <serde error>"}`.
- `422` — valid `Command` JSON, but `World::apply_command` rejected it (e.g. an unknown vessel id), body is `{"error": "<rejection reason>"}`.

## WebSocket: `GET /ws`

Connect to `ws://<host>:<port>/ws`, or `ws://<host>:<port>/ws?token=<token>` for command authority.

**On connect**, the server sends, in order:
1. `{"type":"connected","command_authority":true|false}` — whether this connection can issue commands.
2. `{"type":"snapshot","snapshot":{...}}` — the current world state.

**After that**, the server sends a new `{"type":"snapshot","snapshot":{...}}` message after every tick and after every successfully applied command (from any client, HTTP or WebSocket) — a WebSocket client never needs to poll.

**To issue a command**, send a raw `Command` JSON object as a text frame (same shape as the HTTP body). If the connection lacks command authority, or the command is malformed, or `World::apply_command` rejects it, the server replies with `{"type":"error","message":"..."}` to that connection only — other connected clients never see it. A *successful* command still broadcasts its resulting `{"type":"snapshot",...}` to every connected client, which is correct: a real state change should reach every viewer, only the rejection notice for a bad attempt shouldn't.

## Payload Shapes

### `WorldSnapshot`

```json
{
  "schema_version": "monad.worldSnapshot.v1",
  "world_id": "monad.local",
  "tick": 1234,
  "sim_time": "2026-07-10T20:20:34Z",
  "clock_state": "running",
  "time_scale": 1,
  "tick_duration_seconds": 1,
  "vessels": [ /* Vessel, see fleetcore-data-contract.md */ ],
  "watch_events": [ { "tick": 12, "sim_time": "...", "message": "..." } ],
  "event_sequence": 42,
  "land_zones": [ { "name": "Qeshm Island", "south": 26.62, "north": 26.98, "west": 55.55, "east": 56.25 }, "..." ]
}
```

Identical to the CLI's `snapshot` command output (`fleetcore/src/snapshot.rs`'s `snapshot()` function) — there is exactly one snapshot shape in this codebase, not a separate live-API variant.

**`land_zones`** (`fleetcore/src/geography.rs`) is static reference data, not part of the mutable `World` — the same five rough bounding-box rectangles `toys/fleet-motion/app.js`'s client-side `LAND_ZONES` already draws (same names, same coordinates, kept in sync deliberately rather than defining a second geography). Recomputed fresh on every snapshot, never persisted. Before this existed, FleetCore had no concept of land at all — every vessel was just a lat/lng point on open water, and Fleet Motion's own land-hazard boxes were a purely client-side, unenforced heuristic (explicitly not checked once talking to a real backend). `World::apply_command` now actually rejects `spawn-passive-contact` and `set-route` commands that would place a vessel inside one of these zones (`422`, message names the zone) — see Command Shapes below. This is still a rough approximation, not real coastline polygons, and only five hand-picked rectangles near the Persian Gulf/Strait of Hormuz — most of the world these vessels operate in has no land data at all and is treated as open water by default.

### `Command`

Internally tagged on `"type"`, kebab-case, matching `fleetcore/src/command.rs`'s `Command` enum exactly — this is not a separate API-level schema, it's the same Rust type the CLI parses its positional arguments into:

```json
{"type": "pause-clock"}
{"type": "resume-clock"}
{"type": "set-time-scale", "scale": 5}
{"type": "set-route", "vessel_id": "vessel.monad", "route": [{"lat": 26.2, "lng": 55.9}]}
{"type": "spawn-passive-contact", "id": "traffic.new-01", "name": "New Contact", "callsign": "NEW CONTACT", "position": {"lat": 24.0, "lng": 58.0}, "course": 90.0, "speed_mps": 8.0}
{"type": "record-watch-event", "message": "operator note"}
{"type": "step", "ticks": 1}
```

`set-route` and `spawn-passive-contact` are rejected (`422`) if any position involved — every waypoint for `set-route`, the spawn point for `spawn-passive-contact` — falls inside one of `land_zones`' rectangles (see Payload Shapes above). The error message names the zone, e.g. `"spawn rejected: position (26.8, 55.9) is on land (Qeshm Island)"`.

`step` is what the server's own tick loop sends itself every `--tick-ms`; a client can send it too (e.g. to single-step a paused world), but there's normally no reason to — the tick loop already advances the clock in real time whenever it isn't paused.

## What This API Does Not Do

Per Sprint.md's explicit v1.0 scope: no binary serialization (everything is JSON text), no distributed deployment (one process, one `World`, in-memory), no advanced conflict resolution (single-writer assumption — the `Mutex<World>` simply serializes every command, first request in wins, no merge logic), no database (still flat files via `fleetcore::persistence`), no per-token permission scoping (see Command Authority above).
