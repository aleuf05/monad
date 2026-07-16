# Vessel Events Retention — Investigation

**Status:** Investigated, then implemented per Command's rulings on GitHub
issue #6 (stable `event_seq` cursor — not `tick` alone, since events can
share a tick; configurable default `N = 2000`; `watch_events` and Mission
Director's persisted-cursor resilience both out of scope, the latter
resolved for free by the `event_seq` migration itself). See the issue
thread for the implementation summary: `fleetcore/src/vessel.rs` /
`world.rs` / `snapshot.rs` / `bin/serve.rs`, `fleetcore/tests/vessel_events_retention.rs`
(5 new tests), `toys/fleetcore-live/app.js`, `tools/mission-director/mission_director.py`.
**Not yet deployed live** — the running production `fleetcore-serve`
predates this change entirely; shipping it requires a rebuild + restart via
the standard privileged commissioning path, and the client-side JS fix is
deliberately not copied to `web/toys/fleetcore-live/` until that happens
(deploying the new cursor logic against the old server would make every
event's `event_seq` read `undefined`, permanently stalling the live feed).

This document's original text (below) reflects the investigation-only pass
that preceded implementation; it remains accurate as the record of what was
found and why, not as a live status report.
**Source:** GitHub Issue #6 ("Bound unbounded FleetCore vessel event
history"). Prepared for Commander integration.
**Current production evidence (2026-07-14, ~04:57 UTC):** 167,379
`vessel_events` at tick 74,346; `world.json` = 30,292,227 bytes (~30.3 MB);
`data/fleetcore/` = 3.3 GB across 121 retained checkpoints. Growing
continuously — the issue's own cited numbers (160,559 events / 29.0 MB / 3.1
GB) are already stale by comparison, confirming this is live and ongoing,
not a one-time historical spike.

## Consumer inventory: full history vs. recent tail

Grep for `vessel_events`/`vesselEvents` across the whole repository (not just
the files named in the tasking) found exactly these references on the
current branch:

| Location | Role | Needs full history, or only a recent tail? |
|---|---|---|
| `fleetcore/src/world.rs` (`World.vessel_events`, `apply_canon_change`-adjacent code at lines 576, 1059) | **Producer.** Pushed on `route-set` (a genuine `route_replaced`) and once per vessel per tick inside `advance_vessel` (only on actual waypoint arrival/route completion/holding transitions — not every tick of travel). | N/A (producer) |
| `fleetcore/src/snapshot.rs` | Copies `world.vessel_events.clone()` verbatim into every `WorldSnapshot`. | Currently: full history, unconditionally. **Observation, not requirement** — nothing downstream has been found that needs more than a recent tail (see below). |
| `fleetcore/src/persistence.rs` (`save_world`, `save_checkpoint`) | Serializes the *entire* `World` struct (including all of `vessel_events`) to `world.json` on every tick/command, and to a new checkpoint file every 60 ticks (`CHECKPOINT_EVERY_TICKS`, keeping newest 120 + genesis). | Full history embedded today; **not required** — see "Deterministic replay" below. |
| `fleetcore/src/bin/serve.rs` (`broadcast_snapshot`) | Broadcasts the full `WorldSnapshot` (JSON) to every connected WebSocket client, on every tick and every applied command. | Only a recent tail, per the one real consumer's own code (below) — it only ever looks at what's new since its last snapshot. |
| `toys/fleetcore-live/app.js` / `web/toys/fleetcore-live/app.js` (identical deployed copy) | **The only browser consumer.** `processVesselEvents()` (line ~224). | Only a recent tail — explicitly designed to diff "what's new since last snapshot," never re-reads old entries. |
| `tools/mission-director/mission_director.py` | A scripted mission-tracking CLI/service (Quacken Transit). Same pattern (`processed_vessel_event_count`, line 226/272-274). | Only a recent tail, same reasoning. |
| `docs/architecture/fleetcore-api.md` | Documents the contract (`vessel_events` "Never truncated server-side... a client wanting only what's new since its last look should diff against array length or the highest tick seen"). | Documentation, not a consumer — but it's the source of the "array length" idiom both real consumers follow. |

