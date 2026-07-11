# Monad Bridge Station

Bridge Station Mk III is the unified command console for Vessel Monad. It gives the operator one front door for Fleet Motion, Periscope Station, Watchbook, and Bridge-owned engineering state while preserving every instrument as an independently runnable static artifact.

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

- Live Console: Fleet Motion and Periscope Station rendered side by side (stacked on narrow viewports), both visible at once with no click required.
- Watchbook: the read-only operational log viewer, reached through its own tab.
- Engineering: Bridge-owned state rail for runtime condition, shared fleet state, contacts, and station status.

Each embedded instrument remains available as a standalone artifact through its existing route and an `Open standalone` link.

## Unified Console Model

Mk III replaced the three-way Command Plot / Periscope / Watchbook tab switch with a two-way split: a Live Console tab that composites Fleet Motion and Periscope into one always-visible layout, and a Watchbook tab that keeps the lower-priority log viewer tab-switched as before. This makes Fleet Motion's canonical fleet-state sharing (introduced in `7003852`) visible to a first-time visitor instead of hidden behind a tab click — selecting a ship in either live instrument now visibly updates the other.

Both Live Console iframes stay mounted and visible simultaneously, which matters beyond aesthetics: browsers throttle `requestAnimationFrame` in `display:none` iframes, so keeping Periscope's render loop actually running (and therefore actually re-polling shared state) requires it to stay on screen rather than hidden behind a tab.

The station tabs are keyboard-operable with Arrow keys, Home, and End. The engineering rail remains visible beside the active station on desktop and stacks below the station deck on smaller screens.

## Selection Sync

Selection sync is bidirectional. Fleet Motion writes `selection.selectedShipId` through the shared `MonadFleetState` contract (throttled to roughly every 1.2s, sooner via the same-origin `storage` event). Periscope reads that value on every animation frame and re-aims to the selected ship, and — as of Mk IV — a contact selected directly in Periscope (click on the scope, the details button, or the contact strip) writes `selectedShipId` back into the same shared state, so Fleet Motion's map and Bridge's status rail update to match. Bridge Station polls the shared state once a second and, in addition to the storage-event listener it already used to keep its status rail current, detects any change in `selectedShipId` regardless of which instrument caused it and fires a brief amber pulse on both Live Console panels so the sync reads as an intentional feature rather than something the visitor has to notice on their own.

Fleet Motion adopts an externally-written selection (i.e. one it didn't just write itself) on every animation frame rather than on its own throttled poll — this isn't just responsiveness, it's required for correctness. Fleet Motion is still the periodic writer of the rest of `MonadFleetState`, and if it only checked for Periscope's selection on a separate, independently-throttled timer, there was a real window where its own next scheduled write would fire on stale local state and silently overwrite Periscope's selection before Fleet Motion ever noticed the change. Checking every frame, immediately before any write decision, closes that race by construction rather than by tuning throttle intervals.

## Shared State

Bridge Station reads Fleet Motion's browser-local canonical state from `localStorage` key `monad.fleetMotion.state` through `toys/shared/fleet-state.js` when that state is available on the same origin. It does not mutate that state.

The Engineering Status panel observes flagship state, active route counts, selected motion state, and shared contact counts when Fleet Motion has saved them.

If no Fleet Motion state has been written yet, the Bridge shows honest awaiting-state placeholders rather than fake telemetry.

## Boundaries

- No backend services.
- No networking beyond existing instrument behavior.
- No new simulation engine.
- No replacement of existing instruments.
- No WebGL or shader work.

## Mk V Direction

Bridge Station Mk V could add a richer contact list in the Bridge rail and direct station handoff actions such as selecting a contact then opening Periscope on its bearing. The Mk IV selection-sync gap (Periscope-originated selections not propagating) is closed — see `ENGINEERING_REPORT.md`.
