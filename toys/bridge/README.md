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

Fleet Motion writes `selection.selectedShipId` through the shared `MonadFleetState` contract (throttled to roughly every 1.2s, sooner via the same-origin `storage` event). Periscope reads that value on every animation frame and re-aims to the selected ship. Bridge Station polls the same state once a second and, in addition to the storage-event listener it already used to keep its status rail current, now detects any change in `selectedShipId` and fires a brief amber pulse on both Live Console panels so the sync reads as an intentional feature rather than something the visitor has to notice on their own.

Periscope's own click-to-select interaction is local to Periscope only — it does not write back to `MonadFleetState`, so selecting a contact directly in Periscope does not (yet) update Fleet Motion or the Bridge status rail. See `ENGINEERING_REPORT.md` for this as a documented follow-up rather than a schema change made mid-sprint.

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

## Mk IV Direction

Bridge Station Mk IV should close the Periscope-to-Fleet-Motion selection gap (likely by giving Periscope a narrow, additive write path into `MonadFleetState.selection` rather than expanding the schema Fleet Motion owns), add a richer contact list in the Bridge rail, and consider direct station handoff actions such as selecting a contact then opening Periscope on its bearing.
