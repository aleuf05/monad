# MONAD ENGINEERING PACKET — Issue #6 Design V0.1

Status: **DESIGN READY — IMPLEMENTATION REQUIRES COMMAND APPROVAL**

> Command disposition — accepted in principle at review baseline
> `0093de8b733ee352fb85dbc44dcdf1a64c658897`. The five open decisions were
> resolved and the direct `/command` authority defect was elevated to a release
> blocker in [`issue-6-design-v0.2.md`](issue-6-design-v0.2.md). V0.1 remains
> preserved as the design-review record.

Issue: [#6 — Bound unbounded FleetCore vessel event history](https://github.com/aleuf05/monad/issues/6)

Baseline: commissioned revision
`8bcb14b6adfb96d13a4e6a5f22ca4175527b84e1`

## Problem statement

`World.vessel_events` is an ever-growing derived route/motion history. The
complete vector is serialized into `world.json`, every retained checkpoint,
the disk snapshot, every HTTP snapshot, and every WebSocket broadcast.

At investigation time it held 166,399 events. `world.json` was 30,105,081
bytes, the disk snapshot 30,089,023 bytes, the command log 9,209,797 bytes, and
`data/fleetcore` 3.3 GB. This is not a current correctness failure, but every
tick compounds storage, serialization, lock duration, memory, and network cost.

A simple vector cap is unsafe. FleetCore Live and Mission Director use array
length as an absolute cursor. Once a fixed tail reaches capacity, equal-length
replacement makes FleetCore Live ignore all later events; Mission Director can
silently skip events after truncation.

## Operational value

- Bound current-world, checkpoint, snapshot, and broadcast size.
- Keep tick cost stable as historical event count grows.
- Preserve complete inspectable history and deterministic replay.
- Make consumer gaps explicit instead of silently losing mission events.
- Leave canon state, provenance, and narrative adjudication untouched.

## Scope

Included:

- Stable identity for each vessel event.
- Complete durable vessel-event history.
- A bounded recent tail in current state and snapshots.
- Versioned persistence and wire contracts.
- Migration of existing worlds, checkpoints, and consumer cursors.
- Replay, crash consistency, history reads, rollback, and measurements.
- FleetCore Live source/deployed copy and Mission Director migration.

Excluded:

- Truncating command history, canon events, provenance, or watch events.
- Changing vessel movement or route semantics.
- Living World Intake behavior or automatic canon approval.
- General event sourcing, database replacement, or UI redesign.
- Fixing `fwupd`, captain-memory reflection, or unrelated host concerns.

## Affected components and contracts

| Area | Current dependency | Required change |
|---|---|---|
| `fleetcore/src/world.rs` | Owns the unbounded vector and emitters | Stable sequence, deterministic bounded tail |
| `fleetcore/src/event.rs` | Durable command envelope | Versioned derived-event envelope or equivalent atomic archive |
| `fleetcore/src/persistence.rs` | Serializes full World/checkpoints | Migration, archive/history read, reconciliation |
| `fleetcore/src/snapshot.rs` | Clones full vector | V2 tail and cursor metadata |
| `fleetcore/src/bin/serve.rs` | Rewrites/broadcasts every tick | Versioned delivery, gap handling, fail-closed persistence |
| `fleetcore/src/main.rs` | Full snapshot replay equality | Separate canonical-state and history-boundary verification |
| FleetCore Live, both copies | Array-length cursor | Stable sequence plus bootstrap baseline |
| Mission Director | Persisted array-length cursor | Durable sequence cursor and gap recovery |
| `fleetcore-api.md` | Promises never-truncated arrays | V2 contract and V1 retirement notes |

No other semantic vessel-event consumer was found. Other snapshot clients pay
the payload cost but do not read the field.

## Smallest coherent architecture

### 1. Stable event cursor

Assign every `VesselEvent` a strictly increasing `sequence`. Tick is not a safe
cursor: multiple vessels may emit in one tick, and operator commands may emit
without advancing time. Persist `vessel_event_next_sequence` and
`vessel_event_tail_start_sequence` in World.

### 2. Complete durable history

Extend the versioned durable command `Event` envelope with the ordered vessel
events produced by that command, defaulting absent for legacy records. This
keeps command and derived output in one append-only JSONL record instead of
introducing a dual-write database. Replay regenerates vessel events and rejects
a mismatch with recorded derived outputs. Legacy envelopes continue through
deterministic regeneration.

Command approval must decide whether the existing legacy history is durable
enough through deterministic command replay or must be explicitly backfilled
into V2 envelopes/a separate immutable archive.

### 3. Bounded state and snapshot tail

Retain only the newest configured vessel-event window in World, checkpoints,
and snapshots. Start measurement with 2,048 events; the final limit is a
Command decision based on benchmarks. Tail eviction happens deterministically
inside command application after sequence assignment.

`canon_events`, FleetCore command events, provenance, and adjudication data are
never subject to this retention policy.

### 4. Versioned contracts

Bump persisted world schema to `monad.fleetcore.world.v2` and snapshot schema to
`monad.worldSnapshot.v2`. Preserve the `vessel_events` field and event shapes,
but define it as a tail and add:

- `vessel_event_tail_start_sequence`
- `vessel_event_next_sequence`
- a current per-vessel route/event baseline sufficient for browser bootstrap

Provide a bounded read-only history query by `after_sequence` unless Command
explicitly defers it. A stale cursor must receive complete missed events or an
explicit cursor-expired response; silent loss is forbidden.

### 5. Consumer migration before truncation

Mission Director persists the highest processed vessel-event sequence and
processes only higher sequences. Existing `processed_vessel_event_count` values
must be translated while the complete V1 array still exists; ambiguous states
fail with an actionable error.

Both FleetCore Live copies migrate together. They consume sequences and use the
current route baseline to render correct status when opened mid-route or after
a gap. No tail is capped until these consumers are deployed and observed.

## Canon, replay, persistence, and memory implications

Canon collections and provenance remain separate and unchanged. Canon commands
continue through existing validation, event logging, checkpoints, and replay.
Tests must prove vessel retention cannot select or delete canon records.

Seed replay and checkpoint-plus-tail replay must reproduce canonical state,
vessel-event sequence metadata, bounded tail, and derived outputs. Full history
is verified independently from the bounded current-state snapshot.

The server currently mutates memory, logs append/save failures, and continues.
That behavior cannot support a durable-history guarantee. V2 must not
acknowledge a command whose durable event append failed. Startup reconciles
`world.json.event_sequence` with the command log and replays a committed log
tail. Command must choose whether persistence failure exits the process or
enters a visible read-only degraded mode.

Bounding the tail reduces long-lived heap and temporary serialization memory.
No captain-memory database or World Intake SQLite change is involved.

## Failure modes

- Length-based consumers silently stop or skip after rollover.
- Duplicate, missing, or non-monotonic vessel-event sequences.
- Off-by-one eviction at the retention boundary.
- Multiple events from one command ordered incorrectly.
- Legacy cursor translated after its source history was truncated.
- Browser bootstrap lacks enough route context.
- Checkpoint tail and archive disagree after replay.
- Command log is ahead of `world.json` after a crash.
- Memory/world is ahead after an event-log append failure.
- Final JSONL record is truncated or corrupt.
- Migration stops before its completion marker.
- Stored derived outputs differ from deterministic regeneration.
- Sequence overflow is not rejected safely.
- Vessel retention touches canon/provenance data.

## Pass/fail acceptance tests

1. Multiple vessel events in one tick receive unique, strictly ordered cursors.
2. Several full tail rollovers deliver every new event exactly once.
3. A disconnected consumer either recovers every missed event or receives an
   explicit cursor-expired error; silent loss fails.
4. Mission Director restart resumes at its durable cursor without duplicate or
   skipped mission advancement.
5. Existing same-poll waypoint/completion ordering remains correct.
6. FleetCore Live opened mid-route renders correct status and leg count.
7. Browser reconnect after rollover shows no stale replacement/completion.
8. A real-shaped V1 mission cursor migrates before truncation or startup fails
   explicitly when translation is ambiguous.
9. Seed and checkpoint replay reproduce canon plus the exact history boundary.
10. Restart preserves next sequence and history query results.
11. Snapshot event count/bytes remain bounded beyond several window lengths.
12. Checkpoint size remains approximately constant as history grows.
13. History queries across windows are ordered, gap-free, and nonduplicated.
14. Legacy worlds load safely; inconsistent V2 metadata fails loudly.
15. Source and deployed FleetCore Live copies pass the same tests.
16. Event-log append failure is never acknowledged as accepted canon or world
    state, and recovery produces one consistent state.
17. Vessel-event retention leaves all canon records and provenance unchanged.
18. Interrupted migration leaves the V1 baseline restorable and no completed
    V2 marker.

These tests are the coding gate and must exist before tail truncation is
enabled.

## Evidence plan

Use generated scratch state and copies of production-shaped data, never live
production files. Capture 0, 1,000, 10,000, and 100,000 vessel-event cases.

Record before/after:

- world, checkpoint, snapshot, and WebSocket message bytes;
- world save, checkpoint write, snapshot construction, serialization, replay,
  archive append, and history-query latency;
- tick-loop lock duration and late/missed ticks;
- peak RSS and network bytes per client/minute;
- generated, delivered, duplicated, skipped, and cursor-expired counts;
- migration source hash, old/new counts, cursor range, replay result, and output
  hashes.

Pass requires bounded state/wire size, zero silent skips or duplicates,
deterministic replay, intact canon/provenance, and materially lower per-tick
serialization/network cost. Numeric performance thresholds are set from the
captured baseline before implementation approval, not guessed here.

## Implementation phases

1. **Contract and tests:** approve V2 schemas, cursor semantics, persistence
   failure posture, acceptance fixtures, and benchmark harness.
2. **Identity and archive:** add stable event identity and complete durable
   output records while retaining the full V1 array.
3. **Consumers:** migrate Mission Director and both FleetCore Live copies;
   translate legacy cursors and add gap/bootstrap behavior.
4. **Bound the wire:** enable the V2 snapshot tail after consumer compatibility
   evidence; retain legacy telemetry during transition.
5. **Bound persistence:** migrate World/checkpoints, verify archive/replay, write
   a completion marker, and only then prune ordinary oversized checkpoints.
6. **Soak and retire V1:** observe correctness/size/latency, then remove the
   never-truncated length contract under separate approval.

No standalone vector cap may merge ahead of phases 1–3.

## Senior and junior task factoring

Senior-owned:

- V2 persistence/wire contract and final cursor semantics.
- Crash consistency, acknowledgment, and startup reconciliation.
- Migration/rollback tooling and canon-isolation review.
- Replay/history validation and final deployment gate.

Junior-safe after contracts are fixed:

- Consumer cursor conversions and parity checks.
- Retention, gap, bootstrap, and deployed-copy tests.
- Scratch fixture generation and benchmark collection.
- API/operating-note updates.
- Migration testing against disposable production-shaped copies.

## Migration and rollback

Migration is explicit and marker-based:

1. Stop the V1 writer and copy the V1 world, command log, current checkpoint,
   binary, and configuration outside normal pruning.
2. Hash the source set.
3. Assign sequences in existing vector order and translate legacy consumer
   cursors while full history is present.
4. Verify seed/command replay reproduces the ordered legacy history.
5. Write V2 world/checkpoint/archive through temporary-file rename.
6. Verify counts, cursor bounds, replay, consumers, and canon equality.
7. Write a migration marker containing source hashes, counts, first/last
   sequence, replay result, and accepted revision.
8. Only then enable bounded retention and later prune normal checkpoints.

Rollback stops the V2 writer and restores the named V1 artifact set. Never
construct a supposed complete V1 history from the bounded V2 tail. Confirm old
binaries tolerate unknown V2 command-envelope fields before relying on the
unchanged command log; otherwise restore its V1 copy too.

## Unresolved Command decisions

1. Persistence failure posture: process exit or visible read-only degraded mode.
2. Legacy history: deterministic replay suffices, or explicit event backfill is
   required.
3. Tail size: approve 2,048 provisionally or select from measured results.
4. History endpoint: required in this issue or deferred until a demonstrated
   operator need.
5. V1 compatibility window and removal criteria.
6. Whether the adjacent same-tick checkpoint filename collision receives a
   separate issue; it must not silently expand this implementation.
7. Direct FleetCore `/command` authentication/network boundary, identified by
   commissioning closeout; this is not solved by Issue #6.

Implementation remains blocked until Command resolves decisions 1–5 and
approves the phased plan.
