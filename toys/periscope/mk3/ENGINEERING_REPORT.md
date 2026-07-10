# Periscope Station Mk III Engineering Report

## Summary

Mk III investigated whether Periscope Station should become a true bridge instrument consuming Fleet Motion state. The answer is yes architecturally, but not by directly wiring Periscope to Fleet Motion internals in this sprint.

Fleet Motion should become the authoritative vessel-state producer. Periscope should consume a shared, display-neutral contact contract and keep its existing bearing projection and rendering pipeline.

## Findings

Alpha, Bravo, and Charlie are currently generated locally in Periscope. They are defined in `toys/periscope/app.js` and animated by local `vesselState()` logic using base bearing, speed, wobble, and range drift.

Fleet Motion already has a canonical persisted state model in `toys/fleet-motion/app.js`. It writes browser-local state under `monad.fleetMotion.state` and includes MONAD, escort positions, headings, speeds, route state, escort mode, selected ship, and simulation clock.

Fleet Motion does expose a reusable contact model in concept, but not as a clean shared module. Its state helpers are embedded in the application file beside Leaflet rendering, route editing, UI controls, and local persistence.

## Architecture Recommendation

Defer direct integration for Mk III.

Recommended path:

1. Extract pure shared-state helpers into `toys/shared/fleet-state.js`.
2. Keep Fleet Motion as the writer and source of truth.
3. Add an adapter from Fleet Motion state to `monad.scoutContact.v1`.
4. Update Periscope to read shared state when present.
5. Keep Periscope's local demo contacts as a no-state fallback.

This gives future Radar, Scout Status Board, and other bridge instruments a common source without coupling them to Fleet Motion UI code.

## Why Integration Was Deferred

The integration is not large, but it is not risk-free:

- Fleet Motion's canonical state is not separated from the Fleet Motion app.
- Periscope currently uses bearing/range-first demo contacts, while Fleet Motion uses lat/lon vessel state.
- A correct bridge instrument needs a clear observer origin, likely MONAD position and heading.
- A direct read from `localStorage` would work, but would encode contract decisions before the schema is documented.
- Updating both toys requires validating Fleet Motion and Periscope together.

The cleaner move is to extract the contract first, then wire consumers.

## Created Artifacts

- `toys/periscope/mk3/ARCHITECTURE.md`
- `toys/periscope/mk3/CONTACT_MODEL.md`
- `toys/periscope/mk3/ENGINEERING_REPORT.md`

## Modified Artifacts

None outside the new Mk III documentation directory.

## Validation Performed

- Inspected `toys/periscope/app.js` for local contact generation, projection, selection, and details-panel dependencies.
- Inspected `toys/fleet-motion/app.js` for Fleet Motion state, escort model, persistence, and canonical state helpers.
- Verified repository status before editing.
- Verified generated documentation files exist under `toys/periscope/mk3/`.
- No runtime code was modified, so no browser regression test was required for this sprint.

## Recommended Mk IV

Implement the shared-state extraction:

1. Create `toys/shared/fleet-state.js`.
2. Move Fleet Motion schema constants and pure normalization helpers into it.
3. Add `toScoutContacts(fleetState)` with bearing/range derivation.
4. Update Fleet Motion to keep writing the same state through the shared helper.
5. Update Periscope to read shared contacts and fall back to its local demo contacts.
6. Validate both toys in browser.

Estimated effort: one focused implementation sprint.

## Known Limitations

- This sprint did not implement shared-state runtime code.
- The proposed schema is documentation only until Mk IV.
- Unit and conversion policy should be locked before implementation: Fleet Motion uses km/h while the proposed bridge contact model uses nautical units for instrument display.
