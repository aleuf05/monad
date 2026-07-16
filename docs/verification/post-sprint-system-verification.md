# Post-Sprint System Verification

**Date:** 2026-07-14
**Trigger:** Post-reboot verification of Monad / Living Fleet v0.1 (Effort B), following a real Granite reboot (boot 2026-07-14 01:36:32 UTC).
**HEAD at time of testing:** `686bc916a2c30a9d5232595f0c75f21de79a085d` (branch `agent/living-fleet-v0-1`; a second commit landed mid-verification from a concurrent contributor — see "Environment and Commands Used").

## Result

**PASS WITH WARNINGS**

The deployed system (FleetCore, Living Fleet captain runtime, captain memory, Caddy) came back cleanly from a real reboot, is currently healthy, and a full request-to-durable-state workflow was verified end to end through the public URL. One real, currently-active defect was found: an unbounded per-tick array embedded in every persisted world/checkpoint/snapshot file, driving steadily increasing disk write volume. It is not causing failures today but will degrade write latency and disk usage if left unaddressed — see "Defects Found."

## Architecture Observed

- **FleetCore** (`fleetcore/`, Rust) — deterministic world model. Two binaries share one library: `fleetcore` (CLI, one-shot commands against a state dir) and `serve` (`fleetcore-serve`, live HTTP+WebSocket server, systemd-managed). Persists to `data/fleetcore/{world.json, events.jsonl, checkpoints/, snapshots/snapshot.json}`. Checkpoints retain newest 120 + genesis; the event log is the durable history.
- **Living Fleet captain runtime** (`tools/living-fleet/captain_runtime.py`, `living-fleet.service`) — one shared process running three captains (Alpha/Bravo/Charlie). Polls FleetCore's snapshot, submits bounded `submit-escort-intent` commands via `POST /command`. Never mutates world state directly. Persists its own operational view (last 20 decisions/captain) to `data/living-fleet/runtime.json`. Opens no port.
- **Captain memory & identity** (`tools/living-fleet/memory/`, `living-fleet-memory.service` + `living-fleet-memory-reflect.timer`) — SQLite (WAL mode) at `data/living-fleet/memory.db`. A loopback-only read API (`inspector_server.py`, port 4772) is reverse-proxied publicly at `/captain-memory-api/*`. A 30-minute oneshot timer runs reflection/consolidation over stored episodes.
- **Edge** — Caddy serves `web/` directly at `https://cameronlampley.com/` (no deploy step) and reverse-proxies `/fleetcore-ws/*` → `fleetcore-serve` (loopback:4771) and `/captain-memory-api/*` → the memory inspector (loopback:4772).
- **No auth anywhere in this stack** — documented, accepted tradeoff (`docs/deployment.md`), not re-flagged here as new.
- **Health/status surface**: no dedicated `/health` endpoint on any service. `GET /snapshot` doubles as a liveness probe for FleetCore. Captain-level status (`captain_controls[].runtime_status`/`status_message`) is carried in every snapshot and rendered by the public Agent Ops page. `watchman.py` (a documented, already-built 5-minute heartbeat/health logger) is **not installed** as a systemd unit on this box — flagged, not fixed (needs a privileged install; see "Recommended Next Engineering Action").

## Environment and Commands Used

