# Mission

Build a FleetCore Control Center: a standalone toy that lets an operator with command authority populate and steer the shared FleetCore world through friendly scenario controls, instead of hand-typing raw `Command` JSON.

Bridge Station's Command Token field (just shipped) proved operators want to grant and use command authority from a real UI, not a URL param. But Bridge itself is deliberately an *operational* console — it composes Fleet Motion, Periscope, and Radio Console as they already are, and only forwards a token through to Fleet Motion. There is no tool anywhere in the repo for actually setting a scene up: spawning contacts, staging a scripted situation, or clearing the board between demos. Today that means either writing raw `curl -X POST /command` calls by hand, or manually clicking through Fleet Motion's own waypoint UI one vessel at a time.

# Context

- `docs/architecture/fleetcore-api.md` is the authoritative contract. Read it before implementation — this sprint works entirely within the existing `Command` surface, described in full below, and does not require or assume any change to `fleetcore/src/command.rs` or `world.rs`.
- The `Command` enum today (`fleetcore/src/command.rs`) is: `SetRoute { vessel_id, route }`, `PauseClock`, `ResumeClock`, `SetTimeScale { scale }`, `SpawnPassiveContact { id, name, callsign, position, course, speed_mps }`, `RecordWatchEvent { message }`. That's the complete toolkit available — there is no despawn/remove-contact command and no reset/teleport command. Both are real gaps; do not attempt to add them mid-sprint (see Constraints).
- `toys/fleetcore-live/` is the closest existing precedent: a thin standalone client with its own Command Token field, connecting directly to `fleetcore-serve`'s `/ws`. Read its `app.js` for the connection/auth pattern before writing a new one.
- `toys/fleet-motion/app.js`'s `liveConnectUrl()`/`fleetCoreServerUrl()` functions are the reference for deriving the right server URL in both local-dev and public-deployment (`/monad/fleetcore-ws/ws` reverse-proxy) contexts. Reuse that derivation logic rather than reinventing it.
- `fleetcore-serve` is currently running locally on port 4771 with `--command-token bridge-3-0-lan` for development verification. The public deployment's systemd unit (`scripts/fleetcore-serve.service`) does not set a command token by default (read-only for the public), per `docs/deployment.md`.

# Objective

Ship `toys/fleetcore-control/` (name open to a better one) as a new standalone static toy:

- Connects to `fleetcore-serve` the same way `toys/fleetcore-live/` does (WebSocket, optional `?fleetcoreServer=` override), and requires a command token to be entered before any write control is enabled — read-only world view otherwise, matching every other instrument's authority model.
- Shows the current world state (vessel list, clock state, time scale) so an operator can see what's already there before adding to it.
- Offers a handful of canned scenario buttons (e.g. "Distress Call," "Storm Convoy," "Collision Course") that each issue a short, hardcoded sequence of `spawn-passive-contact` + `set-route` + `record-watch-event` commands to set a scene, plus standalone manual controls for spawning one contact and setting one route ad hoc.
- Exposes `pause-clock` / `resume-clock` / `set-time-scale` directly, since "steer the scenario once it's running" is part of the ask, not just "populate it."

# Requirements

- Read `docs/architecture/fleetcore-api.md`, `toys/fleetcore-live/app.js`, and `toys/fleet-motion/app.js`'s live-mode section before implementation.
- Command authority is opt-in via a token field, same UX pattern Bridge's Command Token field and `toys/fleetcore-live/` already use — do not invent a new auth pattern.
- Scenario buttons must be visibly disabled (not hidden) without command authority, with the same kind of explanatory note Fleet Motion's live-mode note already uses for disabled controls.
- Every scenario/manual action must use IDs that can't collide with whatever Fleet Motion or another operator already spawned — namespace generated contact IDs (e.g. a random or timestamp suffix) rather than reusing fixed literal IDs across repeated runs.
- Since there is no despawn command, document prominently in this toy's own README that "clearing the board" is not currently possible from here or anywhere else — spawned contacts persist in the world until the process restarts. Do not attempt to fake a client-side "hide" of a contact; that would lie about shared world state to every other connected viewer.
- This toy must degrade honestly with no reachable `fleetcore-serve`: show a clear "not connected" state, no fake/local-simulation fallback (unlike Fleet Motion/Periscope, there's no meaningful "local demo" version of a live-world control panel).

# Constraints

- No changes to `fleetcore/src/command.rs`, `world.rs`, or any other shared-core FleetCore file. If a scenario idea needs a command that doesn't exist (despawn, reset, teleport), document it as a follow-up request rather than implementing it — Codex has reportedly been working the FleetCore interface track independently (see `logs/captains/2026/2026-07-11_fleet-motion-command-restoration.md`'s Follow-up note); a new Command variant is a shared-core change that needs to be reconciled with that track, not added unilaterally here.
- No changes to Bridge Station, Fleet Motion, Periscope, or Radio Console. This is a new, independent standalone toy — it may be linked from Bridge's station-links or `web/index.html`'s artifact list as a follow-up, but wiring it into Bridge's own composited console is out of scope for this sprint.
- No new backend, database, or persistence beyond what `fleetcore-serve` already provides. Static HTML/CSS/JS only, matching every other toy.
- No baked-in command token anywhere in the bundle, same reasoning as every other public-deployable toy in this repo.
- Do not deploy to `web/` or run `scripts/deploy-web.sh` as part of this sprint without separate confirmation — build and verify locally against the already-running `fleetcore-serve` first.

# Acceptance Tests

- Load the toy with no token: world state (vessel list, clock) is visible and updates live; every write control is visibly disabled with an explanatory note; no console errors.
- Load with a valid command token (`bridge-3-0-lan` against the local dev server): write controls enable; a manual "spawn contact" action results in a new vessel visible in this toy, in Fleet Motion, and in Periscope's contact list within a few seconds, with no ID collision on repeated clicks.
- Fire one canned scenario button: confirm the resulting sequence of spawned contacts/routes lands correctly in a fresh `GET /snapshot`, and a `record-watch-event` message documenting the scenario appears in the snapshot's `watch_events`.
- Pause/Resume/Time Warp controls actually change `clock_state`/`time_scale` in a fresh snapshot.
- Point the toy at an unreachable `fleetcoreServer` (dead port): confirm a clear "not connected" state, no fake data, no console errors.
- No regressions: reload Fleet Motion, Periscope, and Bridge Station afterward and confirm they observe whatever this toy spawned into the shared world, same as they would any other FleetCore-originated vessel.

# Deliverables

- `toys/fleetcore-control/` (index.html, app.js, style.css, README.md) as a new standalone toy.
- A short doc note on the "no despawn/reset" gap and what a real fix would require (which FleetCore file, roughly what shape), for whoever picks that up next.
- A watch log under `logs/captains/2026/`.
- Local verification against the already-running `fleetcore-serve` (port 4771, `--command-token bridge-3-0-lan`), with results reported before any deploy step is considered.
