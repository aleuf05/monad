# Monad Bridge Station

Bridge Station Mk V is the unified command console for Vessel Monad. It gives the operator one front door for Fleet Motion, Periscope Station, Radio Console, Watchbook, and Bridge-owned engineering state while preserving every instrument as an independently runnable static artifact.

## Run Locally

Serve the repository root:

```sh
python -m http.server 8080
```

Then open:

```text
http://localhost:8080/toys/bridge/
```

The Bridge is static HTML, CSS, and JavaScript. It requires no backend, database, authentication, build step, or package manager.

## Included Stations

- Live Console: Fleet Motion and Periscope Station rendered side by side (stacked on narrow viewports), both visible at once with no click required, with Radio Console running as a third, shorter panel below them for ambience.
- Watchbook: the read-only operational log viewer, reached through its own tab.
- Engineering: Bridge-owned state rail for runtime condition, shared fleet state, contacts, and station status.

Each embedded instrument remains available as a standalone artifact through its existing route and an `Open standalone` link.

## Unified Console Model

Mk III replaced the three-way Command Plot / Periscope / Watchbook tab switch with a two-way split: a Live Console tab that composites Fleet Motion and Periscope into one always-visible layout, and a Watchbook tab that keeps the lower-priority log viewer tab-switched as before. This makes Fleet Motion's canonical fleet-state sharing (introduced in `7003852`) visible to a first-time visitor instead of hidden behind a tab click — selecting a ship in either live instrument now visibly updates the other.

Both Live Console iframes stay mounted and visible simultaneously, which matters beyond aesthetics: browsers throttle `requestAnimationFrame` in `display:none` iframes, so keeping Periscope's render loop actually running (and therefore actually re-polling shared state) requires it to stay on screen rather than hidden behind a tab.

The station tabs are keyboard-operable with Arrow keys, Home, and End. The engineering rail remains visible beside the active station on desktop and stacks below the station deck on smaller screens.

