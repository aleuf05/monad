# Monad FleetCore Control Center

A scenario launcher and manual command console for a running `fleetcore-serve` process. Where `toys/fleetcore-live/` is a viewer of the shared world, this is a way to set the world up: spawn contacts, stage routes, and fire a handful of canned scenarios, instead of hand-typing `curl -X POST /command` calls.

## Run locally

From the repository root:

```sh
python -m http.server 8080
```

Then open:

```text
http://localhost:8080/toys/fleetcore-control/
```

Enter a server URL (defaults to `ws://localhost:4771/ws`) and a command token, then Connect. See `docs/architecture/fleetcore-api.md` for the full API contract this toy is built against.

## What it does

- **Connects** over the same WebSocket contract `toys/fleetcore-live/` uses. Read-only with no token; every write control below enables only once the server confirms command authority for this connection.
- **Scenarios** — three buttons, each a short hardcoded sequence of `spawn-passive-contact` (+ `set-route` where relevant) and a closing `record-watch-event`, positioned relative to the flagship's position at the moment the button is clicked:
  - **Distress Call** — one stopped vessel spawned near the flagship.
  - **Storm Convoy** — three vessels spawned in a loose line, each routed a short distance toward the flagship's area.
  - **Collision Course** — one vessel spawned at a distance and routed to the flagship's *current* position.
- **Manual Spawn Contact** — a form wrapping `spawn-passive-contact` directly: name, callsign, position, course, speed.
- **Manual Set Route** — a form wrapping `set-route`: pick any vessel from the live vessel list, enter one or more `lat,lng` waypoints (one per line).
- **Vessels** and **Watch Events** panels mirror the current `WorldSnapshot` live, same rendering approach as `toys/fleetcore-live/`.

## ID collisions

Every scenario- or manually-spawned contact gets a timestamp+random suffix (`distress-<suffix>`, `manual-<suffix>`, etc.) so repeated runs never collide with an earlier spawn still sitting in the world — `spawn-passive-contact` rejects a duplicate id outright (`world.rs`), and a fixed literal id would make every second click of the same scenario button fail.

## No despawn, no reset

FleetCore's `Command` enum (`fleetcore/src/command.rs`) has no despawn/remove-contact command and no world-reset/teleport command — only `set-route`, `pause-clock`, `resume-clock`, `set-time-scale`, `spawn-passive-contact`, and `record-watch-event`. Anything spawned from this page, or from anywhere else, stays in the world until the `fleetcore-serve` process itself restarts. This toy does not attempt to fake a client-side "hide" of a contact — that would misrepresent shared world state to every other connected viewer, who would still see it. A real fix needs a new `Command` variant in FleetCore's shared core (`fleetcore/src/command.rs` + `world.rs`), which is out of scope here — see `logs/captains/2026/2026-07-11_fleet-motion-command-restoration.md`'s Follow-up note for the same gap flagged from Fleet Motion's side, including the note that this may already be Codex's independent FleetCore-interface track rather than something to pick up unilaterally.

## Route scenarios track a point, not a moving target

`set-route` takes a fixed waypoint list. **Collision Course** routes the spawned contact to the flagship's position *as read from the snapshot at the moment the button was clicked* — if the flagship keeps moving afterward, the contact does not re-aim to follow it. Good enough for a one-shot scripted setup; not a real intercept simulation.

## Boundaries

- No changes to `fleetcore/src/command.rs`, `world.rs`, or any other shared-core FleetCore file.
- No changes to Bridge Station, Fleet Motion, Periscope, or Radio Console.
- No backend, database, or persistence of its own — everything here is a thin client over `fleetcore-serve`'s existing HTTP/WebSocket API.
- No baked-in command token. This page can be deployed publicly like every other toy in this repo; an operator supplies a token via the form, never the URL (unlike Bridge/Fleet Motion, there is no `?commandToken=` passthrough here — the token field is the whole mechanism).
