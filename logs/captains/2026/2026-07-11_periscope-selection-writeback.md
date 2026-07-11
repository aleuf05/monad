# Periscope Selection Write-Back Watch Log

Date: 2026-07-11
Operator: Lt. cgl
Objective: close the documented Bridge Mk III gap where selecting a contact directly in Periscope never propagated to Fleet Motion or Bridge's status rail, making selection sync genuinely bidirectional.

## Problem

Bridge Mk III's engineering report flagged that `selectVessel()` in `toys/periscope/app.js` only updated Periscope's own local `state.selectedId` — it never wrote to `MonadFleetState`, so a Periscope-originated selection was invisible to Fleet Motion and Bridge. The report's own "Recommended Next Watch" named the fix directly: give Periscope a narrow, additive write path into `MonadFleetState.selection` without touching the schema or either instrument's simulation logic.

## Integration

- `toys/periscope/app.js`: `selectVessel(contact, { propagate = false })` gained an options parameter. The three call sites triggered by direct user interaction (scope click, details button, contact strip) pass `{ propagate: true }`; the two call sites that just reflect an already-current selection (auto-acquiring Fleet Motion's pick, and the per-frame panel refresh) don't, to avoid echoing Fleet Motion's own selection straight back at it every frame. A new `propagateSelection()` only fires for contacts sourced from shared state (`contact.source` set), never Periscope's own local demo vessels, and no-ops if the shared state already agrees.
- `toys/fleet-motion/app.js`: added `syncExternalSelection()`, called every animation frame before `advanceFleet()`, so it always runs immediately before `persistFleetState()` in the same frame. On detecting a genuine external change to `selection.selectedShipId`, it adopts the id locally and re-renders, using the same `flashAt()` cue `selectShip()` already used for a local click.

## The bug this caught

The first version of `syncExternalSelection()` was throttled to once per second on its own independent timer, separate from `persistFleetState()`'s ~1.2s write throttle. Browser verification caught that this let Fleet Motion's own periodic write land on stale local state in the gap between two external-selection polls — silently overwriting Periscope's selection back to whatever Fleet Motion last knew, typically within a few seconds. `localStorage` would briefly hold the correct value right after a Periscope click, then quietly revert. Bridge's status rail (polling independently) sometimes caught the value before the revert and sometimes didn't, which is what made this easy to miss on a single manual check.

Fixed by removing the independent throttle entirely: `syncExternalSelection()` now runs unthrottled every frame. Because Fleet Motion's `animationFrame()` always calls it before `advanceFleet() -> updateStatus() -> persistFleetState()`, this guarantees `selectedShipId` is fresh at the exact moment any write decision gets made, closing the race by construction instead of by tuning intervals. This mirrors an existing pattern already proven in this codebase: Periscope's own `sharedContacts()` already does a full shared-state read every animation frame with no reported performance cost.

## Verification

Served the repository root locally and drove `toys/bridge/` (which embeds both Fleet Motion and Periscope as live iframes) with headless Chromium via Playwright.

Periscope -> Fleet Motion: clicked `escort-bravo` in Periscope's contact strip (not the already-auto-acquired contact, so the click is unambiguously the cause). Confirmed Periscope's own panel updated immediately, Bridge's status rail showed "Escort Bravo," and reading `localStorage` directly from Fleet Motion's own frame confirmed `selection.selectedShipId === "escort-bravo"`.

First run (before the throttle fix) showed the bug directly: Fleet Motion's own selection readout stayed on "MONAD" immediately after the click and 4s and 8s later, and `localStorage` had reverted to `monad` by the 8-second check — confirming the clobber, not just a slow read. Re-ran after the fix: Fleet Motion's readout showed "ESCORT BRAVO" immediately and held steady across repeated checks at +4s and +8s, with `localStorage` never reverting.

Fleet Motion -> Periscope (regression check for the Mk III behavior, since this sprint touched `persistFleetState()`'s surrounding code): called `selectShip("escort-charlie")` directly in Fleet Motion. Confirmed the amber `is-sync-pulse` cue fired on both live panels and cleared again after ~900ms, Bridge's status rail showed "Escort Charlie," and Periscope's panel showed "SCOUT CHARLIE" — unchanged from Mk III.

Captured all browser console and page-error events across every run: none were emitted.

## Follow-up

None outstanding for selection sync specifically. Bridge's engineering report's "Recommended Next Watch" now points at a richer Bridge-native contact rail and direct station handoff (select on Bridge, open Periscope already slewed to that bearing) as the next reasonable step, now that sync is bidirectional in both directions.
