# FleetCore Live API

This is the contract for `fleetcore-serve` (`fleetcore/src/bin/serve.rs`), written for anyone building a new bridge instrument against it. The guiding question from Sprint.md applies: a future instrument should be able to connect to FleetCore without knowing how FleetCore works internally. Everything below is the interface; the simulation logic behind it (`World`, `Command`, `fleetcore/src/world.rs`) is not something a toy author needs to read.

FleetCore's CLI (`fleetcore`, `src/main.rs`) and its data files (seed/world/events/checkpoints/snapshot JSON on disk) are a separate, older contract — see `fleetcore-data-contract.md`. This document covers only the live server.

## Transports

Two ways in, both accepting and producing the same JSON shapes:

- **Plain JSON over HTTP** — `GET /snapshot` and `POST /command`. Stateless, one request in, one response out. Use this if your instrument just wants to read state occasionally or issue a single command, and doesn't need to be told about changes as they happen.
- **WebSocket** — `GET /ws`. Stateful, push-based: the server sends a fresh snapshot after every tick or applied command, so every connected instrument observes the same world without polling. Use this if your instrument wants to render live, the way `toys/fleetcore-live/` does.

Both transports read from and write to the same in-memory `World`. A command applied over HTTP shows up in every WebSocket client's next broadcast, and vice versa.

## Command Authority

Mutation is read-only by default. `GET /snapshot` requires nothing and every
WebSocket connection may observe snapshots. Every external command path first
authenticates a Bearer principal or hardened same-origin browser session, then
separately checks command authority. Missing or invalid credentials receive HTTP `401`;
the optional authenticated observer principal receives `403`. WebSocket
attempts receive an equivalent targeted error without disconnecting observers.

`--command-token <token>` configures the command principal. With no command
token configured, no external caller can mutate the world. The optional
`--observer-token <token>` proves identity without granting mutation. The
command principal currently covers the existing `Command` surface rather than
per-command scopes. See `fleetcore-command-auth.md` for operating and threat
notes.

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

