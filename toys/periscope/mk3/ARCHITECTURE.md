# Periscope Station Mk III Architecture

Mk III is an architecture investigation, not an integration sprint. The recommendation is to make Fleet Motion the authoritative source of vessel state, but to defer implementation until the shared contract is extracted deliberately.

## Current Source Of Truth

Periscope and Fleet Motion currently maintain separate world models.

Periscope:

- Defines Alpha, Bravo, and Charlie locally in `toys/periscope/app.js`.
- Generates observed bearing and range locally with `vesselState()`.
- Projects local contacts into the periscope field with `projectContact()`.
- Has no dependency on Fleet Motion state.

Fleet Motion:

- Defines the active vessel world in `toys/fleet-motion/app.js`.
- Simulates MONAD plus formation escorts from `FORMATION` and `escortStates`.
- Persists a canonical browser-local fleet state under `localStorage` key `monad.fleetMotion.state`.
- Includes positions, headings, speeds, route state, escort mode, and selection state.

Therefore Alpha, Bravo, and Charlie in Periscope are generated locally. They are not currently derived from Fleet Motion.

## Reusable Fleet Motion Model

Fleet Motion already has a useful state shape:

- `createCanonicalFleetState()`
- `createBaselineFleetState()`
- `normalizeFleetState()`
- `applyCanonicalFleetState()`
- persisted schema version `FLEET_STATE_SCHEMA_VERSION`

This is reusable in concept, but not yet reusable as a clean dependency. The model is embedded inside the Fleet Motion app file and mixed with map rendering, UI controls, route editing, persistence, and Leaflet marker state.

## Proposed Bridge Instrument Architecture

```text
Fleet Motion
      |
      v
Shared Fleet State
      |
      +-- Periscope Station
      +-- Fleet Motion Display
      +-- Future Radar
      +-- Scout Status Board
      +-- Future Bridge Instruments
```

Fleet Motion should author vessel state because it already owns:

- vessel position updates,
- heading and speed,
- escort formation behavior,
- route state,
- pause/time-warp behavior,
- persistence.

Periscope should consume an observation-ready projection of that state. It should not own vessel truth.

## Recommended Static-Frontend Pattern

No backend or networking is required for the next step. A static shared-state layer can work in-browser:

```text
toys/shared/
  fleet-state.js
  contact-contract.js

toys/fleet-motion/app.js
  imports or copies through shared state writer

toys/periscope/app.js
  reads shared state and adapts contacts into periscope projection
```

If the repo continues to avoid JavaScript modules for direct file opening, the shared files can expose one global namespace:

```js
window.MonadFleetState = {
  schemaVersion,
  storageKey,
  read(),
  write(),
  normalize(),
  toScoutContacts()
};
```

If serving from a local HTTP server is acceptable for bridge instruments, ES modules would be cleaner:

```js
import { readFleetState, toScoutContacts } from "../shared/fleet-state.js";
```

## Required Code Changes

Minimum clean integration:

1. Extract Fleet Motion's canonical state constants and normalization helpers into `toys/shared/fleet-state.js`.
2. Keep Fleet Motion as the writer for `monad.fleetMotion.state`.
3. Add a small adapter that turns Fleet Motion vessels into shared scout contacts.
4. Replace Periscope's local `vessels` and `vesselState()` source with a read from shared state.
5. Keep Periscope's existing `projectContact()` and rendering layer.
6. Add a Periscope fallback to local demo contacts when no shared state exists.

The critical adapter work is converting Fleet Motion lat/lon positions into Periscope-relative bearing and range. That requires a viewpoint definition, likely MONAD's current position and heading from Fleet Motion.

## Compatibility Notes

Periscope's current local contacts use:

- `baseBearing`,
- `range`,
- local wobble,
- local range drift,
- presentation-only mission/status/report fields.

Fleet Motion's current vessels use:

- lat/lon position,
- speed in km/h,
- heading degrees,
- blocked state,
- route and escort mode context.

These are compatible, but not identical. The shared contract should preserve Fleet Motion's real state and let Periscope derive observed bearing/range.

## Recommendation

Do not wire Periscope directly to Fleet Motion internals in Mk III.

Recommended next implementation is a small shared-state extraction sprint:

- Create `toys/shared/fleet-state.js`.
- Move only pure schema, storage, normalization, and adapter helpers.
- Have Fleet Motion keep writing canonical state.
- Have Periscope read shared state if available and fall back to local contacts if not.

This keeps the bridge architecture clean and avoids coupling Periscope to Leaflet, route editing, or Fleet Motion UI state.

## Integration Effort Estimate

Estimated effort: moderate, about one focused sprint.

Expected change surface:

- `toys/shared/fleet-state.js`: new shared module or global helper.
- `toys/fleet-motion/app.js`: small extraction and writer call cleanup.
- `toys/periscope/app.js`: replace local contact source with adapter input and fallback.
- Documentation and browser validation for both toys.

Primary risk is not math complexity. The risk is coupling two previously independent toys too tightly without first defining the shared contract.
