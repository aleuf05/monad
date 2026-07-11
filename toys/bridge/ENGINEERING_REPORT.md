# Bridge Station Mk III Engineering Report

## Summary

Bridge Station Mk III replaces the three-way tab switch (Command Plot / Periscope / Watchbook) with a two-way split: a default "Live Console" tab that composites Fleet Motion and Periscope side by side (stacked on narrow viewports), both visible and live-updating with no click required, and a "Watchbook" tab that keeps the lower-priority log viewer tab-switched exactly as before. Selecting a ship in Fleet Motion now visibly re-aims Periscope and pulses both panels, making the canonical fleet-state sharing landed in `7003852` ("Make Fleet Motion the canonical fleet-state source across instruments") visible to a first-time visitor instead of hidden behind a tab click.

## Created Artifacts

No new top-level artifacts were created.

## Modified Artifacts

- `toys/bridge/index.html`
- `toys/bridge/style.css`
- `toys/bridge/app.js`
- `toys/bridge/README.md`
- `toys/bridge/ENGINEERING_REPORT.md`
- `logs/captains/2026/2026-07-11_bridge-live-console.md`

## Implementation Notes

- Collapsed the `plot` and `periscope` station tabs/panels into a single `console` station. Its panel (`#panel-console`, class `live-console`) is a CSS grid holding both instrument articles (`#liveFleetMotion`, `#livePeriscope`) so both iframes are mounted and visible simultaneously rather than one being `hidden`.
- Kept the Watchbook tab and panel untouched in behavior — it is still shown/hidden via the same `selectStation()` tab logic, unmodified except for the station id set shrinking from three entries to two.
- Kept the existing standalone `../fleet-motion/` and `../periscope/` "Open standalone" links and the station-links block intact.
- Added a CSS grid (`.live-console`) with two equal columns on desktop, collapsing to a single stacked column with scrollable overflow under 900px viewport width so the layout stays usable (not squeezed) on common mobile widths.
- Added a `syncPulse` CSS keyframe animation and `is-sync-pulse` class on `.live-instrument` panels for the selection-change cue.
- In `app.js`, `updateSharedState()` now reads `selection.selectedShipId` on every tick (both the 1s poll interval and the existing `storage` event listener) and compares it against the last-observed value. On a change, it calls `triggerSyncCue()`, which adds `is-sync-pulse` to both live-instrument panels and removes it after 900ms. The comparison is gated by a `hasObservedSelection` flag so the cue does not fire on first load.
- Did not modify Fleet Motion's or Periscope's simulation logic, and did not modify Watchbook.
- Did not change the `MonadFleetState` schema.

## Why both iframes had to be visible, not just present

Bridge Mk II already mounted all three iframes in the DOM at all times and only toggled a `hidden` attribute to switch between them. That was insufficient for this sprint's goal: browsers throttle or fully suspend `requestAnimationFrame` in `display:none` iframes, and Periscope's re-aim logic (`autoAcquireSharedContact`, `render()`) runs inside a `requestAnimationFrame` loop. With Periscope hidden, its render loop — and therefore its shared-state polling — does not reliably run, so the live sync built in `7003852` had no visible (or even actively running) audience. Making both panels part of the same always-visible grid, rather than switching between them, is what actually makes the sync observable.

## Known Gap: Periscope-originated selection does not propagate

Acceptance testing surfaced that selecting a contact directly in Periscope (`selectVessel()` in `toys/periscope/app.js`) only updates Periscope's own local `state.selectedId` and detail panel. It never writes to `MonadFleetState`, so Fleet Motion's `selectedShipId` and Bridge's status rail do not reflect a Periscope-originated selection. This is a pre-existing limitation, not a regression introduced by this sprint.

Fixing it would require either (a) giving Periscope a write path into the shared state, or (b) extending the `MonadFleetState` schema to carry a second, Periscope-owned selection field. Both are out of scope for this sprint per its constraints (no modification to Periscope's simulation logic, no schema changes). This is intentionally left as a Mk IV follow-up — see the README's "Mk IV Direction" section — rather than fixed mid-sprint.

## Validation Performed

- Ran `node --check toys/bridge/app.js` — no syntax errors.
- Served the repository root with `python3 -m http.server 8790 --bind 127.0.0.1`.
- Drove `http://127.0.0.1:8790/toys/bridge/` with a headless Chromium via Playwright (installed ad hoc into the scratchpad for this verification; not added to the repo).
- Verified Fleet Motion and Periscope are both visible at 1440×900 with no click, and both iframes resolve to their expected `src`.
- Dispatched a native click on an escort marker inside the Fleet Motion iframe. Confirmed: both `#liveFleetMotion` and `#livePeriscope` gained the `is-sync-pulse` class within the poll window; Periscope's own detail panel updated to the selected escort's name and bearing; the Bridge status rail's "Selected Vessel" field updated to match — all without a page or iframe reload.
- Resized to 390×844 (a common mobile width). Confirmed the two live panels stack vertically, each retaining a usable ~300px height within the viewport, rather than being squeezed side by side.
- Clicked the Watchbook tab. Confirmed the Watchbook panel becomes visible, the Live Console panel becomes hidden, and Watchbook's own content (log index, search, latest log) renders normally.
- Captured all browser console messages (`console` events and `pageerror`) throughout the run: none were emitted, so no new console warnings or errors were introduced.

## Validation Caveat

Fleet Motion's own splash/loading overlay is visible over its map on the initial screenshot in the sandboxed run; this is Fleet Motion's existing intro-sequence behavior (also present in the Mk II tabbed layout) and is unrelated to this sprint's changes.

## Recommended Next Watch

Bridge Station Mk IV should close the Periscope-selection gap documented above, most likely by adding a narrow, additive write path for Periscope into `MonadFleetState.selection` rather than expanding the fields Fleet Motion itself owns. A richer Bridge-native contact rail and direct station handoff (select a contact on Bridge, open Periscope already slewed to its bearing) remain good follow-on steps once that gap is closed.