Connect to `ws://<host>:<port>/ws`. Header-capable clients supply
`Authorization: Bearer <token>` in an Origin-less upgrade. Browsers first use
`POST /auth/session` from an allowlisted Origin, then upgrade with the issued
HttpOnly cookie. URL query credentials are not supported.

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
  "vessel_events": [ /* VesselEvent, see "Vessel Events" below */ ],
  "event_sequence": 42,
  "escort_mode": "patrol",
  "agent_fleet_paused": false,
  "captain_controls": [ /* enablement and runtime status */ ],
  "escort_intents": [ /* current accepted intent per captain */ ],
  "agent_decisions": [ /* accepted/rejected history and consequences */ ],
  "land_zones": [ { "name": "Qeshm Island", "south": 26.62, "north": 26.98, "west": 55.55, "east": 56.25 }, "..." ]
}
```

Identical to the CLI's `snapshot` command output (`fleetcore/src/snapshot.rs`'s `snapshot()` function) — there is exactly one snapshot shape in this codebase, not a separate live-API variant.

**`land_zones`** (`fleetcore/src/geography.rs`) is static reference data, not part of the mutable `World` — the same five rough bounding-box rectangles `toys/fleet-motion/app.js`'s client-side `LAND_ZONES` already draws (same names, same coordinates, kept in sync deliberately rather than defining a second geography). Recomputed fresh on every snapshot, never persisted. Before this existed, FleetCore had no concept of land at all — every vessel was just a lat/lng point on open water, and Fleet Motion's own land-hazard boxes were a purely client-side, unenforced heuristic (explicitly not checked once talking to a real backend). `World::apply_command` now actually rejects `spawn-passive-contact` and `set-route` commands that would place a vessel inside one of these zones (`422`, message names the zone) — see Command Shapes below. This is still a rough approximation, not real coastline polygons, and only five hand-picked rectangles near the Persian Gulf/Strait of Hormuz — most of the world these vessels operate in has no land data at all and is treated as open water by default.

### Vessel Events

`vessel_events` (`fleetcore/src/vessel.rs`'s `VesselEvent` enum) is a structured, ever-growing log of route/motion transitions per vessel — distinct from `watch_events` (free-text operator log lines) and from the internal replay `Event` (`fleetcore/src/event.rs`, records which `Command` was applied, not used over the wire). Never truncated server-side, same as `watch_events` — a client wanting only what's new since its last look should diff against array length or the highest `tick` seen, the same pattern `fleetcore-control`'s own `renderWatchEvents()` already uses for `watch_events`.

Exactly one of four types can occur for a given vessel in a given tick — they're mutually exclusive, never blended:

```json
{"type": "waypoint_reached", "vessel_id": "vessel.scout-bravo", "route_id": 1, "waypoint": {"lat": 26.539, "lng": 56.628}, "remaining_leg_count": 1, "tick": 2872, "sim_time": "..."}
{"type": "route_replaced", "vessel_id": "vessel.monad", "old_route_id": 1, "old_active_waypoint": {"lat": 26.2, "lng": 55.9}, "new_route_id": 2, "new_first_waypoint": {"lat": 24.5, "lng": 59.0}, "remaining_leg_count": 2, "issuing_authority": "operator", "tick": 57, "sim_time": "..."}
{"type": "route_completed", "vessel_id": "vessel.scout-alpha", "route_id": 0, "tick": 1294, "sim_time": "..."}
{"type": "holding", "vessel_id": "vessel.monad", "tick": 10, "sim_time": "..."}
```

- **`waypoint_reached`** — a vessel reached one leg of a multi-leg route and has more remaining (`remaining_leg_count >= 1`). Status stays `underway`.
- **`route_completed`** — a vessel reached the *last* leg of its route (`remaining_leg_count` would be `0`). Status becomes `arrived`.
- **`route_replaced`** — a `set-route` command landed on a vessel that was genuinely `underway` on a real route (not `holding`/`arrived`/`paused`, not routeless). The vessel holds its current position (no snap/jump to the old or new target), keeps moving (`status` stays `underway`), and its heading is recomputed toward `new_first_waypoint` immediately. This is the fix for the bug this event type exists to solve: previously, a new route arriving near an old route's completion was indistinguishable downstream from a genuine arrival followed by a fresh assignment — now the two are structurally different events with different payloads, and a replacement never passes through `arrived`/`holding` on the way. `issuing_authority` is always `"operator"` today — there is no per-connection identity anywhere in `fleetcore-serve` (see Command Authority above), so treat this as a placeholder, not a real actor id.
- **`holding`** — a `set-route` command with an empty route was applied (explicit "cancel route, hold position").

A `set-route` command that assigns a route to a vessel that was *not* underway on an existing one (e.g. from `holding` or `arrived`) is a fresh assignment, not a replacement — nothing was superseded, so no event fires for it. Escort Mode's own per-tick station-keeping (`world.rs`'s `advance_one_tick`, re-issuing each scout's route toward a freshly computed formation point every tick) deliberately bypasses this event system entirely — treating every tick's station update as a route replacement would fire `route_replaced` continuously the whole time escorting is active, which isn't useful signal.

**Tie-break, replacement vs. genuine arrival landing "the same tick":** there isn't one to design, and no special-case code exists for it. `World` lives behind a single `Mutex`, and even the tick loop's own advancement is just another `Command` (`Step`) applied through the same `apply_command` entry point everything else uses — so a `set-route` command and a tick's arrival check are always strictly ordered by lock acquisition, never concurrent. Whichever actually ran first is definitionally correct: if the command ran first, the route was already replaced before that tick's arrival check ever evaluates against it (unambiguous `route_replaced`). If the tick ran first, arrival was already genuine before the command was even processed (unambiguous `route_completed`/`waypoint_reached`), and the command that lands a moment later is just an ordinary fresh assignment.

### `Command`

Internally tagged on `"type"`, kebab-case, matching `fleetcore/src/command.rs`'s `Command` enum exactly — this is not a separate API-level schema, it's the same Rust type the CLI parses its positional arguments into:

```json
{"type": "pause-clock"}
{"type": "resume-clock"}
{"type": "set-time-scale", "scale": 5}
{"type": "set-route", "vessel_id": "vessel.monad", "route": [{"lat": 26.2, "lng": 55.9}]}
{"type": "spawn-passive-contact", "id": "traffic.new-01", "name": "New Contact", "callsign": "NEW CONTACT", "position": {"lat": 24.0, "lng": 58.0}, "course": 90.0, "speed_mps": 8.0}
{"type": "despawn-vessel", "id": "traffic.new-01"}
{"type": "submit-escort-intent", "captain_id": "captain.alpha", "vessel_id": "vessel.scout-alpha", "posture": "advance-screen", "target_contact_id": null, "objective": "Establish the forward screen.", "assessment": "Forward sector clear.", "observed_tick": 1234, "observed_event_sequence": 42, "reconsider_at_tick": 1294}
{"type": "set-captain-enabled", "vessel_id": "vessel.scout-alpha", "enabled": false}
{"type": "set-agent-fleet-paused", "paused": true}
{"type": "report-captain-runtime", "captain_id": "captain.alpha", "vessel_id": "vessel.scout-alpha", "status": "idle", "provider": "doctrine-fallback-v1", "message": "Decision accepted.", "observed_tick": 1234}
{"type": "record-watch-event", "message": "operator note"}
{"type": "step", "ticks": 1}
```

`set-route` and `spawn-passive-contact` are rejected (`422`) if any position involved — every waypoint for `set-route`, the spawn point for `spawn-passive-contact` — falls inside one of `land_zones`' rectangles (see Payload Shapes above). The error message names the zone, e.g. `"spawn rejected: position (26.8, 55.9) is on land (Qeshm Island)"`.

`despawn-vessel` is the symmetric inverse of `spawn-passive-contact` and only that: it's rejected (`422`) for an unknown id, and rejected for any vessel that isn't `passive-traffic` kind (`"cannot despawn '...': only passive-traffic contacts can be removed, not a Flagship/Scout vessel"`) — the flagship and scout escorts aren't removable through this command, on purpose. There is still no bulk "clear the board"/reset command; each vessel has to be despawned individually.

`step` is what the server's own tick loop sends itself every `--tick-ms`; a client can send it too (e.g. to single-step a paused world), but there's normally no reason to — the tick loop already advances the clock in real time whenever it isn't paused.

`submit-escort-intent` is the only captain decision command. It accepts no
route or coordinates. FleetCore checks captain assignment, enablement,
observation freshness, bounded text/reconsideration fields, and a current
passive contact for investigations. A domain rejection returns a normal updated
snapshot with an `escort-intent-rejected` command event and `agent_decisions`
record, keeping rejection visible and replayable. Malformed JSON remains HTTP
400; non-agent command validation remains HTTP 422.

## What This API Does Not Do

Per Sprint.md's explicit v1.0 scope: no binary serialization (everything is JSON text), no distributed deployment (one process, one `World`, in-memory), no advanced conflict resolution (single-writer assumption — the `Mutex<World>` simply serializes every command, first request in wins, no merge logic), no database (still flat files via `fleetcore::persistence`), no per-token permission scoping (see Command Authority above).
