# Monad Bridge Station

Bridge Station Mk II is the unified command console for Vessel Monad. It gives the operator one front door for Fleet Motion, Periscope Station, Watchbook, and Bridge-owned engineering state while preserving every instrument as an independently runnable static artifact.

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

- Command Plot: Fleet Motion embedded as the operational map and route-control station.
- Periscope: Periscope Station embedded as the optical watch.
- Watchbook: the read-only operational log viewer.
- Engineering: Bridge-owned state rail for runtime condition, shared fleet state, contacts, and station status.

Each embedded instrument remains available as a standalone artifact through its existing route and an `Open standalone` link.

## Unified Console Model

Mk II uses a tabbed station deck rather than showing every iframe at once. This keeps the Bridge usable as a single page on laptops and tablets while avoiding a risky rewrite of Fleet Motion, Periscope, or Watchbook internals.

The station tabs are keyboard-operable with Arrow keys, Home, and End. The engineering rail remains visible beside the active station on desktop and stacks below the station deck on smaller screens.

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

## Mk III Direction

Bridge Station Mk III should deepen shared-state behavior without collapsing the instruments into one codebase. Good next steps are a richer contact list in the Bridge rail, direct station handoff actions such as selecting a contact then opening Periscope on its bearing, and a future Radar tab once the shared contact contract is mature.
