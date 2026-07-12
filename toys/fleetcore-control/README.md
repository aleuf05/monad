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

## Harbor Pilot Boarding

A stateful, multi-phase scenario implementing `Harbor.md` (Captain T's mission packet), built entirely on the same commands every other scenario here uses — no new FleetCore `Command` variant. Six operator clicks step through the mission packet's seven phases (phases 5 and 6, conn transfer and harbor transit, are one click since the packet itself has the pilot issue helm orders immediately after taking the conn):

1. **Begin Harbor Approach** — spawns a pilot boat and two harbor traffic contacts at a synthetic harbor point (offset from the flagship's position at click time; there's no real harbor/berth data in this world), routes the pilot boat toward the flagship, records the ETA watch event.
2. **Confirm Pilot Boat Detected** — narrative-only advance.
3. **Acknowledge Pilot Boat** — shows the pilot's hail text first, then on click re-routes the pilot boat to the flagship's current position and records the exchange.
4. **Confirm Boarding** — narrative-only advance.
5. **Grant the Conn** — the real centerpiece: issues a single `set-route` on the **flagship's own vessel id**, a four-leg staged path curving from its current position to the harbor point, with each leg's `record-watch-event` named after one of the packet's helm orders ("Port five," "Dead slow ahead," "Midships," "Ease to starboard"). This is what actually moves Monad under "pilot control" — confirmed via a live snapshot fetch during verification: flagship `status` flips to `"underway"` and `route` holds the real four waypoints.
6. **Arrive at Berth** — records completion, routes the pilot boat back out to the harbor point (departing).

**Reset Scenario Tracker** only resets this toy's own client-side phase tracker so a fresh run can start (with a new id suffix, avoiding collision with the previous run) — it does not despawn anything, same limitation as the rest of this toy.

### What's simplified versus the mission packet

- **Phase advancement is a manual operator action**, not automatic detection/proximity/radio-driven progression. The mission packet itself says "scenario should not automatically advance... communication is the trigger" — but FleetCore has no proximity-detection or dialogue-parsing capability to fire that trigger on its own, so a human click stands in for it at every phase.
- **No FleetCore-side phase state machine.** The mission packet's Architectural Principle asks for "every event to arise from authoritative world state and state transitions rather than isolated UI logic." The *content* of each phase (spawns, routes, watch events) is genuinely authoritative FleetCore state, visible to every connected instrument — but the phase sequencing itself (`harbor.phase` in `app.js`) lives in this one browser tab, not in FleetCore. A second visitor's Control Center wouldn't know a Harbor Pilot run is in progress elsewhere.
- **No Radio Console integration.** The hail text ("Request permission to come alongside," "Captain, request the conn.") displays in this toy's own UI and is written to FleetCore's watch log — it is not spoken through Radio Console's synthesized voice. Wiring that in would mean changing Radio Console, which both this toy's and the separate Command Center brief's boundaries rule out.
- **No visual boarding/transfer event or animation** — "Harbor Pilot aboard" is a watch-log line, not a rendered event in Fleet Motion or Periscope.
- **The harbor point is synthetic**, not a real charted harbor/berth location — an offset from wherever the flagship happens to be when the scenario starts. As of `fleetcore/src/geography.rs`, FleetCore now genuinely rejects any spawn or route waypoint that lands inside one of its five known land zones — so if the flagship happens to be operating near the Persian Gulf/Strait of Hormuz when this scenario starts, a phase could fail with a real `"... is on land (...)"` error rather than silently succeeding. Deliberately not special-cased around this: picking the harbor point relative to real geography instead of the flagship's current position would fix the land problem but break the scenario's actual premise (a short, plausible pilot-launch distance), since the flagship's operating area isn't reliably near any of the five zones. See `showCommandFeedback` for how a rejection surfaces if it happens.

## Boundaries

- No changes to `fleetcore/src/command.rs`, `world.rs`, or any other shared-core FleetCore file.
- No changes to Bridge Station, Fleet Motion, Periscope, or Radio Console.
- No backend, database, or persistence of its own — everything here is a thin client over `fleetcore-serve`'s existing HTTP/WebSocket API.
- No baked-in command token. This page can be deployed publicly like every other toy in this repo; an operator supplies a token via the form, never the URL (unlike Bridge/Fleet Motion, there is no `?commandToken=` passthrough here — the token field is the whole mechanism).
