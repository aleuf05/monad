# Bridge Command Authority Rail Watch Log

Date: 2026-07-11
Operator: Commander Claude, Integration Watch
Directed by: Admiral C — asked for an impactful Bridge Station feature; recommended surfacing command authority in Bridge's own Engineering rail rather than leaving it buried inside the embedded Fleet Motion panel, and was told to implement it.

## Problem

Bridge Station calls itself "the unified command console," and as of the last watch it can genuinely command MONAD through its embedded Fleet Motion panel when given a `?commandToken=`. But nothing in Bridge's own chrome said whether that token actually worked — an operator had to open the Fleet Motion iframe and read its live-mode note to find out. That's a real gap for something billing itself as a command console rather than a viewer.

## Fix

- `toys/shared/fleet-state.js`: added `liveCommandAuthority` as a first-class field on the `MonadFleetState` contract, defaulting to `false` like every other field the normalizer defends.
- `toys/fleet-motion/app.js`: `createCanonicalFleetState()` now writes the existing `liveCommandAuthority` var (already tracked for the live-mode note and control-gating added last watch) straight into shared state — no new tracking needed, just one more field on an existing write.
- `toys/bridge/app.js` / `index.html`: new **Command Authority** row in the Status Board, read the same way Data Source already is (1s poll + `storage` event). Shows "Granted" (live class, matches Data Source's live styling), "Read-Only" (caution styling — live world visible, but this session can't act on it), or "N/A (Local Sim)" when not live at all.

## Verification

Playwright against the real `fleetcore-serve` on this box, three states:
- Forced local-sim fallback (`?fleetcoreServer=` at a dead port): `dataSource="Fleet Motion (Local Sim)"`, `commandAuthority="N/A (Local Sim)"`.
- Live, no token: `dataSource="FleetCore Live"`, `commandAuthority="Read-Only"` (caution styling).
- Live, `?commandToken=bridge-3-0-lan`: `dataSource="FleetCore Live"`, `commandAuthority="Granted"` (live styling).

Zero console errors in all three runs.

## Follow-up

None outstanding. Small, additive, backward-compatible schema change — existing consumers of `MonadFleetState` that don't know about `liveCommandAuthority` are unaffected.
