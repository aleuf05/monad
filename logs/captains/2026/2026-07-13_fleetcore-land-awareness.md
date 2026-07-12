# FleetCore Land Awareness Watch Log

Date: 2026-07-13
Operator: Lt. cgl
Objective: give FleetCore itself a real concept of land — previously it had none at all, which the Harbor Pilot Boarding scenario's own "synthetic harbor point" gap made obvious.

## Problem

`fleetcore/src/*.rs` had zero references to land, coastline, terrain, or harbor. Every vessel was purely a lat/lng point on open water. The only "land" anywhere in this repo was `toys/fleet-motion/app.js`'s client-side `LAND_ZONES` — five rough hazard rectangles, explicitly documented as unenforced against the real backend ("the land-hazard check no longer blocks live waypoint placement — it has no server-side enforcement to be honest about"). Considered anchoring Harbor Pilot Boarding's synthetic harbor point to one of those zones for geographic plausibility, but checked first: the flagship's actual seed position (`HOME`, 20.5°N 63.2°E) is nowhere near any of the five zones, so hardcoding a zone-adjacent harbor point would only look right by the accident of however much live-testing had already dragged the flagship toward the Persian Gulf that session, and would be absurd (a "12-minute pilot launch" thousands of km away) whenever the flagship actually operates near its real home area.

## Fix

Gave FleetCore the same five zones Fleet Motion already draws, made them real:

- New `fleetcore/src/geography.rs`: `LandZone` struct, `land_zones()` returning the same five rectangles as `toys/fleet-motion/app.js`'s `LAND_ZONES` (same names, same bounds — deliberately not a second, divergent geography), `zone_containing()`/`is_on_land()` helpers.
- `fleetcore/src/world.rs`: `World::apply_command` now rejects `SpawnPassiveContact` if the spawn position is inside a zone, and rejects `SetRoute` if any waypoint is inside a zone — both return the existing `Err(String)` path, so they flow through the exact same `422`/WS `error` handling every other rejection already uses. No changes needed to `fleetcore/src/bin/serve.rs`.
- `fleetcore/src/snapshot.rs`: `WorldSnapshot` gained a `land_zones` field, populated fresh from `geography::land_zones()` on every snapshot. This is static reference data, not part of persisted `World` state (`persistence.rs` only ever reads/writes `World`, never `WorldSnapshot`), so it required no migration and carries zero risk to existing `world.json`/`events.jsonl`/checkpoint files.
- `docs/architecture/fleetcore-api.md`: documented the new `land_zones` snapshot field and the rejection behavior, and fixed a `spawn-passive-contact` example that (coincidentally) sat right on the Musandam Peninsula zone's western edge.
- `toys/fleet-motion/README.md`: corrected the now-false claim that land-hazard enforcement doesn't exist server-side. Left Fleet Motion's own client-side blocking off in live mode (not restored) — its existing WS `error` handler already logs `Command rejected — ...` for any command the server refuses, so a live route through a land zone now surfaces a real, specific rejection instead of being silently allowed through as before.
- `toys/fleetcore-control/README.md`: noted that Harbor Pilot Boarding's synthetic harbor point can now genuinely collide with a land zone and get rejected, and explained why the fix isn't to anchor the harbor point to real geography (see Problem above).

## Regression caught and fixed

`cargo test` failed immediately: `fleetcore/tests/determinism.rs`'s existing fixture spawned a test contact at `(26.1, 56.1)`, which sits inside the new Musandam Peninsula zone. Moved it to `(25.5, 58.0)` (open water just east of the zone) with a comment explaining why — the test checks determinism, not geography, so the exact position was never meaningful to what it verifies.

## Deployment

Rebuilt `fleetcore/target/release/serve` and restarted the single long-running `fleetcore-serve` process (`--port 4771 --bind-all --command-token bridge-3-0-lan`) from the same working directory, preserving `data/fleetcore/`'s persisted state (confirmed: tick and vessel count carried through the restart unchanged).

This is the same process Caddy's public `/monad/fleetcore-ws/*` reverse proxy already points at, so **the public API has land enforcement live now too, with no separate deploy step** — confirmed via `https://cameronlampley.com/monad/fleetcore-ws/snapshot` immediately after restart: reachable, `land_zones` present, vessel count unchanged.

## Verification

- `cargo test --release --manifest-path fleetcore/Cargo.toml`: all tests pass after the fixture fix.
- Direct `curl -X POST /command`: spawning at `(26.8, 55.9)` (inside Qeshm Island) rejected with `"spawn rejected: position (26.8, 55.9) is on land (Qeshm Island)"`; spawning at `(22.0, 60.0)` (open water) succeeded; routing the newly-spawned vessel through `(26.8, 55.9)` rejected with the equivalent `"route rejected: ..."` message.
- Ran the full Harbor Pilot Boarding sequence (all 6 clicks) against the restarted, land-aware server: completed with no rejections — the currently-computed harbor point and all four staged flagship legs happened to clear every zone, confirmed via a fresh snapshot fetch (flagship's real 4-leg route, `status: "underway"`, all 8 expected watch events).

## Known follow-ups, not done here

- Fleet Motion's own client-side `LAND_ZONES` check is still not restored for live mode — a rejected route now surfaces via the log after the fact rather than being blocked before sending. Restoring the preemptive client check would need touching `toys/fleet-motion/app.js`, out of scope for a FleetCore-side watch.
- The five zones are still rough bounding-box rectangles, not real coastline polygons, and cover only the Persian Gulf/Strait of Hormuz area — most of the operating world has no land data and defaults to open water.
- Harbor Pilot Boarding can still hit a land-rejection mid-run depending on the flagship's position when it starts; this is accepted, not fixed, per the reasoning above.

## Updated

- `fleetcore/src/geography.rs` (new)
- `fleetcore/src/lib.rs`
- `fleetcore/src/world.rs`
- `fleetcore/src/snapshot.rs`
- `fleetcore/tests/determinism.rs`
- `docs/architecture/fleetcore-api.md`
- `toys/fleet-motion/README.md`
- `toys/fleetcore-control/README.md`
