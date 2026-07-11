# Bridge Station Mk II Engineering Report

## Summary

Bridge Station Mk II turns the existing integrated command deck into a single unified console. Fleet Motion, Periscope Station, and Watchbook now live behind keyboard-operable station tabs, while Bridge-owned engineering state remains visible as a persistent rail.

## Created Artifacts

No new top-level artifacts were created.

## Modified Artifacts

- `toys/bridge/index.html`
- `toys/bridge/style.css`
- `toys/bridge/app.js`
- `toys/bridge/README.md`
- `toys/bridge/ENGINEERING_REPORT.md`

## Implementation Notes

- Preserved iframe composition so existing instruments remain independently operable.
- Added a tabbed station deck for Command Plot, Periscope, and Watchbook.
- Kept the Engineering Status rail visible beside the active station on desktop.
- Added an Active Station field to the shared engineering state.
- Kept shared-state reads routed through `toys/shared/fleet-state.js`.
- Did not rewrite Fleet Motion, Periscope, or Watchbook internals.

## Validation Performed

- Ran `node --check toys/bridge/app.js`.
- Served the repository root with `python -m http.server 8790 --bind 127.0.0.1`.
- Loaded `http://127.0.0.1:8790/toys/bridge/` in Chrome through Playwright.
- Verified Bridge Station loads with Command Plot active.
- Verified all three instrument iframes are present.
- Verified clicking the Periscope tab activates the Periscope panel and hides the Command Plot panel.
- Verified ArrowRight keyboard navigation moves from Periscope to Watchbook.
- Verified the Active Station engineering field updates with tab changes.

## Validation Caveat

The sandboxed browser run reported Fleet Motion iframe errors for the existing external Leaflet/OpenStreetMap dependency path (`ERR_NETWORK_ACCESS_DENIED`, then `L is not defined`). Those errors are not introduced by Bridge Mk II and reflect the validation environment blocking external network access. The Bridge-owned tab code and state rail executed during the same run.

## Known Limitations

- The Bridge still composes instruments through iframes, so deep cross-instrument actions are intentionally limited.
- The Bridge observes shared fleet state but does not command Fleet Motion or Periscope directly.
- Fleet Motion still depends on its existing Leaflet/OpenStreetMap tile behavior.

## Recommended Next Watch

Bridge Station Mk III should add a Bridge-native shared contact rail with contact selection and station handoff affordances. The likely first handoff is selecting a contact from Bridge and opening Periscope already slewed to that bearing, while preserving standalone Periscope operation.