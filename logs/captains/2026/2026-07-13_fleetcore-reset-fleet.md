# FleetCore Reset Fleet Command Watch Log

Date: 2026-07-13
Operator: Lt. cgl
Objective: add a reset control for the flagship and scout escorts, with clearly defined initial conditions — not arbitrary numbers, the values already established in `fleetcore/data/seed-world.json`.

## Design

- `fleetcore/src/command.rs`: new `Command::ResetFleet` (no parameters — a single, well-known target, not a configurable reset).
- `fleetcore/src/world.rs`: `initial_conditions()` returns the exact position/course/speed_mps/route for `vessel.monad`, `vessel.scout-alpha`, `vessel.scout-bravo`, `vessel.scout-charlie`, copied directly from `seed-world.json` rather than invented — kept as a hardcoded constant (not read from the seed file at reset time) since `World::apply_command` has no file I/O anywhere else and stays a pure in-memory state transition; a comment flags that both must be updated together if the seed's starting positions ever change deliberately.
- Passive-traffic contacts are untouched by design — `despawn-vessel` already exists for those, and the ask was specifically "Monad and escorts."
- A missing vessel id (shouldn't happen — the flagship and three scouts are permanent, `despawn-vessel` already refuses to remove scouts) is silently skipped per-vessel rather than failing the whole command.
- `toys/fleetcore-control/`: new "Reset Fleet" button next to Pause/Time Scale in the clock-controls row (same "global, affects everyone" category of control). Gated behind a `window.confirm()` — a misclick here silently overwrites the flagship's position for every connected visitor at once, more consequential than a single despawn.

## Verification

- `cargo build --release --bin serve` and `cargo test --release`: clean.
- Restarted the live server with the new binary (state preserved — tick and vessel count carried through, same as every restart this session).
- Direct `POST /command {"type":"reset-fleet"}` against the real server: all four vessels returned to exactly their seed values (position, course, speed, route, status `underway`); the passive-traffic count was unchanged.
- End-to-end UI test: manually routed Monad off-course via FleetCore Control Center, confirmed its position had actually changed via a fresh snapshot, then clicked Reset Fleet — confirm dialog text checked, accepted, and a fresh snapshot afterward showed Monad and scout-alpha back at (approximately, accounting for a tick or two of movement between the reset and the check) their seed positions. 51 passive-traffic contacts confirmed unchanged by the reset. Zero console errors.

## Updated

- `fleetcore/src/command.rs`
- `fleetcore/src/world.rs`
- `toys/fleetcore-control/index.html`
- `toys/fleetcore-control/app.js`