No other toy (`fleetcore-control`, `bridge`, `fleet-motion`, `periscope`,
`agent-ops`, `bridge-station-3.0`) reads `vessel_events` at all — confirmed
by the same repo-wide grep. `fleetcore-control` reads `watch_events` (a
separate, structurally analogous but out-of-scope field) via the same
length-cursor idiom (`renderWatchEvents`), which is why the doc describes
both together — noted for awareness, not investigated further here since
issue #6 is scoped to `vessel_events` only.

**Finding: nothing in this repository needs full `vessel_events` history at
read time.** Both real consumers are strictly incremental/tail-only by
design. This significantly simplifies the solution space.

## Compatibility hazards

**This is the headline finding, and it's a confirmed, evidenced bug pattern,
not a hypothetical:**

Both real consumers cursor on **raw array length**, not on any stable
per-event identifier:

```js
// toys/fleetcore-live/app.js
function processVesselEvents(vesselEvents) {
  if (vesselEvents.length === state.processedVesselEventCount) return;
  vesselEvents.slice(state.processedVesselEventCount).forEach(...);
  state.processedVesselEventCount = vesselEvents.length;
}
```
```python
# tools/mission-director/mission_director.py
new_events = vessel_events[state["processed_vessel_event_count"]:]
state["processed_vessel_event_count"] = len(vessel_events)
```

Every `VesselEvent` variant already carries a `tick: u64` field (confirmed
in `fleetcore/src/vessel.rs`), but neither consumer uses it as a cursor —
both use `array.length` as a stand-in for "how many I've already seen."

**Failure mode if the array is ever naively shortened (rotated/capped):** if
the server-side array's length ever becomes *smaller* than a client's
already-recorded `processedVesselEventCount`/`processed_vessel_event_count`,
`array.slice(largeOffset)` (JS) and `list[large_offset:]` (Python) both
silently return an empty result — **no error, no exception, just silent,
permanent loss of every subsequent event** until that specific client
process restarts (browser tab reload) or, for `mission_director.py`, until
someone manually resets its persisted state file.

**This hazard already exists today, latently, and is not hypothetical
speculation about a future bug:** `toys/fleetcore-live/app.js` has a
WebSocket auto-reconnect loop (`reconnectDelayMs`, `reconnectTimer`) that
never resets `state.processedVesselEventCount` on reconnect — confirmed by
grep; the counter is only ever initialized once, at module load. If
`fleetcore-serve` restarts today while a browser tab stays open (auto-
reconnecting rather than being reloaded) and, for any reason, comes back
with a `vessel_events` array shorter than what that tab had already counted,
the tab silently stops receiving vessel-event updates. This is rare today
only because the array currently never shrinks during a process's lifetime.
**Any bounding/rotation scheme would convert this from a rare edge case into
a routine occurrence on every rotation cycle.** `mission_director.py`'s
version is worse in one respect: its cursor is persisted to disk
(`save_state`), so a stale cursor survives even a full process restart of
the mission tracker itself, with no page-reload-equivalent recovery path.

**Conclusion: server-side truncation is not safe to ship until the
consumer-side cursor logic changes first (or the server gives clients an
explicit signal to resync).** This is a hard sequencing constraint, not a
preference.

## Smallest versioned architecture preserving complete durable history

**Key architectural observation, confirmed by reading the code, not
assumed:** `vessel_events` is **fully derived/reconstructible state**, not
an independent source of durable history.

- `World::replay_event()` (`fleetcore/src/world.rs:932`) just calls
  `self.apply_command(event.command.clone())` — the *exact same* function
  used for live command/tick processing, which is exactly where
  `vessel_events.push(...)` happens (both producer sites). Replaying
  `events.jsonl` from the seed (or from a checkpoint + event tail,
  `persistence::replay_from_latest_checkpoint`) therefore regenerates the
  complete, byte-identical `vessel_events` sequence as a side effect —
  nothing about it is stored anywhere *except* as a derived field of
  whatever `World` state currently exists in memory/on disk.
- The actual durable, never-pruned source of history is `events.jsonl`
  (append-only, confirmed never truncated anywhere in `persistence.rs`) plus
  the seed world. This matches this repo's own existing doctrine
  (`docs/architecture/fleetcore-data-contract.md`: "The append-only event
  log, not the checkpoint set, is the durable history").

**Consequence:** bounding what's embedded in the *live* `World` struct (and
therefore in `world.json`, checkpoints, and live snapshots/broadcasts) does
not discard any durable history, because none of it was uniquely stored
there in the first place — `events.jsonl` already has everything, and
already will continue to, unmodified. This is what makes the retention
architecture "smallest": no new archival subsystem is needed for what
already exists.

