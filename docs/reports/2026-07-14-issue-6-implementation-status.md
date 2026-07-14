# Issue #6 Integrated Change — Status Report

Date: 2026-07-14

Status: **IMPLEMENTATION ACTIVE — NOT RELEASE READY**

Design: [`issue-6-design-v0.2.md`](../engineering-orders/issue-6-design-v0.2.md)

Parent: [GitHub Issue #6](https://github.com/aleuf05/monad/issues/6)

Security gate: [GitHub Issue #16](https://github.com/aleuf05/monad/issues/16)

## Command decisions in force

- One integrated change with reviewable slices.
- Stable monotonic vessel-event sequence is the durable cursor. Tick is not
  unique: production verification found 58,511 duplicate-tick groups and as
  many as four events at one tick.
- Initial tail default is configurable `N=2,000`.
- `watch_events`, canon events, provenance, command history, and World Intake
  data are outside compaction scope.
- No destructive truncation before consumer replay, restart, lag, migration,
  and rollback evidence passes.
- Direct FleetCore command authentication is a release blocker.

## Completed isolated work

### Durable history and bounded read API

The first integrated A+B build exists only in the isolated clone
`/home/cgl/dev/monad-history-integration` at commit
`196137a5e07c302f7c8dc6adf9627013dbdbb310`.

Implemented and tested:

- stable vessel-event sequences;
- V2 durable command envelopes with derived vessel events;
- V1 deserialization compatibility without silent backfill;
- deterministic V2 replay checks;
- read-only degraded mode and `/health`;
- GET-only bounded history API with stable sequence ranges, explicit scope and
  cursor errors, and page limits;
- reserved configurable tail default of 2,000, with compaction disabled;
- full V1 `vessel_events` retained and `watch_events` untouched.

Adversarial review correctly rejected this first build. Corrective code now
passes locally for corrupt/missing World handling, full-log validation,
migration-marker write gating, committed append semantics, serialized history
reads, bounded scan work, future-cursor rejection, log-derived health, and
fault/replay/DoS tests. That amendment is intentionally uncommitted pending the
idempotency decision below.

### Command authentication hardening

The amended Slice G exists only in `/home/cgl/dev/monad-slice-g` at commit
`41e93cdac0da85796cbbf7fc88c78ecfb7390994`.

It provides:

- separate authentication and authorization;
- default-deny HTTP and WebSocket mutation;
- fixed-length hashed token material and constant-time comparison;
- startup rejection of identical commander/observer credentials;
- same-origin, short-lived `HttpOnly`, `Secure`, `SameSite=Strict` browser
  command sessions with exact Origin validation;
- Bearer authentication for non-browser clients;
- no query-string or browser-storage secrets;
- real router/WebSocket and negative zero-mutation tests.

All 16 FleetCore tests, formatting, serve-target Clippy, and diff checks pass in
that clone. It has not been deployed and contains no production credentials.

## Current decision required

True retry idempotency after a lost response is not defined for generic
FleetCore commands. After append and `sync_data` succeed, the command is
authoritative even if saving derived `world.json` fails. The server can return
`committed: true`, the durable event sequence, and `degraded: true`, but a
caller that loses that response cannot distinguish retry from an intentional
repeat such as another `Step` command.

Recommended platform decision: add a caller-supplied idempotency key to both
HTTP and WebSocket command envelopes, persist it in the authoritative Event,
and return the original committed result for duplicate keys. Keys are scoped to
the authenticated principal; reusing one with different command bytes fails
closed. This is required before claiming retry idempotency.

## Residual security and operational work

- Integrate amended authentication after durable-history fixes.
- Add session quota, rate limit, logout/revocation, and protected credential
  loading in the deployment slice.
- Prove authentication and degraded-mode interaction end to end.
- Implement explicit legacy backfill with dry run, hashes, counts, checksums,
  marker, and idempotent retry.
- Migrate Mission Director and both FleetCore Live copies before compaction.
- Preserve the two-release V1 compatibility and telemetry window.
- Assemble scratch-only migration, replay, restart, rollback, authorization,
  benchmark, and commissioning evidence.

## Workspace and production posture

All Issue #6 implementation work described above is isolated and uncommissioned.
No production services, data, credentials, migration markers, or configuration
were changed. No event tail was compacted.

The earlier shared-checkout collision has cleared and the primary repository is
clean. Integration remains in isolated clones until review gates pass; no
isolated implementation commit has been merged into the commissioned branch.

The commissioned V1 baseline remains authoritative.
