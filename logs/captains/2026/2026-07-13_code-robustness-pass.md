# Code Robustness Pass Watch Log

Date: 2026-07-13
Operator: Lt. cgl
Objective: correctness/robustness review of this session's new FleetCore/Fleet Motion code (land awareness, despawn, live-fleet rendering) — not a security posture change, per explicit scope from the Admiral.

## Findings and fixes

**1. `fleetcore/src/world.rs` — panic risk in `SetRoute`'s land check.**

`route.iter().find(|point| geography::is_on_land(point))` followed by a second, separate `geography::zone_containing(waypoint).expect(...)` call. Currently always safe (both functions check the same zones against the same point, so the `.expect()` can never actually fire today) — but a panic inside `World::apply_command` runs under the server's shared `Mutex<World>`, so if a future refactor of either function ever let them disagree, this wouldn't just reject one command, it would poison the mutex and take down every future command on the live server. Fixed by using `find_map` to compute the zone once and use that result directly — removes the `.expect()`, the redundant second computation, and the correctness assumption that both functions stay in lockstep.

**2. `toys/fleet-motion/app.js` — `renderLiveVessels()` had no guard against a malformed vessel position.**

`upsert()` read `entity.position.lat`/`.lng` directly. FleetCore's `Vessel` struct makes `position` non-optional, so this is not reachable through normal use — but it's a genuine network boundary (JSON from a WebSocket), and a single bad or missing position would throw mid-`forEach`, aborting the whole render pass for *every* vessel, not just the bad one, and skipping the removal loop entirely (stale markers left on the map with no path to clean up until the next successful pass). Added a guard that skips just the one malformed entity (with a `console.warn`) instead of crashing the batch.

**3. `toys/fleet-motion/app.js` — `getShipPosition()`'s `escortStates[0]` fallback could throw on an empty array.**

Guaranteed non-empty in local-sim mode (`FORMATION` always has 3 entries) and in practice in live mode (`despawn-vessel` refuses to remove scouts), but not guaranteed by anything that would stop a custom or edited seed file from shipping zero scouts. Falls back to the flagship's own position instead of throwing on `undefined.position`.

## What I did not change

Scoped this to correctness/robustness only, not a security review — did not touch the `bridge-3-0-lan` token exposure (separate, already-settled decision this session: "don't rotate"), and did not add defensive checks for things that genuinely cannot happen given current code guarantees (e.g., did not add NaN-guards to every FleetCore command handler — `Position { lat: f64, lng: f64 }` deserializes from JSON numbers, and `serde_json` already rejects non-numeric JSON at the parse boundary before `apply_command` ever sees it).

## Verification

- `cargo build --release --bin serve` and `cargo test --release`: clean, all passing, no new warnings.
- Restarted the live `fleetcore-serve` process with the fixed binary — state preserved (tick and vessel count carried through).
- Re-ran land-rejection and flagship-despawn-protection checks directly against the restarted server: both still behave identically.
- Playwright regression: live mode fleet rendering unaffected (still shows the real vessel count); local-simulation mode forced offline still shows exactly 3 escorts + 4 contacts, unchanged.
- Full FleetCore Control Center contract check: connect/authority, pause/resume, a manual spawn→route→despawn round trip (each step confirmed via an independent snapshot fetch, not just UI state), and a scenario button — all still work correctly after both fixes.
- Zero console/page errors across every check.

## Updated

- `fleetcore/src/world.rs`
- `toys/fleet-motion/app.js`
