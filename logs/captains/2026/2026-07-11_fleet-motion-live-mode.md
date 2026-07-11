# Fleet Motion Live Mode Watch Log

Date: 2026-07-11
Operator: Commander Claude, Engineering Watch
Directed by: Admiral C — "engage," following a direct question ("thoughts on better integration") answered with a recommendation: wire Fleet Motion to FleetCore's live snapshot instead of its own simulation loop, since the pieces (`persistenceSuspended`, `fromFleetCoreSnapshot()`) already existed unused for exactly this, and it would let Periscope and Bridge inherit real data for free through the existing `MonadFleetState` contract.
Objective: give Fleet Motion an opt-in live mode, without regressing its existing, publicly-deployed standalone behavior.

## Why this was the highest-risk change of the day

Every other toy built or wired today was additive — new files, new pages, never touching an existing working control loop. This one edits `toys/fleet-motion/app.js` directly, the most established, most feature-rich, most publicly-relied-upon toy in the repo (map click to set course, waypoint editing, escort mode cycling, time warp, detour suggestions — a dozen-plus interactive controls, none of which FleetCore's `Command` surface currently has an equivalent for). Read the full interaction surface (`grep addEventListener`) before writing any code, specifically to find out how large the mismatch between Fleet Motion's feature set and FleetCore's actual `Command` vocabulary really was, rather than assuming.

## Scope decision: read-only live mode, not full read+write

Given that mismatch, implemented Fleet Motion as a **read-only observer** when FleetCore is reachable — not a full migration to sending real Commands for every interactive control (which `toys/bridge-station-3.0/` already demonstrates is possible, but only for the one control — Set Waypoint — that has a matching FleetCore command; Fleet Motion's escort-mode cycling, detour suggestions, and formation tuning have no FleetCore equivalent at all). When live, Fleet Motion suspends its own local physics and interactive controls entirely (all disabled, map clicks become no-ops) and purely renders/re-broadcasts whatever `fleetcore-serve` says. This is the same posture `toys/bridge-2/` already established.

## The other real risk: public deployment

Fleet Motion is deployed at `https://cameronlampley.com/monad/toys/fleet-motion/` — the first opportunity today for a change to reach real public traffic, not just a LAN-only demo. First implementation attempted a live connection unconditionally on load, falling back cleanly to local simulation on timeout — verified this worked correctly (no visible breakage, no delay), but caught during verification that a failed `WebSocket` connection attempt logs a network error to the browser console *natively*, a browser behavior no amount of `try`/`catch` or `close`-event handling in application code can suppress. Since `fleetcore-serve` isn't publicly reachable, this would have put a console error on every single public page load — a real regression against the "no new console warnings or errors" bar this whole session has held to, caught before deploying rather than after.

Fixed by making the live-connection attempt opt-in: it only fires if `?live=1` or `?fleetcoreServer=` is present in the URL. Verified twice, against both source and the deployed bundle, and a third time against the actual live public URL: with no query param, zero console output and 100% identical behavior to before this change.

## Implementation

- New state: `liveMode`, `liveSocket`, `liveMapCentered`, plus reconnect bookkeeping matching the pattern already used in `toys/bridge-2/`/`toys/fleetcore-live/`.
- `advanceFleet()` gains a `liveMode` early return, stopping local physics from computing positions that would immediately be overwritten by (or fight with) live data.
- The map click handler, and `pauseButton`'s per-tick `.disabled` logic inside `updateStatus()`, both gained `liveMode` guards. All other interactive controls (waypoint/escort-mode/detour/time-warp buttons) get `.disabled = true` once, on entering live mode.
- **Deliberately does not call `applyCanonicalFleetState()`** (the function `restoreFleetState()` already uses to load state from `localStorage`) for applying live snapshots, despite it looking like the obvious reuse target. Read it fully first and found two problems with calling it every ~1s: it calls `createInitialTrails()`, which resets ship trail history to a single point — fine once at load, wrong every tick; and it sets `selectedShipId` from the snapshot's `selection` field, which `fromFleetCoreSnapshot()` never populates, meaning every call would silently reset the current selection back to `"monad"`, fighting `syncExternalSelection()` and breaking Periscope's ability to drive Fleet Motion's selection. Wrote a leaner `applyLiveSnapshot()` instead: updates `flagship`/`escortStates`/`contactStates` position/heading/speed directly (matched positionally against FleetCore's scout/passive-traffic arrays, since Fleet Motion's own ids like `escort-alpha` don't match FleetCore's `vessel.scout-alpha`), then calls the same `updateFleetMarkers()`/`updateStatus()` the local physics loop already calls every frame — which correctly accumulates trails (`syncTrails()`/`addTrailPoint()`, confirmed by reading the code rather than assumed) and, via the existing unmodified `persistFleetState()` write path, writes to `MonadFleetState` using Fleet Motion's own established ids and shape. Periscope and Bridge needed zero changes to inherit this.

## Verification

Playwright, run three times against three targets (source, the deployed `web/` bundle, and after deploying, the actual public URL): confirmed the true default (no query param) is byte-for-byte behaviorally identical to before — local simulation, all controls interactive, map click sets a destination, zero console output.

With `?live=1` against the real running `fleetcore-serve`: confirmed live mode activates, the "Data Source" telemetry line and header badge both update, all listed controls report `disabled: true`, a map click after entering live mode does not change the displayed destination (confirms the guard works, not just that the button states changed), the displayed position is FleetCore's real Hormuz-area coordinates (not Fleet Motion's own unrelated Arabian Sea local-sim baseline), the position visibly advances over a 3-9 second window (real ticking, not a frozen snapshot), and `localStorage` correctly contains the live flagship position and three escorts.

Full downstream chain, inside Bridge Station (Fleet Motion + Periscope sharing one origin): switched Fleet Motion's embedded iframe into live mode and confirmed Periscope — completely unmodified — picked up the real seed-world contacts (`escort-alpha/bravo/charlie`, `traffic-dhow-01` etc.) through the existing `MonadFleetState` read path. Regression check for the Periscope-selection-sync feature built earlier today: selected a contact in Periscope and confirmed Fleet Motion's own selection readout updated correctly even while in live mode, proving `syncExternalSelection()` — which runs every frame regardless of `liveMode` — is unaffected by this change.

Trail accumulation was verified by reading `syncTrails()`/`addTrailPoint()` directly rather than trying to introspect Leaflet's internal layer state through a browser test script (a flakier approach for less signal) — confirmed they append, unlike `createInitialTrails()`, which resets.

## Follow-up

No FleetCore command exists yet for most of Fleet Motion's interactive surface (escort mode, detours, formation tuning) — a full read+write migration, if ever wanted, would need FleetCore's `Command` vocabulary to grow substantially first, not just a client-side change. `toys/bridge-station-3.0/`'s narrower Set Waypoint-only integration is the current reference for what that would look like for the one control that does have a matching command today.
