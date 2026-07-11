# Bridge Station 3.0 Watch Log

Date: 2026-07-11
Operator: Commander Claude, Engineering Watch
Directed by: Admiral C — "bridge station 3.0," confirmed via clarifying question to mean merging Bridge Station 2.0 (real FleetCore data, read-only) with Bridge Station 2.1 (interactive operator loop, mock state).
Objective: wire 2.1's React UI to real `fleetcore-serve` data, making Set Waypoint a genuine write against the real backend.

## Problem

Two separate artifacts needed reconciling, and neither could just be edited into the other without losing something real:

- **2.1's rendering was built around an abstract 600×400 chart space**, not geography — no lat/lng anywhere in the original component. FleetCore's real vessel positions are lat/lng. Needed a projection layer, not a data-format swap.
- **2.1's "Act" was entirely local** — Set Waypoint mutated in-memory mock state directly, with a local `setInterval` physics loop making the mock ship visibly turn. Making this real meant removing that local simulation entirely and trusting FleetCore's own tick loop to move the ship, which meant Bridge Station 3.0 needed genuine write access to `fleetcore-serve` — the first deployment in this project to need one.

## Integration

- New project `toys/bridge-station-3.0/`, scaffolded from a copy of `toys/bridge-station-2.1/`'s Vite setup (not from scratch — same dependencies, same design tokens, same visual layout). `toys/bridge-station-2.1/` itself is untouched, left as a frozen mock-data reference (its own README updated to point at 3.0 as "the merge," not a replacement).
- **Projection layer**: `computeBounds()` reads the fleet's real lat/lng spread from the first snapshot only, pads it 60%, and freezes it; `toChart()`/`toGeo()` convert between real positions and that fixed abstract space for the rest of the session. Frozen rather than recomputed every tick, for the same reason `toys/bridge-2/` centers its map once via `hasCenteredMap` — recomputing every snapshot would make the whole view visibly rescale and jump as vessels move.
- **Set Waypoint now sends a real `Command`**: clicking the chart in waypoint mode converts the clicked chart-space point back to lat/lng via `toGeo()`, then sends `{"type":"set-route","vessel_id":<flagship's real id>,"route":[{lat,lng}]}` over the WebSocket. No local state mutation happens on click at all — the UI just logs "command sent" and waits for the next real snapshot broadcast to show the result.
- **Bearing/range math swapped from flat-plane geometry to real geodesy**: reused `bearingDegrees`/`distanceKm` from `toys/shared/fleet-state.js` (the same utilities `toys/bridge-2/` already uses), copied into this project's `public/` directory so Vite serves it verbatim.
- **Command token**: restarted the shared `fleetcore-serve` process (already `--bind-all` from the Bridge Station 2.0 LAN watch) with `--command-token bridge-3-0-lan` added — the first command-token ever configured in this project. Verified before building anything React: `POST /command` with no token still 401s, with the wrong token still 401s, with the correct token succeeds (200), and `GET /snapshot` (what `toys/bridge-2/` and `toys/fleetcore-live/` both use) is completely unaffected. The token is baked into Bridge Station 3.0's client bundle — acceptable under the already-established "LAN is the trust boundary" scope from 2.1's own packet, explicitly not acceptable as a real secret, and explicitly shared with anything else that knows it (including `toys/fleetcore-live/`'s own Command Token field, since it's the same backend process).

## Verification

Playwright against the deployed build via Granite's LAN address. Confirmed real seed-world callsigns render (MONAD, SCOUT ALPHA/BRAVO/CHARLIE, COASTER QESHM, DHOW LANTERN, GULF STAR, PILOT AMBER) rather than 2.1's mock placeholder names — direct proof this is live data, not the old mock state. Selected MONAD (had to correct the test script once: FleetCore sorts vessels alphabetically by id, so `traffic.*` entries sort before `vessel.monad`, putting MONAD at array index 4, not 0 — confirmed via the rendered label order rather than assumed), sent a real Set Waypoint command, and confirmed MONAD's own course changed from 249° to 044° over the following four real seconds — the actual backend physics turning the ship, not a client-side animation matching what 2.1 would have shown regardless of any backend. Mobile (390×844): the original component's own responsive rule still stacks cleanly. Zero console errors throughout every run.

## Follow-up

Label collision in the Fleet Motion panel when several vessels cluster tightly (visible in the final screenshot near the scout formation) is 2.1's original rendering behavior, unchanged — noted as a known limitation in the new README rather than fixed here, since this pass was scoped to data wiring, not a visual redesign. `toys/bridge-2/` already has a label-collision fix that could be ported over if this becomes a real problem. No reconnect-safe command queue, matching the same documented limitation on `toys/fleetcore-live/`. Reboot durability not addressed, per standing operator instruction for this whole deployment day.
