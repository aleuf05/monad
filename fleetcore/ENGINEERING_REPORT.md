# FleetCore v1 Engineering Report

## Summary

FleetCore v1 implements the first deterministic local world prototype for Monad.

It is a Rust CLI that loads a seed maritime world, applies replayable commands, advances fixed deterministic ticks, writes local JSON state, appends JSONL events, exports browser-facing snapshots, and verifies replay determinism.

## Created Artifacts

- `fleetcore/Cargo.toml`
- `fleetcore/Cargo.lock`
- `fleetcore/README.md`
- `fleetcore/ENGINEERING_REPORT.md`
- `fleetcore/data/seed-world.json`
- `fleetcore/src/clock.rs`
- `fleetcore/src/command.rs`
- `fleetcore/src/event.rs`
- `fleetcore/src/lib.rs`
- `fleetcore/src/main.rs`
- `fleetcore/src/persistence.rs`
- `fleetcore/src/route.rs`
- `fleetcore/src/snapshot.rs`
- `fleetcore/src/vessel.rs`
- `fleetcore/src/world.rs`
- `fleetcore/tests/determinism.rs`
- `toys/shared/fleet-state.js`
- `docs/architecture/fleetcore-v1.md`
- `docs/architecture/fleetcore-data-contract.md`
- `docs/architecture/fleetcore-replay.md`

## Modified Artifacts

- `.gitignore`
- `toys/bridge/index.html`
- `toys/bridge/app.js`
- `toys/periscope/index.html`
- `toys/periscope/app.js`

## Implementation Notes

- FleetCore uses meters per second internally.
- FleetCore uses fixed integer ticks and deterministic simulation timestamps.
- Runtime state defaults to `data/fleetcore/`, which is ignored by Git.
- Seed state is tracked at `fleetcore/data/seed-world.json`.
- The CLI uses manual argument parsing to keep dependencies small.
- Browser toys remain standalone.
- Bridge reads through `MonadFleetState` when present and falls back to prior behavior.
- Periscope reads shared contacts when available and falls back to local demo contacts.

## Determinism Proof

The automated determinism test:

1. Loads the seed world.
2. Applies a fixed command sequence.
3. Advances deterministic ticks.
4. Appends events to JSONL.
5. Replays the event history from seed.
6. Compares final snapshot JSON exactly.

Passing this test is the primary FleetCore v1 acceptance proof.

## Validation Performed

- Ran `cargo fmt --manifest-path fleetcore/Cargo.toml -- --check`.
- Ran `cargo clippy --manifest-path fleetcore/Cargo.toml -- -D warnings`.
- Ran `cargo test --manifest-path fleetcore/Cargo.toml`.
- Ran JavaScript parse checks:
  - `node --check toys/shared/fleet-state.js`
  - `node --check toys/bridge/app.js`
  - `node --check toys/periscope/app.js`
- Ran CLI validation against a temporary state directory:
  - `init`
  - `set-time-scale 10`
  - `set-route vessel.monad ...`
  - `step 12`
  - `spawn-contact ...`
  - `record-watch-event ...`
  - `step 18`
  - `snapshot`
  - `replay`
- Confirmed CLI replay matched 6 events at final tick 300.
- Confirmed runtime `world.json`, `events.jsonl`, and `snapshots/snapshot.json` were written.
- Served the repository locally with `python -m http.server`.
- Browser-smoke validated Fleet Motion, Bridge Station, and Periscope Station in Chrome.
- Confirmed Bridge observed 7 shared contacts from Fleet Motion state.
- Confirmed Periscope rendered 7 shared contact cards from the shared helper.
- Confirmed no browser console errors in the final smoke run.

Note: Cargo emitted a Google Drive filesystem warning that hard-linking files in the incremental compilation cache failed and files were copied instead. This did not fail formatting, clippy, tests, or CLI replay.

## Known Limitations

- No daemon or service API.
- No database.
- No live browser polling.
- No collision physics.
- No autonomous agents.
- No global traffic model.
- Route movement is intentionally simple.
- Replay currently compares JSON snapshots rather than a compact hash.

## Recommended FleetCore v2 Direction

1. Add stable snapshot hashing.
2. Improve command validation and rejected-command events.
3. Add checkpoint manifest and recovery from latest checkpoint plus events.
4. Add shared-state fixture export for browser validation.
5. Keep networking deferred until file-contract integration is proven.