- No sudo available in this session (`sudo -n true` fails) — every privileged action (systemd restarts) is out of reach per `docs/commissioning-handoff.md`, so restart/recovery testing below was designed around what's verifiable without it: the real reboot that already happened, plus isolated copies of production binaries/data.
- `git rev-parse HEAD` moved from `c758db6` to `686bc91` mid-session (a concurrent contributor's commit, "Keep memory API within latency budget") — noted for the record; nothing in this report depended on that commit.
- FleetCore CLI/server binaries built clean from source (`cargo build --manifest-path fleetcore/Cargo.toml --bins`, debug profile; release binaries already existed from `install-living-fleet.sh`, timestamped 2026-07-13 22:57).
- All test commands and observed state are quoted verbatim below.

## Clean Startup

Two independent lines of evidence:

1. **The real reboot.** `caddy`, `fleetcore-serve`, `living-fleet`, `living-fleet-memory` all show `ActiveEnterTimestamp = 2026-07-14 01:36:32 UTC`, matching system boot, with `NRestarts=0` and `ExecMainStatus=0` — all four came up clean on the first try, no crash loop. `living-fleet-memory-reflect.timer` is `active`/`waiting` and has fired on schedule since (`OnBootSec=10min` → first post-boot run at 01:46:51, then 30-minute cadence exactly as configured).
2. **Isolated CLI cold start.** Using a scratch state directory (not touching production data):
   ```
   fleetcore/target/debug/fleetcore --state-dir <scratch> init
   fleetcore/target/debug/fleetcore --state-dir <scratch> inspect
   ```
   produced a fresh genesis world (tick 0, 4 vessels, empty event log) with no errors.

## End-to-End Workflow

Selected workflow: an operator command submitted through the **public** stack, all the way to durable on-disk state — the smallest real workflow that exercises every layer (Caddy → `fleetcore-serve` → `World::apply_command` → event log → `world.json`).

```
curl -s https://cameronlampley.com/fleetcore-ws/snapshot   # watch_events: 2 entries (baseline)

curl -s -X POST https://cameronlampley.com/fleetcore-ws/command \
  -H "Content-Type: application/json" \
  -d '{"type":"record-watch-event","message":"Post-sprint system verification: end-to-end check via public API, 2026-07-14T02:35Z"}'
# -> 200, new tick 65714, watch_events now has 3 entries including the new one
```

Verified durable and independently re-readable three ways after the command returned: (1) directly in `data/fleetcore/world.json` on disk, (2) via a fresh `GET http://127.0.0.1:4771/snapshot` call, (3) via the same public `https://cameronlampley.com/fleetcore-ws/snapshot` URL. All three agree. This is a real, reversible, low-risk operator action (an append-only log note) — no vessel state, routes, or captain intent were touched.

## Persistence Across Restart

- **Live production evidence:** `fleetcore-serve`'s `ActiveEnterTimestamp` (01:36:32, i.e. boot) shows the process restarted at reboot, yet its first observed tick after boot was already 64532 (not 0/genesis) — proof it loaded `world.json` from disk rather than reinitializing from seed. World state (5 vessels, 1479+ agent decisions, escort intents) was intact immediately post-restart.
- **Controlled, isolated restart proof:** in the scratch state dir, after `step 30` + `spawn-contact` + `record-watch-event`, a brand-new CLI process invocation (`inspect`) read back tick 30, event_sequence 3, and the new contact/watch event — each CLI invocation is itself a cold read of persisted state, so this is a real restart test, not a simulation.
- **`replay` command** (FleetCore's own built-in recovery proof): `replay matched from seed: 3 events, tick 30` — exact match.
- **Automated determinism suite:** `cargo test --manifest-path fleetcore/Cargo.toml` → all 6 integration tests pass, including `checkpoint_retention_keeps_newest_and_genesis`, `checkpoint_plus_event_tail_replays_to_current_world`, and `same_seed_events_and_ticks_replay_to_same_snapshot`.
- **Captain memory persistence suite:** `test_memories_beliefs_relationships_and_identity_survive_a_restart` and `test_rows_survive_a_fresh_connection` (part of the 30-test suite below) already assert this property in code; both pass.

## Failure and Recovery Test

**Component chosen:** the captain-memory scheduled reflection job (`run_scheduled_reflection.py`, normally fired by `living-fleet-memory-reflect.timer` every 30 minutes) — noncritical (world clock and captain decisions are unaffected if it never runs; a missed reflection just means less-refined guidance next cycle), and fully controllable without sudo (a plain Python subprocess, no systemd needed to exercise the same code path).

**Backup first:** production `data/living-fleet/memory.db` was WAL-checkpointed (`PRAGMA wal_checkpoint(TRUNCATE)`) and copied aside before any destructive test; production itself was never targeted by the crash test — all kills ran against copies. Verified production `PRAGMA integrity_check` = `ok` and `living-fleet-memory.service` still `active` after the checkpoint operation.

**Test:**
1. Copied the backup DB to a scratch working copy (15 pre-existing `reflections` rows).
2. Ran the real reflection script against the copy under `timeout --signal=KILL`, at 8 different short deadlines (15ms–120ms), to force a hard kill mid-run.
3. After each kill: `PRAGMA integrity_check` → `ok` every time; row counts unchanged (no partial writes observed — WAL mode plus per-statement commits meant the process was killed before or between transactions, not inside one).
4. Confirmed reads still work against the post-crash DB (`MemoryService.request_context()` succeeded, `identity_summary` present).
5. **Recovery:** re-ran the script normally against the crashed copy. Exit 0, all 3 captains reflected, `reflections` count went 15 → 18 (exactly 3 new rows, no duplicates from the earlier killed attempts).

**Result:** clean, idempotent recovery in every trial. One caveat: the script's actual DB-write phase is fast enough relative to Python interpreter startup that none of the 8 kill attempts is confirmed to have landed *inside* a multi-row write sequence (all showed 0 rows written, i.e. killed before writing started) — so crash-mid-write safety was inferred from WAL guarantees and per-statement commits in `store.py`, not directly observed. Flagged as a residual gap — resolved below (GitHub issue #14).

**Update, deterministic fault injection (resolves the caveat above):** timing-based kills couldn't reliably land mid-write, so instead of retrying with different delays, `store.insert`/`store.update` gained an optional `commit: bool = True` parameter, and `reflection.apply_reflection()` was rewritten to run every write for one triggered reflection (belief revisions, procedural lessons, relationship updates, trait shifts, the summary row) inside one shared transaction — `commit=False` on each individual statement, one `conn.commit()` at the end, `conn.rollback()` and re-raise on any exception. This closes a real gap the code comments already flagged as intentional-but-unenforced: before this, a crash between inserting a new superseding belief and updating the old belief's `status`/`superseded_by_belief_id` could leave a half-linked revision.

Two new tests (`tools/living-fleet/memory/tests/test_reflection_atomicity.py`) monkeypatch `store.insert` to raise a `RuntimeError` deterministically right after the *first* write of a multi-write reflection succeeds — guaranteed to land inside the belief-insert/belief-update pair, unlike the earlier timing-based attempts:
- `test_injected_failure_leaves_no_partial_state`: after the injected crash, `PRAGMA integrity_check` is `ok`, **and** no new belief exists, the old belief is still `active` with `superseded_by_belief_id` still `NULL`, and no procedural-lesson or reflections row landed either — the whole batch rolled back, not just the interrupted pair.
- `test_restart_then_clean_reflection_recovers_with_no_duplication`: closes and reopens the connection (simulated restart), then re-runs the same reflection cleanly — exactly one revision exists afterward, the old belief is correctly marked superseded, no duplicate from the rolled-back attempt.

Both pass. Full suite still green: 32/32 (`tools/living-fleet` + `tools/living-fleet/memory`), up from 30 — no regressions from threading `commit=False` through `identity.ensure_identity`/`apply_trait_shift` (all other call sites keep the `commit=True` default, unchanged behavior).

## Logs and Observability

- No tracebacks, restart loops, or `NRestarts > 0` on any of the 4 continuously-running units since boot.
- No duplicate/orphaned processes found.
- `living-fleet` journal shows a steady, plausible cadence of accepted captain decisions (roughly one every 5–17 seconds across 3 captains) with no repeated rejections or stuck states.
- `living-fleet-memory-reflect` journal shows exactly the expected cadence (10 min after boot, then every 30 min), each run completing in the same second it started.
- Durable state locations, confirmed present and current: `data/fleetcore/{world.json, events.jsonl, checkpoints/, snapshots/snapshot.json}`, `data/living-fleet/{runtime.json, memory.db}`.
- Gap: `monad-watchman` (the project's own designed-for-this heartbeat/health logger, `docs/watchman.md`) is not installed as a service on this box (`systemctl is-enabled monad-watchman` → not-found). Its absence isn't causing any current problem — the checks above cover the same ground manually — but it's the one piece of purpose-built observability tooling in this repo that isn't actually running.

## Defects Found

1. **Severity: Medium (currently latent, worsening over time) — Unbounded `vessel_events` array inflates every checkpoint, `world.json` write, and WebSocket broadcast without bound.**
   - **Evidence:** `vessel_events` currently holds 143,000+ entries and grows continuously (`docs/architecture/fleetcore-api.md` confirms by design it is "Never truncated server-side"). It is embedded in the full `World`/`WorldSnapshot` struct, so it's serialized into: `world.json` (rewritten in full on **every tick**, currently ~25.8 MB per write, at the default 1-second tick interval), every retained checkpoint (121 files retained, each a near-duplicate of the same growing array — `du -sh data/fleetcore` = 2.8 GB), `snapshots/snapshot.json`, and every WebSocket `snapshot` broadcast to every connected browser (Bridge Station, Agent Ops, FleetCore Live, FleetCore Control Center).
   - **Failure scenario:** disk usage and per-tick write I/O both grow roughly linearly with total elapsed sim time, with no cap. At current growth (~2.8 events/tick × 1 tick/sec), the array adds ~240k entries/day; the *write amplification* is worse than the content growth alone, since the entire multi-megabyte file is rewritten every second regardless of how much actually changed. This doesn't fail today (181 GB free, ticks still keeping up), but it is a live, compounding resource cost, and nothing currently caps or pages it.
   - **Recommendation:** this needs a real design decision, not a quick patch — options include capping in-memory/served `vessel_events` to a recent window with a separate append-only file for full history, adding a `since_sequence`/delta subscription mode to `/ws` so clients aren't re-sent the full history every tick, or excluding `vessel_events` from the checkpoint body entirely (checkpoints are recovery anchors, not the durable history — the event log already is). Deliberately not fixed here: it touches the wire contract multiple public toys already depend on, which is out of scope for a verification pass per this mission's own constraints ("preserve current behavior and interfaces," "no broad refactors").

2. **Severity: Low — `monad-watchman`, the project's designed heartbeat/health service, isn't installed.**
   - **Evidence:** `docs/watchman.md` describes it as "a permanent, non-LLM heartbeat process" meant to run continuously; `systemctl is-enabled monad-watchman` → `not-found`.
   - **Failure scenario:** no functional impact observed (this verification pass covered the same ground manually), but if Granite has an issue outside of what the app-level snapshot exposes (disk, Qdrant health, uptime discontinuities), nothing is currently logging it automatically.
   - **Resolution status:** installation is now consolidated into the current marker-gated `/home/cgl/cmd.sh` commissioning batch. It remains pending until that privileged handoff runs.

3. **Correction to the original audit — `web/status/fleet.json` is not orphaned.**
   - `web/fleet.html` loads `web/assets/js/fleet.js`, which fetches this file as its static physical-fleet roster. It is separate from FleetCore's simulated world by design. No deletion or migration is warranted from this report.

## Files Changed

- `docs/verification/post-sprint-system-verification.md` (this report — new).

No source, config, or data files were changed. All destructive/crash testing ran against scratch copies under the session scratchpad, never against production `data/`. One non-destructive, verified-safe operation (`PRAGMA wal_checkpoint(TRUNCATE)`) was run directly against the production memory DB as part of taking a clean backup; confirmed via `integrity_check` and continued service health immediately after.

## Tests Run and Results

- `cargo test --manifest-path fleetcore/Cargo.toml` — **6/6 passed** (3 determinism/persistence integration tests, 3 Living Fleet authority/fallback tests).
- `python3 -m unittest discover -s tools/living-fleet -p 'test_*.py'` — **32/32 passed** (captain runtime doctrine/fallback tests + full captain memory suite: belief revision, identity drift, salience, cross-captain isolation, seed-import idempotency, service/store restart-continuity, reflection atomicity).
- Two new regression tests added for the reflection-atomicity fix (GitHub issue #14) — see the Failure and Recovery Test section. The `vessel_events` growth defect (issue #6) remains an architectural/capacity issue tracked separately; see `docs/architecture/vessel-events-retention-investigation.md`.

## Remaining Risks

- `vessel_events` unbounded growth (Defect 1) — not urgent, but will keep getting more expensive every day it's left as-is; worth scheduling before it becomes a visible performance problem rather than after.
- ~~Crash-mid-write safety for the memory DB is inferred from WAL semantics, not directly observed under load.~~ **Resolved** — see the deterministic fault-injection update above (GitHub issue #14). `apply_reflection()` is now atomic at the per-reflection boundary and proven so by a fault that's guaranteed to land mid-sequence, not a timing race.
- No privileged-restart test was performed against the actual production `fleetcore-serve`/`living-fleet` systemd units in this session (no sudo available) — confidence in restart behavior rests on the real reboot that already occurred plus the isolated CLI-level restart proof, which together are strong but not identical to an operator-triggered `systemctl restart` under this session's control.
- `monad-watchman` gap (Defect 2) — staged in the current privileged commissioning package.

## Recommended Next Engineering Action

Issue [#6](https://github.com/aleuf05/monad/issues/6) tracks the required
`vessel_events` retention/wire design. Keep it separate from commissioning;
the likely direction is durable append-only history plus a bounded recent tail
in current state and live snapshots, after confirming consumer requirements.
