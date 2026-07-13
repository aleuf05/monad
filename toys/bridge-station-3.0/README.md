# Bridge Station 3.0

The merge: 2.1's operator loop (Select → Act → World changes → Instruments respond), wired to 2.0's real `fleetcore-serve` data. "Act" is genuinely real here — Set Waypoint sends an actual `set-route` `Command` over the WebSocket, and every panel re-renders from whatever snapshot the server broadcasts back. There is no local physics simulation left in this component at all; the real backend's tick loop is what actually moves the ship.

## What changed from 2.1

| | 2.1 | 3.0 |
|---|---|---|
| Data source | `initialVessels` + a local `setInterval` tick simulation | Live WebSocket to `fleetcore-serve`, no local state at all |
| Positions | Abstract 600×400 chart units | Real lat/lng, projected into chart space (see "Projection" below) |
| Set Waypoint | Mutates local mock state directly | Sends `{"type":"set-route","vessel_id":...,"route":[...]}` over the socket; the UI just waits for the next real snapshot |
| Auth | None (no backend to protect) | Server-granted command authority per connection — this is the first write-capable deployment in the project |
| Bearing/range math | Flat abstract-plane geometry | Real `bearingDegrees`/`distanceKm` (reused from `toys/shared/fleet-state.js`, same utilities `toys/bridge-2/` uses) |

`toys/bridge-station-2.1/` is untouched — this is a new artifact, not an edit to it, same as 2.1 didn't touch `toys/bridge-2/`.

## Projection: real lat/lng in an abstract chart

The original 2.1 component's Fleet Motion panel was built around a 600×400 abstract coordinate space, not geography. Rather than redesign the visual layout, `computeBounds()` takes the fleet's real lat/lng spread from the *first* snapshot received, pads it generously (60%), and freezes it — `toChart()`/`toGeo()` then convert between real positions and that fixed chart space for the rest of the session. Frozen rather than recomputed every tick for the same reason `toys/bridge-2/` centers its map once (`hasCenteredMap`): recomputing bounds every snapshot would make the whole view rescale and jump as vessels move, which reads as broken, not live.

## Command authority

Bridge Station 3.0 was the first deployment in this project to need write access. It originally carried a `COMMAND_TOKEN` baked into the client bundle (`src/App.jsx`) to satisfy FleetCore's read-only-by-default gate — since removed, once it turned out `fleetcore-serve` grants command authority to every connection unconditionally regardless of what token (if any) is presented (see `docs/deployment.md`'s "Known limitation" note). `serverUrl()` now connects with no token param at all; whatever authority the server decides to grant this connection is what you get.

## Run locally

```sh
cd toys/bridge-station-3.0
npm install
npm run dev
```

Needs a running `fleetcore-serve` reachable at the default URL, or override `?server=`.

## Build and serve

```sh
npm run build
npx serve -s dist -p 8070
```

## Deployment: LAN-only

Deployed at `http://192.168.0.100:8070/` — reachable from Granite's LAN, not the public internet, same posture as 2.0 and 2.1. Ad hoc `nohup npx serve ...` process, no systemd unit, does not survive a reboot — durability explicitly deferred, same as everything else deployed today.

## Verified

Playwright against the deployed build, using the LAN address: confirmed real seed-world callsigns render (MONAD, SCOUT ALPHA/BRAVO/CHARLIE, COASTER QESHM, DHOW LANTERN, GULF STAR, PILOT AMBER — not 2.1's mock `PILOT AMBER`/`CONVOY GAMMA` placeholder set, proving this is live data). Selected MONAD, sent a real Set Waypoint command, and confirmed the flagship's own course actually changed (249° → 044°) over the following real ticks — the real FleetCore backend physics turning the ship, not a client-side animation. Mobile (390×844): the original component's own `@media (max-width: 860px)` rule still stacks correctly, no overflow. Zero console errors throughout.

## Known limitations

- Contact labels near a tight cluster of vessels can overlap — this is 2.1's original label rendering (no collision avoidance), carried forward unchanged since this pass was about data wiring, not a visual redesign. `toys/bridge-2/`'s optics panel has a label-collision fix if this needs porting over later.
- No reconnect-safe command queue: a Set Waypoint click while the socket is mid-reconnect is simply lost, matching the same known limitation documented for `toys/fleetcore-live/`.
