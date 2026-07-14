# MONAD ENGINEERING PACKET — Issue #6 Design V0.2

Status: **APPROVED FOR REVIEWABLE IMPLEMENTATION SLICES**

Issue: [#6 — Bound unbounded FleetCore vessel event history](https://github.com/aleuf05/monad/issues/6)

Security gate: [#16 — Require authentication and authorization for FleetCore authoritative commands](https://github.com/aleuf05/monad/issues/16)

Design-review baseline: `0093de8b733ee352fb85dbc44dcdf1a64c658897`

Commissioned runtime baseline:
`8bcb14b6adfb96d13a4e6a5f22ca4175527b84e1`

## Command disposition

V0.1 is accepted in principle. This revision incorporates all Command rulings,
closes its five architectural decisions, and makes direct FleetCore command
authentication a release blocker. Implementation may proceed only through the
slices below. Destructive truncation remains forbidden until migrated consumers
pass replay, restart, lag, and rollback tests against durable history.

Doctrine: array position is not identity, and truncation is not retention.

## Problem and objective

FleetCore embeds the complete, ever-growing `vessel_events` array in current
World state, checkpoints, snapshots, and every broadcast. At design time the
array held more than 166,000 events; current state and snapshots were about 30
MB and the retained FleetCore directory was 3.3 GB.

The objective is to preserve complete authoritative history while bounding the
recent tail carried by operational state and wire snapshots. Stable sequences
replace array length as the cursor contract. FleetCore Live and Mission
Director migrate before any tail is compacted.

Canon events, provenance, command history, World Intake data, watch events, and
movement semantics are outside retention scope and must remain unchanged.

## Resolved Command decisions

### 1. Persistence failure posture

FleetCore enters a visible read-only degraded mode when authoritative
persistence fails. It remains available for trusted reads, replay, health,
metrics, and operator diagnosis, but rejects every command that could create or
mutate authoritative state.

The process exits only when it cannot establish a coherent readable snapshot or
continued reads cannot be trusted. It never acknowledges a mutation before its
authoritative event is durably appended. Recovery requires reconciliation of
the command log, current World sequence, vessel-event history boundary, and
checkpoint before mutation is re-enabled.

Required health output includes mode, transition time, cause, last durable
command sequence, last durable vessel-event sequence, and recovery action.

### 2. Legacy history migration

Legacy history receives an explicit, idempotent, observable backfill command.
Normal startup does not silently reinterpret a V1 array as V2 durable history.

The command supports dry run and commit modes and reports:

- source world, event-log, and checkpoint hashes;
- legacy and output event counts;
- first/last allocated sequence;
- duplicate/gap/conflict counts;
- output checksum and replay comparison;
- translated consumer cursors;
- completion-marker path and contents.

Commit writes through temporary files and atomic rename. Repeating a completed
backfill with identical source hashes is a no-op with the same result. A source
or output mismatch fails closed. Startup detects missing/incomplete migration
and refuses authoritative writes while retaining coherent read/diagnostic
access.

### 3. Configurable tail

The initial default is 1,024 vessel events. Tail size is configuration, not a
wire or persistence contract. Invalid, zero, or unreasonably large values fail
configuration validation rather than silently changing behavior.

Before reducing the default, evidence must cover cursor lag, consumer catch-up,
gap frequency, memory/RSS, snapshot and checkpoint bytes, history-query
latency, and network cost.

### 4. Bounded operational history API

The first history API retrieves authoritative events by stable sequence range
with optional event type and mission/world scope. It enforces deterministic
ordering, a configured maximum page size, and an opaque or explicit next cursor.

It does not support arbitrary search, semantic retrieval, unrestricted scans,
or mutation. Qdrant may index derived copies but is never a source of truth and
cannot satisfy replay or recovery.

Invalid ranges, excessive limits, unknown scopes, and expired/unavailable
cursors return explicit errors. They never silently return a plausible partial
history.

### 5. V1 compatibility window

The legacy wire contract remains available through:

1. the first commissioned release containing durable V2 history; and
2. the immediately following migration release.

Both releases emit explicit deprecation warnings and usage telemetry for V1
snapshot/array-length behavior. Removal requires evidence that FleetCore Live
and Mission Director use stable cursors and that no active consumer depends on
array length. Removal is a separately approved release action.

## Command security release gate

Issue #16 is a commissioning blocker for the history release. HTTP and
WebSocket mutation paths must share one policy that:

- authenticates the caller;
- authorizes the authenticated identity for the exact command;
- defaults to denying authoritative mutation;
- records accepted and rejected attempts without storing credentials;
- preserves schema, domain, conflict, canon, and idempotency validation;
- provides a local maintenance path only when narrowly scoped, explicitly
  enabled, non-remote, and auditable.

Anonymous callers, invalid credentials, and authenticated callers without the
required privilege must receive rejection without command event, state change,
checkpoint, or canon mutation. Read-only endpoints remain separately governed
and available during coherent degraded operation.

No history release may be commissioned until negative authorization tests and
operational evidence for Issue #16 pass.

## V2 architecture

### Stable identity and bounded tail

Every `VesselEvent` receives a strictly increasing sequence. Tick and FleetCore
command sequence are insufficient alone because a command can emit multiple
vessel events. World stores:

- `vessel_event_next_sequence`;
- `vessel_event_tail_start_sequence`;
- at most the configured recent tail;
- a current per-vessel route/event baseline for correct consumer bootstrap.

Eviction is deterministic and occurs only after durable history, replay, and
consumer contracts are present and verified.

### Authoritative append-only history

The versioned durable command envelope records the ordered vessel events
produced by that command, or an equivalently atomic append-only vessel-event
record if implementation evidence demonstrates a safer transaction boundary.
The chosen format must make command acceptance and derived history
reconstructable without a best-effort dual write.

Replay regenerates derived vessel events and rejects mismatches against stored
V2 output. Legacy data becomes authoritative V2 history only through the
approved backfill command and completion marker.

### Versioned contracts

- Persisted World: `monad.fleetcore.world.v2`
- Snapshot: `monad.worldSnapshot.v2`
- Operational history API: explicitly versioned path and response
- V1 snapshot: compatibility-only, deprecated, metered

V2 `vessel_events` is documented as a recent tail. Responses include tail
start, next sequence, configured tail limit, and gap/bootstrap metadata.

### Consumer cursor behavior

Mission Director durably stores its highest processed stable sequence and uses
bounded history catch-up after a gap. Legacy count cursors are translated only
during explicit backfill while the full V1 array remains present.

Both FleetCore Live copies migrate together. They use stable sequences for
incremental events and current per-vessel baseline state for first load and gap
recovery. Equal-length tail rollover cannot suppress new events.

## Implementation slices

Each slice is independently reviewable and must leave the prior commissioned
baseline recoverable.

| Slice | Tracking issue |
|---|---|
| A — Durable history and sequence allocation | [#17](https://github.com/aleuf05/monad/issues/17) |
| B — Bounded history-read API | [#18](https://github.com/aleuf05/monad/issues/18) |
| C — Consumer cursor migration | [#19](https://github.com/aleuf05/monad/issues/19) |
| D — Explicit legacy backfill | [#20](https://github.com/aleuf05/monad/issues/20) |
| E — Compatibility and deprecation | [#21](https://github.com/aleuf05/monad/issues/21) |
| F — Safe tail compaction | [#22](https://github.com/aleuf05/monad/issues/22) |
| G — Command authentication hardening | [#16](https://github.com/aleuf05/monad/issues/16) |
| H — Acceptance and commissioning | [#23](https://github.com/aleuf05/monad/issues/23) |

### Slice A — Durable history and sequence allocation

Deliver stable sequences, versioned durable output records, replay comparison,
sequence restoration after restart, and scratch-only fault tests. Retain the
complete V1 array; do not compact.

Gate: unique ordering, multi-event commands, append durability, restart, and
replay tests pass.

### Slice B — Bounded history-read API

Deliver sequence-range reads, optional event-type and mission/world filters,
page limits, next cursor, explicit errors, and read-path performance evidence.
No semantic or unrestricted search.

Gate: ordered gap-free pagination, scope isolation, maximum limits, corrupt-tail
handling, and read-only behavior pass.

### Slice C — Consumer cursor migration

Migrate Mission Director, FleetCore Live source, and its deployed copy. Add
baseline bootstrap, catch-up, persistent cursor, duplicate protection, and lag
telemetry. Still do not compact.

Gate: replay, restart, disconnect beyond 1,024 events, equal-length rollover,
multi-event batch, browser bootstrap, and source/deployed parity pass.

### Slice D — Explicit legacy backfill

Deliver dry-run/commit migration, hashes, counts, checksums, cursor translation,
atomic output, marker, idempotent retry, and incomplete-migration write refusal.

Gate: production-shaped disposable copies migrate twice identically; injected
failure before every boundary leaves V1 restorable and V2 unmarked.

### Slice E — Compatibility and deprecation

Ship V1 and V2 together, warning headers/messages, usage telemetry, operator
dashboard/readout, and documented removal criteria. V1 remains supported for
the two-release window.

Gate: telemetry identifies protocol and consumer without credentials; no known
consumer uses array length before removal approval.

### Slice F — Safe tail compaction

Enable configurable bounded World/checkpoint/snapshot tails with default 1,024.
Full durable history and query results remain unchanged. Canon/provenance are
explicitly excluded.

Gate: all consumer migration evidence passes; state and wire size remain
bounded; lag/catch-up, replay, restart, rollback, and canon-isolation tests pass.

### Slice G — Command authentication hardening

Complete Issue #16 with shared HTTP/WebSocket authentication and authorization,
default-deny mutation, audited local maintenance access, negative tests, key or
credential operating notes, and degraded-mode compatibility.

This slice may proceed in parallel with A–E but must merge before the
commissioning package and before any live V2 mutation path is accepted.

### Slice H — Acceptance and commissioning package

Assemble migration dry run, immutable backups, rollback, tests, benchmark
matrix, authorization evidence, compatibility telemetry, service health, and a
marker-gated privileged handoff. No production migration occurs outside this
package.

Gate: Command reviews the evidence plan and exact rollback before execution.

## Cross-slice acceptance requirements

1. Anonymous and insufficiently privileged mutation is rejected without state
   transition.
2. Persistence failure enters visible read-only degraded mode and rejects every
   mutation.
3. Startup with incomplete migration refuses authoritative writes.
4. Stable sequences remain unique and monotonic across commands and restarts.
5. Consumers deliver each event exactly once through rollover and catch-up.
6. Seed and checkpoint replay reproduce canon, sequence boundary, tail, and
   durable derived outputs.
7. Backfill dry run is non-mutating; committed retry is idempotent.
8. History pagination is bounded, ordered, scoped, and gap-free.
9. Snapshot/checkpoint size remains bounded beyond many tail windows.
10. Canon events, permissions, provenance, and World Intake records are never
    compacted by vessel-event retention.
11. V1 warnings and usage telemetry remain available for two releases.
12. Rollback restores the named V1 baseline without manufacturing history from
    the bounded V2 tail.

## Evidence and rollback

All destructive and fault testing uses generated state or disposable copies.
Benchmark 0, 1,000, 10,000, and 100,000 events and capture state/checkpoint/wire
bytes, save and query latency, tick lock duration, RSS, network bytes, cursor
lag, catch-up time, duplicates, skips, and authorization outcomes.

Before migration, preserve and hash the V1 world, command log, latest
checkpoint, binaries, configuration, consumer state, and service units outside
normal pruning. The backfill completion marker records source/output hashes,
counts, cursor bounds, accepted revision, and replay result.

Rollback stops mutation, restores the named V1 set and consumer cursors, starts
the V1 binary under its known configuration, verifies replay and service reads,
and records the rollback decision. Never convert a bounded V2 tail into a
purported complete V1 history.

## Delegation boundaries

Senior-owned:

- atomic persistence/degraded-mode contract;
- authentication and authorization policy;
- V2 schemas and replay invariants;
- backfill, startup reconciliation, and rollback;
- final compaction and commissioning gates.

Junior-safe after contracts are fixed:

- bounded API filters and pagination tests;
- browser and Mission Director cursor adapters;
- telemetry, fixture generation, benchmarks, and documentation;
- disposable migration/failure test matrices;
- source/deployed-copy parity automation.

No delegate may enable production compaction, weaken command authorization, or
reinterpret incomplete migration without explicit Command approval.

## Release gates

Implementation completion is not commissioning authorization. Commissioning
requires all of the following:

- Issue #16 closed with negative-test evidence;
- explicit backfill dry run accepted;
- consumers migrated and observed within the 1,024-event lag window and beyond;
- replay, restart, rollback, and canon-isolation evidence green;
- bounded API and deprecation telemetry green;
- privileged package and recovery plan approved by Command.

Until then, the commissioned V1 baseline remains authoritative and destructive
truncation remains prohibited.
