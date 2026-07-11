# Periscope Bearing Slew Watch Log

Date: 2026-07-11
Operator: Lt. cgl
Objective: make Periscope's optics visibly turn to an externally-selected contact instead of jump-cutting, now that Bridge's new contact roster (uncommitted, `2026-07-11_bridge-command-authority-rail.md` diff, not written by this watch) can select any contact regardless of its bearing relative to whatever Periscope is currently pointed at.

## Problem

`autoAcquireSharedContact()` (`toys/periscope/app.js`) set both `state.bearing` and `state.targetBearing` to the newly acquired contact's bearing in the same call. The render loop's smoothing (`state.bearing += shortestDelta(state.bearing, state.targetBearing) * 0.13` per frame) only does anything when the two values differ, so an externally-driven selection change was an instant jump-cut of the whole rendered ocean view — no visible turn. That already existed for Fleet-Motion-originated selections, but a large bearing jump was rare in practice since Fleet Motion's own map click UI naturally biases toward nearby contacts. Bridge's new roster makes an arbitrary, large jump the common case, which made the jump-cut much more noticeable and much more likely to read as a glitch.

## Fix

`autoAcquireSharedContact()` now only sets `state.targetBearing` (and resets `state.velocity` to clear any leftover drag momentum), leaving `state.bearing` for the existing per-frame smoothing to catch up — the same mechanism a manual drag release already uses. No other function changed; the existing "Contact acquired: NAME" field-note cue (`triggerAcquisitionCue`, called from `selectVessel`) still fires correctly on the same path.

## Verification

Served the repository root locally and drove `toys/periscope/` standalone with headless Chromium via Playwright — no Bridge/Fleet Motion needed since the bug and fix are both purely about how Periscope reacts to a `MonadFleetState` write, regardless of who wrote it.

- Wrote a shared state with two escort contacts roughly 90° apart in bearing (~000° and ~270°), selected the first, waited for Periscope to acquire it (`#bearingReadout` read `000°`).
- Flipped `selection.selectedShipId` to the second contact and sampled `#bearingReadout` repeatedly: 315° → 290° → 279° → 274° → 272° → 271° → 270°, settling cleanly over roughly 2-3 seconds with no oscillation or overshoot, versus an instant jump straight to 270° beforehand.
- Zero console/page errors in both the acquisition and re-acquisition runs.

## Updated

- `toys/periscope/app.js`
- `toys/periscope/README.md`
