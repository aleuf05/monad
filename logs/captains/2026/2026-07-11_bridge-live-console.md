# Bridge Live Console Watch Log

Date: 2026-07-11
Operator: Lt. cgl
Objective: replace Bridge Station's tab-switched panels with a composited console so Fleet Motion and Periscope are visible together and their live selection sync (landed in `7003852`) has a visible audience.

## Problem

`7003852` made Fleet Motion the canonical fleet-state source and taught Periscope to re-aim live at Fleet Motion's selected ship, with Bridge surfacing the same selection in its status rail. All of that only mattered if a visitor never had to click away from one instrument to see the other — and Bridge's Mk II tab switch forced exactly that click. No watch log was written for `7003852`, so this entry also closes that gap.

## Integration

- Collapsed Bridge's three station tabs (Command Plot, Periscope, Watchbook) into two: a default "Live Console" tab that shows Fleet Motion and Periscope in the same always-visible grid, and an unchanged "Watchbook" tab.
- Both Live Console iframes now stay mounted and visible at once rather than one being `hidden` — this also matters functionally, since `display:none` iframes throttle `requestAnimationFrame`, which would have silently stalled Periscope's re-aim loop.
- Added a CSS `syncPulse` cue: when Bridge's poll of shared fleet state (or the existing `storage` event) observes `selection.selectedShipId` change, both live instrument panels flash an amber ring for 900ms.
- Live Console grid stacks to a single scrollable column under 900px viewport width so it stays usable on mobile rather than squeezing two panels side by side.
- Left Fleet Motion's, Periscope's, and Watchbook's own implementations untouched; left the `MonadFleetState` schema untouched.
- Updated `toys/bridge/README.md` and `toys/bridge/ENGINEERING_REPORT.md` to describe the Mk III layout and reasoning, and documented a known gap as a Mk IV follow-up: Periscope's own click-to-select is local only and does not write back to shared state, so a Periscope-originated selection does not yet update Fleet Motion or Bridge's status rail.

## Verification

Served the repository root with `python3 -m http.server 8790 --bind 127.0.0.1` and loaded `http://127.0.0.1:8790/toys/bridge/` in a headless Chromium via Playwright (installed ad hoc for this verification, not added to the repo).

Confirmed: Fleet Motion and Periscope both visible at load with no click; clicking an escort marker in the Fleet Motion iframe triggered the amber pulse on both live panels, re-aimed Periscope to the selected escort, and updated Bridge's "Selected Vessel" status field — all without reloading either iframe. Confirmed the layout stacks cleanly and stays usable at a 390×844 mobile viewport. Confirmed the Watchbook tab still opens Watchbook and hides the Live Console panel. Captured browser console output for the full run: no warnings or errors were emitted.
