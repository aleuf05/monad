# Deployment Handoff: Issues #6, #13, #14

Date: 2026-07-14
Branch: `agent/living-world-intake-v0-1`
HEAD at time of writing: `74c063454dd39694d2542001e2104c52f33cd369`
Working tree: clean

## Issue #6 — FleetCore `vessel_events` unbounded growth

**Fix:** per-event monotonic `event_seq`, bounded retention (default 2000,
configurable), migration/trim of pre-existing state on load.

**Files changed:**
- `fleetcore/src/vessel.rs` — `event_seq: u64` field (+ `#[serde(default)]`)
  on every `VesselEvent` variant; `event_seq()`/`set_event_seq()` accessors.
- `fleetcore/src/world.rs` — `World.next_vessel_event_seq`,
  `World.vessel_event_retention` (default 2000); `record_vessel_event()` as
  the single push/trim site; migration + retention enforcement in
  `normalize()`.
- `fleetcore/src/snapshot.rs` — `vessel_event_retention` and
  `vessel_events_emitted_total` exposed in `WorldSnapshot`.
- `fleetcore/src/bin/serve.rs` — new `--vessel-event-retention <N>` CLI flag.
- `fleetcore/tests/vessel_events_retention.rs` — 5 tests (seq uniqueness,
  retention bound, restart/replay survival, migration of pre-existing
  state, trim of oversized pre-existing state).
- `toys/fleetcore-live/app.js` — consumer cursor changed from array-length
  slicing to `event_seq`-based filtering (`state.lastVesselEventSeq`),
  with gap-detection warning. **Source only** — not yet copied to
  `web/toys/fleetcore-live/app.js` (confirmed: `web/` copy has 0
  occurrences of `event_seq`, still running the old array-length logic).
- `toys/fleetcore-live/test_vessel_events_cursor.js` — 7 tests (Node `vm`
  module, no new dependency).
- `tools/mission-director/mission_director.py` — same cursor fix
  (`last_vessel_event_seq`) for the CLI mission tool.
- `tools/mission-director/test_cursor.py` — 7 tests.

**Test status:** `cargo test --manifest-path fleetcore/Cargo.toml` —
passing at last run. `node --test toys/fleetcore-live/test_vessel_events_cursor.js`
— passing. `python3 -m unittest tools/mission-director/test_cursor.py` —
passing.

**Remaining blocker:** the running `fleetcore-serve` binary predates this
change and has not been rebuilt/restarted with it. The live `web/`
JS client also predates it. Both require the deployment steps below.

## Issue #13 — Living World Intake never reached FleetCore

**Fix:** `/adjudications` HTTP handler compiled commands but never
submitted them. Added the actual submission call.

**Files changed:**
- `tools/world-intake/world_intake.py` — added `submit_to_fleetcore()`
  (line 203; POSTs to `FLEETCORE_COMMAND_URL`, default
  `http://127.0.0.1:4771/command`); wired into the `/adjudications` HTTP
  handler's `serve()` after `compile()`, via `intake.commit(command_id,
  submit_to_fleetcore)`.

**Test status:** existing `tools/world-intake/test_world_intake.py`
suite passing at last run.

**Remaining blocker:** the running `world-intake` service predates this
change and has not been restarted with it.

## Issue #14 — Captain-memory reflection non-atomicity

**Fix:** `apply_reflection()` could leave partial state on failure
mid-write. Rewrote to buffer all writes in one transaction.

**Files changed:**
- `tools/living-fleet/memory/store.py` — added `commit: bool = True` to
  `insert()`/`update()`.
- `tools/living-fleet/memory/identity.py` — threaded `commit` through
  `ensure_identity()`/`apply_trait_shift()`.
- `tools/living-fleet/memory/reflection.py` — `apply_reflection()` now
  wraps all writes with `commit=False`, single `conn.commit()` at the
  end, `conn.rollback()` + re-raise on exception.
- `tools/living-fleet/memory/tests/test_reflection_atomicity.py` — 2 new
  tests (injected mid-write failure leaves no partial state; restart
  recovers cleanly with no duplication).

**Test status:** passing at last run.

**Remaining blocker:** this fix is `commit: bool` threading inside the
Python module used by the `living-fleet-memory` service. Per the running
service's process model (systemd notes: this is understood to be a
long-running daemon, not a oneshot — confirm at deployment time), the
running process holds the old code in memory until restarted, same as
`fleetcore-serve` and `world-intake`.

## Exact deployment instructions

None of the three fixes are live. All three require a privileged restart
this session cannot perform (no sudo). The prior staged package
(`/home/cgl/cmd.sh`) was deleted at direct request earlier in this
session and no longer exists on disk. To deploy:

1. Rebuild FleetCore: `cargo build --release --manifest-path
   fleetcore/Cargo.toml --bins`.
2. Run full test suites as a pre-flight gate:
   - `cargo test --manifest-path fleetcore/Cargo.toml`
   - `python3 -m unittest discover -s tools/world-intake -p 'test_*.py'`
   - `python3 -m unittest discover -s tools/living-fleet/memory/tests`
3. Copy `toys/fleetcore-live/app.js` → `web/toys/fleetcore-live/app.js`
   (this is the one file with a source/deployed split; run `node --check`
   on the copy).
4. `sudo systemctl restart fleetcore-serve world-intake living-fleet-memory`.
5. Post-check: `curl -fsS http://127.0.0.1:4771/snapshot` and confirm
   `vessel_event_retention` and `vessel_events_emitted_total` are present
   in the response (proves the new binary is running).
6. Post-check: submit a test proposal through Living World Intake's
   `/adjudications` endpoint and confirm the response shows
   `canon_mutated: true` (proves #13's submission path is wired).

This is the same sequence the deleted `cmd.sh` automated (including
before/after evidence capture and rollback backups). A fresh version of
that script can be regenerated on request; it is not required to deploy
manually via the steps above.

## Current verified state (as of this document)

- Branch `agent/living-world-intake-v0-1`, HEAD `74c0634`, working tree
  clean, all commits pushed to origin.
- Services `fleetcore-serve`, `world-intake`, `living-fleet-memory`,
  `caddy` all reported `active` by `systemctl is-active`.
- No privileged deployment has occurred. All three fixes exist only in
  the git history above, not in the running services.