At or below 900px width, all three Live Console panels stack into a single column and each gets an equal, fair minimum height (`grid-auto-rows: minmax(300px, 1fr)` with `grid-template-rows: none` clearing the desktop layout's two-row definition) — an earlier version of this rule left Periscope's row on the desktop layout's leftover `auto` track, squeezing it to ~215px while Fleet Motion and Radio Console kept their full height. See ENGINEERING_REPORT.md's Mk V.1 entry.

## Selection Sync

Selection sync is bidirectional. Fleet Motion writes `selection.selectedShipId` through the shared `MonadFleetState` contract (throttled to roughly every 1.2s, sooner via the same-origin `storage` event). Periscope reads that value on every animation frame and re-aims to the selected ship, and — as of Mk IV — a contact selected directly in Periscope (click on the scope, the details button, or the contact strip) writes `selectedShipId` back into the same shared state, so Fleet Motion's map and Bridge's status rail update to match. Bridge Station polls the shared state once a second and, in addition to the storage-event listener it already used to keep its status rail current, detects any change in `selectedShipId` regardless of which instrument caused it and fires a brief amber pulse on both Live Console panels so the sync reads as an intentional feature rather than something the visitor has to notice on their own.

Fleet Motion adopts an externally-written selection (i.e. one it didn't just write itself) on every animation frame rather than on its own throttled poll — this isn't just responsiveness, it's required for correctness. Fleet Motion is still the periodic writer of the rest of `MonadFleetState`, and if it only checked for Periscope's selection on a separate, independently-throttled timer, there was a real window where its own next scheduled write would fire on stale local state and silently overwrite Periscope's selection before Fleet Motion ever noticed the change. Checking every frame, immediately before any write decision, closes that race by construction rather than by tuning throttle intervals.

## Mk V: Radio Console

Radio Console (`toys/radio-console/`) runs as a third Live Console panel, below Fleet Motion and Periscope rather than beside them — it's a much shorter instrument (scripted chatter, controls, a compact signal meter and transcript) than the two full-height map/optics panels, so `.live-console`'s grid gives it its own full-width row (`grid-template-rows: minmax(0, 1fr) auto`) instead of squeezing into the two-column split.

Unlike Fleet Motion and Periscope, Radio Console shares no state with the rest of Bridge — it is a pure ambience/presentation layer requested explicitly to have no read or write path into `MonadFleetState` or FleetCore. Its own script detects `window.self !== window.top` and applies an `is-embedded` body class that trims its layout (hides the subtitle and eyebrow, shrinks headings and control padding, caps the transcript's visible height) specifically for Bridge's fixed, much shorter panel height — the same page otherwise runs full-size when opened standalone. See `toys/radio-console/README.md` for what the toy itself does.

## Shared State

Bridge Station reads Fleet Motion's browser-local canonical state from `localStorage` key `monad.fleetMotion.state` through `toys/shared/fleet-state.js` when that state is available on the same origin. It does not mutate that state.

The Engineering Status panel observes flagship state, active route counts, selected motion state, and shared contact counts when Fleet Motion has saved them.

If no Fleet Motion state has been written yet, the Bridge shows honest awaiting-state placeholders rather than fake telemetry.

## Live Mode (FleetCore)

Fleet Motion and Radio Console each independently default to attempting a live FleetCore connection on their own now (Admiral's call, 2026-07-11 — see their own READMEs), so Bridge doesn't need to switch anything on: loading Bridge normally already puts every embedded instrument that can go live into live mode, the moment each one's own connection lands. Fleet Motion's and Radio Console's embedded iframes still have no `src` in the Live Console's HTML by design — Bridge sets it once at load — and Bridge still passes its own `?fleetcoreServer=` straight through to both if you need to point every instrument at a non-default server URL. Periscope needs no changes to inherit Fleet Motion's live state, since it already composites whatever Fleet Motion writes to `MonadFleetState`. Radio Console's live connection is entirely separate from that — its own independent WebSocket, not routed through `MonadFleetState` at all. If no `fleetcore-serve` is reachable, every instrument falls back to exactly what it always was — same local simulation/scripted chatter, same behavior as before any of this existed. The Status Board's "Data Source" row reflects Fleet Motion's mode; Radio Console shows its own in its own status strip. See `toys/fleet-motion/README.md` and `toys/radio-console/README.md` for each instrument's live-mode contract.

## Commanding the Flagship

Bridge itself stays read-only and unauthenticated — it never mutates `MonadFleetState` and never holds a FleetCore token. But it now forwards a third param, `?commandToken=`, straight through to the embedded Fleet Motion iframe the same way it already forwards `?fleetcoreServer=`. If the token Fleet Motion presents to `fleetcore-serve` is granted command authority (`docs/architecture/fleetcore-api.md`), the controls with a real FleetCore command behind them come alive inside the embedded Fleet Motion panel: Set Waypoint (staged multi-leg routes, not just a single point), Cancel Route, Pause, and Time Warp. This is the same write path `toys/bridge-station-3.0/` proved out for Set Waypoint, minus that build's baked-in token — Bridge's copy of Fleet Motion is also the public deployment, so no token is hardcoded anywhere in this page or in `toys/fleet-motion/app.js`; an operator supplies one via the URL. Pause/Time Warp are global — they affect every connected visitor's clock, not just this Bridge session. Escort Mode, Suggest/Accept Detour, Return to Station, and Reset to Open Water have no FleetCore command at all yet and stay disabled regardless of authority; see `toys/fleet-motion/README.md`'s Live Mode section for the full breakdown.

## Boundaries

- No backend services.
- No networking beyond existing instrument behavior.
- No new simulation engine.
- No replacement of existing instruments.
- No WebGL or shader work.

## Mk VI Direction

A richer contact list in the Bridge rail and direct station handoff actions (selecting a contact then opening Periscope on its bearing) remain open, as does Radio Console's own v2/stretch scope (chatter that references live fleet state; a real broadcast source as a selectable channel — see `toys/radio-console/README.md`, both deliberately deferred). The Mk IV selection-sync gap (Periscope-originated selections not propagating) stays closed. Giving Periscope an embed-aware trim mode like Radio Console's `is-embedded` class, so its scope view doesn't need an in-iframe scroll on mobile, is the leading mobile-layout follow-up (see ENGINEERING_REPORT.md's Mk V.1 Known Remaining Gap).