**Proposed direction (this is a proposal, not a decision made in this
investigation):**

1. Cap `World.vessel_events` to the most recent *N* entries (candidate: a
   count, not a tick window, since events fire irregularly — e.g. "last
   2,000 events," sized well above any observed single-poll gap for either
   consumer). Applied uniformly wherever the field is populated — the live
   in-memory struct, so it's automatically inherited by `save_world`,
   `save_checkpoint`, and `snapshot()`/broadcast, with no separate logic
   needed in three places.
2. Do **not** add a second durable store for "the rest" of the history —
   `events.jsonl` already is that store. If a real future consumer needs
   older `vessel_events` specifically (not just `Command`/`Event` replay
   output), build a small offline tool that replays `events.jsonl` and
   filters — not investigated further here since no current consumer needs
   it (see Consumer inventory).
3. Version the change (`schema_version` on `WorldSnapshot` already exists —
   `monad.worldSnapshot.v1`) so any future consumer can detect whether it's
   talking to a bounded-history server, though in practice today's two
   consumers need code changes regardless of versioning (see next section).

## Deterministic replay and checkpoint implications

- **Replay (`fleetcore/src/tests/canon.rs`-style determinism tests, and
  `cargo test`'s existing `same_seed_events_and_ticks_replay_to_same_snapshot`
  / `checkpoint_plus_event_tail_replays_to_same_world`):** unaffected in
  principle, since replay reconstructs `vessel_events` fresh from
  `events.jsonl` every time regardless of what any prior checkpoint's
  `vessel_events` field happened to contain. **But**: if checkpoints
  themselves start storing a *bounded* `vessel_events` (per the proposal
  above), then `replay_from_latest_checkpoint`'s existing exact-equality
  assumption (`checkpoint_plus_event_tail_replays_to_current_world`
  presumably asserts the replayed world equals the live one field-for-field)
  needs to keep holding — which it would, as long as the *replay path*
  applies the identical bounding logic as the live path (i.e., bounding has
  to happen inside `apply_command`/`advance_vessel`'s push site itself, not
  as a separate post-processing step only run on the live path). This is an
  implementation-correctness requirement to get right, not a blocker.
- **Checkpoint retention (`MAX_RETAINED_CHECKPOINTS = 120`, keep-genesis
  rule):** unaffected in count/policy. The *size* of each retained
  checkpoint drops dramatically once `vessel_events` is bounded within each
  one, which directly addresses the 3.3 GB `data/fleetcore` figure (roughly
  121 × current-world-size today; roughly 121 × a small bounded size after).
- **Migration of existing large `world.json`/checkpoints:** on first load
  after a bounding change, `World::normalize()` (already called by
  `load_world_from` on every load) would need to also enforce the new bound
  (truncate to the newest N on load, not just on push) — otherwise an
  already-oversized `world.json` from before the change stays oversized
  until the next natural rotation. This is a one-line addition to
  `normalize()`'s existing responsibilities, not a separate migration
  script, but it needs a test asserting a pre-existing over-bound
  `vessel_events` gets trimmed on load.

## Failure modes and recovery behavior

| Failure mode | Cause | Recovery |
|---|---|---|
| Silent event loss on a long-lived client (see "Compatibility hazards") | Length-based cursor larger than a rotated array's new length | **Must be fixed client-side before server-side bounding ships** — see Decisions requiring Command approval |
| Replay/checkpoint mismatch (`vessel_events` differs between live and replayed world) | Bounding logic applied inconsistently between the live push path and replay | Caught by existing determinism tests if extended to assert on `vessel_events` specifically, not just top-level snapshot equality (current tests may already do this via whole-struct equality — needs confirming, not assumed here) |
| Oversized `world.json`/checkpoints persisting after the code change ships | No on-load enforcement of the new bound | One `normalize()` addition + a regression test loading a pre-existing oversized fixture |
| Legitimate future consumer needs history older than the bound | By design, older entries are gone from the live/snapshot path | Recoverable via `events.jsonl` replay (see architecture section) — not automatic, needs a purpose-built tool if/when a real need appears |

## Pass/fail acceptance tests (proposed, not yet written)

