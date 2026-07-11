# Fleet Motion Command Restoration Watch Log

Date: 2026-07-11
Operator: Commander Claude, Integration Watch
Directed by: Admiral C — flagged that Fleet Motion's live-mode integration had regressed the original interaction loop and much of it "doesn't make sense anymore"; separately requested a dedicated reset-to-initial-conditions control.

## Problem

Live mode (shipped earlier today, `logs/captains/2026/2026-07-11_fleet-motion-live-mode.md`) blanket-disabled almost every interactive control the moment a real `fleetcore-serve` connection landed, with no explanation shown anywhere in the UI — just a wall of greyed-out buttons. That reads as broken to a first-time visitor, and it's exactly the kind of "weakened flagship experience" the Integration Watch doctrine says should stop and get flagged, not ship silently.

Auditing `fleetcore/src/command.rs` and `world.rs` against what was actually disabled split the list three ways:

- **Real command exists, never wired** — `SetRoute` takes `Vec<Position>` (a full multi-leg route, not one point — last session's command-authority patch only ever sent a single point, collapsing staged waypoint threading down to "click once"). `PauseClock`/`ResumeClock`/`SetTimeScale` are real commands too, never sent at all.
- **No FleetCore command exists at all** — Escort Mode (cosmetic client-side formation drift, overwritten by live snapshots every tick regardless), Suggest/Accept Detour (FleetCore has no terrain model), Return to Station (fixed local-demo coordinate, no shared-world meaning), and the new Reset-to-Open-Water ask (FleetCore has no reset/teleport command, only `set-route`, which moves a vessel over real ticks).
- **Actively misleading** — the rough land-hazard boxes still rendered and still rejected live waypoint placement based on a rule the real backend doesn't enforce at all.

## Fix

**Restored (real command, now wired):**
- Set Waypoint now stages multi-leg routes exactly like local mode (arm, click, Shift-click for more, plain click finalizes) and sends the whole staged route as one `set-route` Command. Undo/Remove/Clear Waypoint edit the staged list client-side, same as before.
- Cancel Route sends `set-route` with an empty route (`world.rs` treats that as "clear course, go to Holding").
- Pause and Time Warp send real `pause-clock`/`resume-clock`/`set-time-scale` commands. Flagged to the Admiral before wiring, since these are global — one operator's Pause affects every connected visitor's clock, not just their own view — and confirmed: wire them in.
- The land-hazard check no longer blocks live waypoint placement (it has no server-side enforcement to be honest about).

**Stayed disabled, now explained:** Escort Mode, Suggest/Accept Detour, Return to Station, and the new Reset to Open Water button remain disabled in live mode regardless of command authority — no FleetCore command exists for any of them. A visible note above the control panel now says so explicitly (and says why authority alone won't unlock them), replacing the previous silent grey-out.

**New: Reset to Open Water button.** `resetFleet()` — flagship at HOME, escorts in formation, contacts scattered — already existed and already did exactly what was asked, but was only reachable through the quarantined scenario-preset UI (`INTERNAL_FEATURES.scenarioTools`, still off). Exposed it as its own button without touching that quarantine. Local-mode only, for the reset/teleport reason above.

## Verification

Against the real `fleetcore-serve` running on this box (`--command-token bridge-3-0-lan`), via Playwright:
- Read-only (no token): every write-capable control disabled, note shows the read-only explanation, zero console errors.
- Command authority granted: waypoint/pause/warp controls enabled, no-equivalent controls stay disabled, note shows the granted-authority explanation.
- Staged a 3-leg route (button-armed click + Shift-click + finalize click) — confirmed the real backend's snapshot received exactly 3 waypoints in order, not 1.
- Pause click → backend `clock_state` became `"paused"`. 10x click → backend `clock_state` returned to `"running"` with `time_scale: 10` (confirming the paired resume+scale send). Cancel Route → backend `route: []`, `status: "holding"`.
- Forced local-simulation fallback (`?fleetcoreServer=` pointed at a dead port) and re-verified staged multi-waypoint routing, time warp, and the new Reset to Open Water button all still work exactly as before this change — zero console errors, zero regressions to non-live mode.

## Follow-up

A true instant reset/teleport in live mode (position, not just route) would need a new FleetCore `Command` variant — that's a shared-core change to `fleetcore/src/command.rs`/`world.rs`, and Codex is reportedly working the FleetCore interface track independently in its own scope. Not attempted here; flagged rather than assumed, per doctrine on reconciling parallel tracks.
