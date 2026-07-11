# Bridge Station Mk IV Engineering Report

## Summary

Bridge Station Mk III (previous revision of this report) replaced the three-way tab switch with a two-way split and made Fleet-Motion-originated selection changes visible across both live panels. It left one documented gap: a contact selected directly in Periscope was local to Periscope only and never propagated to Fleet Motion or Bridge's status rail.

Mk IV closes that gap. Periscope now writes `selection.selectedShipId` back into `MonadFleetState` when a contact is selected by direct user interaction (scope click, details button, or contact strip) — but not when Periscope's own selection changes because it auto-acquired Fleet Motion's selection, which would have created a feedback loop. Selection sync between Fleet Motion, Periscope, and Bridge is now genuinely bidirectional. Closing this required more than adding a write call: Fleet Motion, which is still the periodic writer of the rest of `MonadFleetState`, needed to check for externally-written selection changes on every animation frame rather than its own independently-throttled poll, or its own next scheduled write could land on stale local state and silently clobber Periscope's selection within a few seconds. This was caught by browser verification, not by inspection — see Validation Performed.

## Created Artifacts

No new top-level artifacts were created.

## Modified Artifacts

- `toys/periscope/app.js`
- `toys/fleet-motion/app.js`
- `toys/bridge/README.md`
- `toys/bridge/ENGINEERING_REPORT.md`
- `logs/captains/2026/2026-07-11_bridge-live-console.md` (Mk III)
- `logs/captains/2026/2026-07-11_periscope-selection-writeback.md` (Mk IV)

## Implementation Notes

- Collapsed the `plot` and `periscope` station tabs/panels into a single `console` station. Its panel (`#panel-console`, class `live-console`) is a CSS grid holding both instrument articles (`#liveFleetMotion`, `#livePeriscope`) so both iframes are mounted and visible simultaneously rather than one being `hidden`.
- Kept the Watchbook tab and panel untouched in behavior — it is still shown/hidden via the same `selectStation()` tab logic, unmodified except for the station id set shrinking from three entries to two.
- Kept the existing standalone `../fleet-motion/` and `../periscope/` "Open standalone" links and the station-links block intact.
- Added a CSS grid (`.live-console`) with two equal columns on desktop, collapsing to a single stacked column with scrollable overflow under 900px viewport width so the layout stays usable (not squeezed) on common mobile widths.
- Added a `syncPulse` CSS keyframe animation and `is-sync-pulse` class on `.live-instrument` panels for the selection-change cue.
- In `app.js`, `updateSharedState()` now reads `selection.selectedShipId` on every tick (both the 1s poll interval and the existing `storage` event listener) and compares it against the last-observed value. On a change, it calls `triggerSyncCue()`, which adds `is-sync-pulse` to both live-instrument panels and removes it after 900ms. The comparison is gated by a `hasObservedSelection` flag so the cue does not fire on first load.
- Did not modify Fleet Motion's or Periscope's simulation logic, and did not modify Watchbook.
- Did not change the `MonadFleetState` schema.

## Mk IV Implementation Notes

- `toys/periscope/app.js`'s `selectVessel(contact, { propagate = false })` gained an options parameter. The three call sites that originate from direct user interaction (scope click, details button, contact strip) now pass `{ propagate: true }`. The two call sites that don't represent a new user choice — `autoAcquireSharedContact()`'s re-selection when it adopts Fleet Motion's current selection, and `updateSelectedPanel()`'s per-frame refresh of the already-selected contact's live data — pass nothing, defaulting to `false`. Without that distinction, Periscope would echo Fleet Motion's own selection straight back to it every frame, which is harmless in itself (idempotent) but pointless churn, and more importantly would make it impossible to tell "Periscope is reflecting Fleet Motion" apart from "Periscope is asserting its own choice."
- A new `propagateSelection(contact)` in `toys/periscope/app.js` only fires for contacts with a `source` field set (i.e. contacts that came from `MonadFleetState` via `toScoutContacts()`), never for Periscope's own local demo vessels, which have no corresponding id in Fleet Motion's state to select. It reads the current shared state, and no-ops if `selection.selectedShipId` already matches (avoiding a redundant write on repeat clicks of the same contact).
- `toys/fleet-motion/app.js` gained `syncExternalSelection()`, called at the top of `animationFrame()` — before `advanceFleet()` (and therefore before `updateStatus()` -> `persistFleetState()`) runs. It compares `MonadFleetState.read()`'s `selection.selectedShipId` against a tracked `lastKnownSelectionId`; on a genuine external change it adopts the id into the local `selectedShipId` variable, triggers the same `flashAt()` cue `selectShip()` already used, and calls `updateStatus()`.
- The first version of `syncExternalSelection()` was throttled to once per second on its own timer, independent of `persistFleetState()`'s ~1.2s write throttle. Browser verification (see below) caught that this independent throttling reintroduced the exact clobbering problem this feature was meant to fix: Fleet Motion's own periodic write could fire on stale local state in the gap between two external-selection polls, silently overwriting Periscope's selection back to Fleet Motion's previous value. Localstorage would show the correct id for a moment, then quietly revert within a few seconds. The fix was to remove the independent throttle: `syncExternalSelection()` now runs unthrottled on every frame, which by construction always executes immediately before `persistFleetState()` in the same synchronous call chain, so `selectedShipId` is guaranteed current at the moment any write decision is made. This mirrors the existing precedent of Periscope's own `sharedContacts()`, which already does a full `MonadFleetState.read()` + JSON parse every animation frame with no reported performance issue in this codebase.
- `lastKnownSelectionId` is also updated on Fleet Motion's own successful writes (inside `persistFleetState()`), not just on adoption, so a value Fleet Motion itself just wrote is never mistaken for a new external change on the next frame's poll.

