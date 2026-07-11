# Periscope Embed-Aware Mobile Trim Watch Log

Date: 2026-07-11
Operator: Lt. cgl
Objective: close the mobile-layout follow-up flagged in the previous watch (`2026-07-11_bridge-mobile-live-console-fix.md`) — Periscope's panel now gets a fair share of height inside Bridge's Live Console grid, but its own internal document is still taller than that panel, so reaching the scope view required an in-iframe scroll with no visible hint it was there.

## Fix

Gave Periscope the same `is-embedded` mechanism Radio Console already has:

- `toys/periscope/app.js`: detects `window.self !== window.top` (try/catch-wrapped) and adds an `is-embedded` class to `<body>`.
- `toys/periscope/style.css`: `body.is-embedded` rules hide the eyebrow label, shrink the header and bearing readout, collapse the optics bar to one compact row (dropping the redundant magnification-text readout, since the button group's active state already shows it), tighten shell padding, and resize `.scope-frame` for the embedded viewport.

These overrides win regardless of viewport width, which matters: Periscope's existing width-based `@media` breakpoints assume a full phone screen and actually stack the header into two rows at ≤520px — worse, not better, for Bridge's ~348px-wide panel. `is-embedded` is scoped by embedding context (checked via `window.top`), not viewport width, so it doesn't fight those rules.

Standalone `toys/periscope/` never sets the class and is unchanged.

## Verification

Served the repository root locally and drove `toys/bridge/` and `toys/periscope/` with headless Chromium via Playwright.

- Embedded in Bridge at 390×844: `.scope-frame` moved from `top: 319px` (previously below the fold) to `top: 112px`, height 183px — now fully inside the 295px iframe viewport, no scroll required. Contact strip starts just past the fold instead of several hundred pixels down.
- Embedded in Bridge at 1440×900: zero console/page errors.
- Standalone Periscope at 390×844: confirmed `is-embedded` is never applied and the page renders at full size, unaffected.
- Zero console/page errors across every run.

## Known Remaining Gap

Periscope's contact strip wraps to 3-column rows and can still grow tall enough to push the vessel-detail panel below the fold when many contacts are visible at once. Not addressed here — flagged in ENGINEERING_REPORT.md's Recommended Next Watch if it comes up again.

## Updated

- `toys/periscope/app.js`
- `toys/periscope/style.css`
- `toys/bridge/README.md`
- `toys/bridge/ENGINEERING_REPORT.md`
