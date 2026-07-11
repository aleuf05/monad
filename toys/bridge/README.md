# Monad Bridge Station

Bridge Station Mk I is the first integrated command deck for Vessel Monad. It composes the existing standalone instruments into one operational surface so visitors can see that the toys belong to one ship.

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

## Included Instruments

- Fleet Motion: embedded as the operational plot.
- Periscope Station: embedded as the optical watch.
- Watchbook: embedded as the operational log viewer.
- Engineering Status: Bridge-owned summary of current static runtime and observed Fleet Motion state.

Each embedded instrument remains available as a standalone artifact through its existing route and an `Open standalone` link.

## Shared State

Bridge Station reads Fleet Motion's browser-local canonical state from `localStorage` key `monad.fleetMotion.state` when that state is available on the same origin. It does not mutate that state.

The Engineering Status panel observes flagship state, active route counts, and passive local-traffic contact counts when Fleet Motion has saved them.

If no Fleet Motion state has been written yet, the Bridge shows honest awaiting-state placeholders rather than fake telemetry.

## Boundaries

- No backend services.
- No networking beyond existing instrument behavior.
- No new simulation engine.
- No replacement of existing instruments.
- No WebGL or shader work.

## Mk II Direction

Bridge Station Mk II should introduce a shared state helper under `toys/shared/`, then update Fleet Motion and Periscope to observe the same explicit contract instead of relying on ad hoc `localStorage` reads.