## Why both iframes had to be visible, not just present

Bridge Mk II already mounted all three iframes in the DOM at all times and only toggled a `hidden` attribute to switch between them. That was insufficient for this sprint's goal: browsers throttle or fully suspend `requestAnimationFrame` in `display:none` iframes, and Periscope's re-aim logic (`autoAcquireSharedContact`, `render()`) runs inside a `requestAnimationFrame` loop. With Periscope hidden, its render loop — and therefore its shared-state polling — does not reliably run, so the live sync built in `7003852` had no visible (or even actively running) audience. Making both panels part of the same always-visible grid, rather than switching between them, is what actually makes the sync observable.

## Resolved Gap: Periscope-originated selection now propagates

Mk III shipped with selecting a contact directly in Periscope (`selectVessel()` in `toys/periscope/app.js`) only updating Periscope's own local `state.selectedId` and detail panel, with no write to `MonadFleetState`. Mk IV closes this — see Mk IV Implementation Notes above. No `MonadFleetState` schema change was needed; the existing `selection.selectedShipId` field was already generic enough to carry a Periscope-originated id.

## Validation Performed (Mk III, retained)

- Ran `node --check toys/bridge/app.js` — no syntax errors.
- Served the repository root with `python3 -m http.server 8790 --bind 127.0.0.1`.
- Drove `http://127.0.0.1:8790/toys/bridge/` with a headless Chromium via Playwright (installed ad hoc into the scratchpad for this verification; not added to the repo).
- Verified Fleet Motion and Periscope are both visible at 1440×900 with no click, and both iframes resolve to their expected `src`.
- Dispatched a native click on an escort marker inside the Fleet Motion iframe. Confirmed: both `#liveFleetMotion` and `#livePeriscope` gained the `is-sync-pulse` class within the poll window; Periscope's own detail panel updated to the selected escort's name and bearing; the Bridge status rail's "Selected Vessel" field updated to match — all without a page or iframe reload.
- Resized to 390×844 (a common mobile width). Confirmed the two live panels stack vertically, each retaining a usable ~300px height within the viewport, rather than being squeezed side by side.
- Clicked the Watchbook tab. Confirmed the Watchbook panel becomes visible, the Live Console panel becomes hidden, and Watchbook's own content (log index, search, latest log) renders normally.
- Captured all browser console messages (`console` events and `pageerror`) throughout the run: none were emitted, so no new console warnings or errors were introduced.

## Validation Performed (Mk IV)

- Ran `node --check toys/periscope/app.js` and `node --check toys/fleet-motion/app.js` — no syntax errors.
- Served the repository root locally and drove `toys/bridge/` with headless Chromium via Playwright.
- Periscope-originated selection: clicked a contact button in Periscope's contact strip (`escort-bravo`, deliberately not whichever contact was already auto-acquired, so the click is unambiguously the cause). Confirmed Periscope's own panel updated immediately, Bridge's status rail updated to "Escort Bravo," and `localStorage`'s `MonadFleetState.selection.selectedShipId` read back `escort-bravo` directly from Fleet Motion's own frame.
- Caught the clobbering race described above: the first implementation showed Fleet Motion's own selection readout (`#stateSelectionValue`) still showing "MONAD" immediately after the click, still showing it 4s and 8s later, and `localStorage` reverting to `monad` by the 8-second mark — the write was being made and then silently undone. Fixed by removing `syncExternalSelection()`'s independent throttle (see Mk IV Implementation Notes). Re-ran the identical scenario after the fix: Fleet Motion's own readout showed "ESCORT BRAVO" immediately and held steady through 8 seconds of repeated checks, with `localStorage` never reverting.
- Fleet-Motion-originated selection (regression check for the Mk III behavior): called `selectShip("escort-charlie")` inside the Fleet Motion iframe directly. Confirmed the `is-sync-pulse` class appeared on both `#liveFleetMotion` and `#livePeriscope`, Bridge's status rail updated to "Escort Charlie," Periscope's panel updated to "SCOUT CHARLIE," and the pulse class cleared again after ~900ms (not stuck on) — all still working exactly as Mk III left it.
- Captured all browser `console` and `pageerror` events across every run: none were emitted.

## Validation Caveat

Fleet Motion's own splash/loading overlay is visible over its map on the initial screenshot in the sandboxed run; this is Fleet Motion's existing intro-sequence behavior (also present in the Mk II tabbed layout) and is unrelated to either sprint's changes. Mk IV verification did not re-check the 390×844 mobile layout, since neither sprint touched CSS/layout — only selection-sync JavaScript.

## Recommended Next Watch

A richer Bridge-native contact rail and direct station handoff (select a contact on Bridge, open Periscope already slewed to its bearing) remain good follow-on steps now that selection sync is bidirectional in both directions.