1. `vessel_events` length never exceeds the chosen bound *N* in `world.json`,
   every retained checkpoint, and every live snapshot/broadcast, after a
   sustained run well past *N* pushes.
2. Replay from seed + full `events.jsonl` past *N* pushes produces a
   `vessel_events` tail identical (same last-N entries, in order) to the
   live bounded state at the same tick/sequence — proving replay and live
   bounding stay consistent, not just individually correct.
3. Loading a pre-existing, over-bound `world.json`/checkpoint fixture (a
   real oversized file, not synthetic) results in a correctly-trimmed
   in-memory state after `load_world_from`.
4. `checkpoint_plus_event_tail_replays_to_current_world`-style test
   continues to pass with bounded `vessel_events` included in the equality
   assertion (extend the existing determinism test rather than adding an
   unrelated one, if it doesn't already cover this field).
5. **Client regression (new, not existing today):** a scripted test against
   `toys/fleetcore-live/app.js`'s `processVesselEvents` (or its post-fix
   equivalent) proving that a server restart/rotation that shrinks the
   array is detected and resynced, not silently dropped. Needs the client
   fix to exist first — this test doesn't pass against current code.
6. Same for `mission_director.py`'s cursor handling, including the
   persisted-state-across-restart case specifically (its worse failure
   mode).

## Benchmark/evidence plan (proposed)

- Before/after `world.json` size at a fixed tick count well past the bound.
- Before/after `data/fleetcore/` total size with checkpoints at steady
  state (120 retained).
- Before/after per-tick `save_world` wall-clock time (the actual write
  latency risk flagged in the earlier verification report) — measure, don't
  assume; the write is already a temp-file-write-then-rename
  (`persistence.rs::write_json`), so the risk is CPU/IO time for
  serializing tens of MB every second, not corruption risk.
- Before/after WebSocket broadcast payload size per tick, and (if
  measurable) server CPU time in `broadcast_snapshot` under N connected
  clients.
- Confirm growth trend flattens post-fix by sampling `vessel_events.length`
  and `world.json` size at fixed tick intervals over a sustained run,
  comparing slope before/after.

## Phased senior/junior task split (proposed)

**Senior (design-and-correctness-critical):**
- Choose the exact bound value and where bounding logic lives (push site vs.
  `normalize()` vs. both) so live and replay paths can't diverge.
- Design the client-side cursor fix's contract (tick/sequence-based, or an
  explicit server-signaled resync) — this is the piece with real design
  judgment and cross-file blast radius (two independent consumers in two
  languages).
- Review the determinism-test extension to make sure it actually would have
  caught a live/replay divergence, not just re-assert current behavior.

**Junior (mechanical once the design is set):**
- Implement the chosen bound in `fleetcore/src/world.rs` at both push sites
  and in `normalize()`.
- Update `toys/fleetcore-live/app.js` and `web/toys/fleetcore-live/app.js`
  (keep them identical, per this repo's deploy-copy convention) to the
  senior-approved cursor design.
- Update `tools/mission-director/mission_director.py` to match.
- Write the benchmark script and capture before/after numbers.
- Update `docs/architecture/fleetcore-api.md` and
  `docs/verification/post-sprint-system-verification.md` to reflect the
  resolved state once implemented.

## Decisions requiring Command approval

1. **Sequencing: must the client-side cursor fix ship before, or atomically
   with, any server-side bounding?** This investigation's finding is "before
   or atomically with, never after" — but confirming that's acceptable
   given it touches two consumer codebases (JS + Python) instead of a purely
   server-side change is a scope decision, not something to default into
   silently.
2. **The exact retention bound (*N*).** No consumer-derived requirement sets
   this number — it's a judgment call between "small enough to matter for
   size/latency" and "large enough that no realistic single polling gap
   ever exceeds it." Needs an explicit choice, not an inferred default.
3. **Whether to also address `watch_events`** (the structurally analogous,
   currently also-unbounded field `fleetcore-control` reads the same way).
   Out of this issue's stated scope; flagged here only because the same
   root architecture applies and leaving it alone should be a deliberate
   choice, not an oversight.
4. **Whether `mission_director.py`'s persisted-cursor recovery path** (no
   client-restart-equivalent reset today) needs a real fix as part of this
   work, or is acceptable as a known, documented limitation given it's an
   internal ops tool, not a public toy.
