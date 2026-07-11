# Bridge Mobile Live Console Layout Fix Watch Log

Date: 2026-07-11
Operator: Lt. cgl
Objective: verify Bridge Station's composited Live Console (Fleet Motion + Periscope + Radio Console, live-synced selection) actually holds up at a common mobile width, per the open item flagged in ENGINEERING_REPORT.md's Validation Caveat ("Mk IV verification did not re-check the 390×844 mobile layout").

## Problem

Every prior Live Console watch log claimed the mobile layout "stays usable," but the last time it was actually driven in a browser at 390×844 was Mk III — before Radio Console was integrated as a third panel in Mk V. Mk V's own validation checked Radio Console's own visibility and overflow at mobile width, but not Periscope's, on the assumption that nothing about Periscope's layout had changed.

That assumption was wrong. Mk V's `.live-console` CSS change (`grid-template-rows: minmax(0, 1fr) auto`, added to give Radio Console its own full-width row on desktop) leaked into the `@media (max-width: 900px)` stacked layout too, since the mobile override never reset `grid-template-rows`. Result: at mobile width, Fleet Motion and Periscope landed in the two pre-existing explicit row tracks (one flexible, one `auto`) instead of both getting the mobile rule's intended `grid-auto-rows: minmax(300px, 1fr)`. Periscope's `auto` track collapsed to intrinsic content size — its panel rendered at 215px (iframe itself only 150px), with its actual scope view (`.scope-frame`) sitting off-screen at `top: 319` inside a 1265px-tall document, reachable only via an unadvertised scroll inside the iframe. Fleet Motion and Radio Console were unaffected (Radio Console has its own hardcoded `height: 360px`, which is why the bug went unnoticed).

## Fix

`toys/bridge/style.css`, `@media (max-width: 900px)`: added `grid-template-rows: none;` so the mobile stack has no leftover two-row definition for panels to fall into — all three panels now size from the same `grid-auto-rows: minmax(300px, 1fr)` rule.

## Verification

Served the repository root with `python3 -m http.server 8899` and drove `http://localhost:8899/toys/bridge/` with headless Chromium via Playwright (installed ad hoc into the scratchpad, not added to the repo).

- Before the fix: measured Fleet Motion/Radio Console articles at 360px, Periscope at 215px (iframe 150px); confirmed via `getBoundingClientRect()` inside Periscope's own frame that `.scope-frame` was below the visible fold.
- After the fix: all three articles measure 360px; Periscope's iframe grew to 295px.
- No horizontal overflow before or after (`document.body.scrollWidth === window.innerWidth` held both times).
- Zero console/page errors captured across every run.
- Called `selectShip("escort-alpha")` inside the embedded Fleet Motion iframe at mobile width post-fix: Bridge's status rail updated to "Escort Alpha," confirming this was a layout-only defect — selection sync itself was never broken.
- Scrolled inside Periscope's own iframe document post-fix and confirmed the scope view, bearing dial, and nearest-contact readout are reachable.

## Known Remaining Gap

Periscope's panel is now sized fairly (equal to Fleet Motion and Radio Console), but its own internal document is still taller than the panel — reaching the scope view still requires an in-iframe scroll with no visible affordance hinting it's there. Radio Console solved the equivalent problem for itself with an `is-embedded` body-class trim; Periscope has no such mode. Adding one would touch `toys/periscope/app.js`/`style.css`, which is out of scope for a Bridge-side layout fix — logged as the next mobile-layout follow-up in both `README.md` and `ENGINEERING_REPORT.md`.

## Updated

- `toys/bridge/style.css`
- `toys/bridge/README.md`
- `toys/bridge/ENGINEERING_REPORT.md`
