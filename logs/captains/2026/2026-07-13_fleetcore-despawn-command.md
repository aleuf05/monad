# FleetCore Despawn Command Watch Log

Date: 2026-07-13
Operator: Lt. cgl
Objective: close the longest-standing documented gap in this session's FleetCore work — no way to remove a vessel, so the fleet only ever grows. Directly requested after the fleet-visibility fix made the growing pile of test debris (56+ vessels) visible everywhere instead of hidden by the old 7-slot cap.

## Fix

- `fleetcore/src/command.rs`: new `Command::DespawnVessel { id: String }`, the symmetric inverse of `SpawnPassiveContact`.
- `fleetcore/src/world.rs`: `World::apply_command` handles it — rejects an unknown id (matching `SetRoute`'s existing pattern), rejects any vessel that isn't `passive-traffic` kind (flagship and scout escorts are protected on purpose, named in the error message), otherwise removes it from `self.vessels`.
- `docs/architecture/fleetcore-api.md`: documented the new command and its two rejection cases.
- `toys/fleetcore-control/`: new "Manual: Despawn Vessel" form — a `<select>` populated with only `passive-traffic` vessels (matching the server's own restriction, so flagship/scouts are never offered), wraps `despawn-vessel`. Updated the page's top banner (previously "no undo yet... nothing to call") and the README's now-inaccurate "No despawn, no reset" section.
- `toys/fleetcore-control/README.md`: also updated Harbor Pilot Boarding's Reset Scenario Tracker note to point at the new despawn control for cleaning up a run's spawned vessels.

## Verification

- `cargo test --release` and a clean `cargo build --release --bin serve`: pass.
- Direct `curl -X POST /command` tests, all four cases: real passive contact despawns (vessel count -1); unknown id rejected (`"unknown vessel '...'"`); flagship despawn rejected (`"cannot despawn 'vessel.monad': only passive-traffic contacts can be removed, not a Flagship vessel"`); scout despawn rejected likewise.
- End-to-end UI test: despawned a real scenario-spawned contact from FleetCore Control Center while Fleet Motion (live mode, separate page) had it rendered on the map. Confirmed the marker actually disappeared from Fleet Motion's live map after the next snapshot — not just that the vessel count dropped — and confirmed via an independent `GET /snapshot` fetch that the vessel is genuinely gone from shared world state, not hidden client-side.
- Restarted the live `fleetcore-serve` process with the new binary (state preserved: same tick progression, same vessel count carried through). Zero console errors across every check.

## Known limitation, not addressed here

Still no bulk "clear the board"/reset command — only one-at-a-time despawn, and the flagship/scouts/clock can't be reset to a fresh starting state at all. Flagged, not built, since the ask was specifically the spawn/despawn symmetry gap.

## Updated

- `fleetcore/src/command.rs`
- `fleetcore/src/world.rs`
- `docs/architecture/fleetcore-api.md`
- `toys/fleetcore-control/index.html`
- `toys/fleetcore-control/app.js`
- `toys/fleetcore-control/README.md`
