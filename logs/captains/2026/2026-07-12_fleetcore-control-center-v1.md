# FleetCore Control Center v1 Watch Log

Date: 2026-07-12
Operator: Lt. cgl
Objective: ship a first working version of `SPRINT.md`'s FleetCore Control Center — a scenario launcher and manual command console for `fleetcore-serve`, built entirely on the existing `Command` API with no shared-core changes.

## Build

New standalone toy, `toys/fleetcore-control/` (`index.html`, `app.js`, `style.css`, `README.md`), following `toys/fleetcore-live/`'s connection pattern (WebSocket, command-token gate, read-only until authorized) but dropping the Leaflet map in favor of control surfaces:

- Three scenario buttons (Distress Call, Storm Convoy, Collision Course), each a short hardcoded sequence of `spawn-passive-contact` + optional `set-route` + a closing `record-watch-event`, positioned relative to the flagship's position at click time.
- Manual Spawn Contact form wrapping `spawn-passive-contact` directly.
- Manual Set Route form: pick any vessel from the live vessel list, enter waypoints as `lat,lng` lines, wraps `set-route`.
- Every generated id gets a timestamp+random suffix so repeated scenario/manual runs never collide with an earlier spawn still in the world (there's no despawn command — a collision would be permanent, not self-healing).
- A standing "No undo yet" note: FleetCore's `Command` enum has no despawn/reset, and this toy doesn't fake one client-side.

## Verification

Playwright against the real `fleetcore-serve` already running on this box (port 4771, `--command-token bridge-3-0-lan`):

- No token: "Read-only" authority, all write controls (`disabled`) confirmed disabled — scenario buttons, both form submit buttons, pause/resume, time scale.
- Valid token: authority flips to "Command," every control enables, route-vessel `<select>` populates from the live vessel list.
- Manual spawn: vessel count went 8→9; independently confirmed via a fresh `GET /snapshot` fetch that the new vessel exists with the exact position submitted.
- Distress Call scenario: vessel count +1, watch log shows the expected message at the correct tick.
- Fired Distress Call a second time immediately after: vessel count +1 again, no rejection — confirms the id-suffix scheme actually prevents the collision it's meant to prevent, not just in theory.
- Manual Set Route on the manually-spawned test vessel: confirmed via a fresh snapshot that `status` flipped to `"underway"` and `route` matched the two submitted waypoints exactly.
- Storm Convoy: vessel count +3 as expected. Collision Course: vessel count +1, watch log message correct.
- Mobile viewport (390×844): no horizontal overflow.
- Zero console/page errors across every step of the run.

## Known limitation (by design, documented in README)

Every vessel spawned during this verification run is now permanently in the shared dev world (`fleetcore-serve` on port 4771) — there is no despawn command to clean them up, matching the sprint's explicit constraint not to add one mid-sprint. This is expected on a dev server used for exactly this kind of testing; it would be a real concern if run repeatedly against the public deployment's world, which is a separate, longer-lived shared space.

## Not done (explicitly out of scope per SPRINT.md)

- No changes to `fleetcore/src/command.rs` or `world.rs`.
- No changes to Bridge Station, Fleet Motion, Periscope, or Radio Console.
- Not linked from Bridge's station-links or `web/index.html`'s artifact list yet.
- Not deployed to `web/` or run through `scripts/deploy-web.sh` — local verification only, per the sprint's explicit deploy gate.

## Updated

- `toys/fleetcore-control/index.html` (new)
- `toys/fleetcore-control/app.js` (new)
- `toys/fleetcore-control/style.css` (new)
- `toys/fleetcore-control/README.md` (new)
