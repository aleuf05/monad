# Bridge Command Token Field Watch Log

Date: 2026-07-11
Operator: Lt. cgl
Objective: let Bridge grant live command authority from its own chrome, closing the gap between the just-shipped Command Authority status row (display-only) and the fact that changing it still required editing the URL and reloading the whole page.

## Problem

Bridge's Status Board shows whether the current session has command authority ("Granted"/"Read-Only"/"N/A"), but the only way to change that state was to hand-edit `?commandToken=` into the URL and reload all of Bridge — awkward for something that calls itself a unified command console, and inconsistent with the new Contact Roster, which already lets an operator act on shared state directly from Bridge's own UI.

## Fix

- `toys/bridge/index.html`: added a `Command Token` form (password-type input + Apply button) in the Engineering panel, right after the status list.
- `toys/bridge/app.js`: `applyCommandToken(token)` rebuilds only `#liveFleetMotion iframe`'s `src` with `commandToken` set or cleared, preserving whatever `live`/`fleetcoreServer` params are already there, and mirrors the same change into Bridge's own URL via `history.replaceState`. Deliberately scoped to the Fleet Motion iframe only — Radio Console shares the `[data-instrument-src]` selector used for the initial page-load param passthrough, but it ignores `commandToken` entirely, and reloading it on every token change would interrupt whatever it's currently playing for no reason.
- `toys/bridge/style.css`: styled the new form to match the existing status-list/contact-roster look.

The token's exposure (visible in the iframe `src` and Bridge's own URL) is unchanged from what the manual `?commandToken=` URL param already had — this is a more convenient way to set the same thing, not a new capability or a new exposure. The field still masks on-screen entry.

## Verification

Playwright against the real `fleetcore-serve` already running on this box (`--command-token bridge-3-0-lan`, port 4771):

- Loaded Bridge with `?live=1`, no token: Command Authority read "Read-Only."
- Submitted the real token via the new field: Fleet Motion's iframe `src` gained `commandToken=bridge-3-0-lan`, Bridge's own URL updated to match, Command Authority flipped to "Granted," and Fleet Motion's own Pause control (disabled while read-only) became enabled — confirmed the grant was real, not just a status-row label change. Bridge itself did not reload.
- Cleared the field and resubmitted: both the iframe `src` and Bridge's URL dropped the token, Command Authority reverted to "Read-Only."
- Zero console/page errors across the whole run.

## Updated

- `toys/bridge/index.html`
- `toys/bridge/app.js`
- `toys/bridge/style.css`
- `toys/bridge/README.md`
- `toys/bridge/ENGINEERING_REPORT.md`
