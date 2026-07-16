# Mission Coordinator Lifecycle V0.1

Status: GLUE-04 design. The coordinator sequences adapters and appends Mission
Record events. It is not a command authority, scheduler daemon, model provider,
review authority, or source of world truth.

## Operations

| Operation | Effect |
|---|---|
| `create(envelope)` | Validate IDs/schema, append `mission-created`; no component runs. |
| `inspect(mission_id)` | Fold the append-only record and return current state, artifacts, evidence, blocker, and next permitted actions. |
| `execute(mission_id)` | Lease one runnable step, invoke its adapter, append receipts/results, release lease. |
| `pause(mission_id, reason)` | Stop leasing new steps; an in-flight adapter may finish and record its receipt. |
| `cancel(mission_id, reason)` | Append terminal cancellation; request adapter cancellation where supported, but preserve late receipts. |
| `resume(mission_id)` | From `paused` or retryable `blocked`, revalidate dependencies and lease the next incomplete step. |
| `review(mission_id, review_artifact)` | Record a human decision; never synthesize acceptance from elapsed time or component success. |
| `complete(mission_id)` | Allowed only when required steps and reviews have terminal successful receipts. |

## Coordinator state machine

```text
created --execute--> running --review needed--> review-required
   |                    |   ^                         |
   |                    |   | resume                  | review accepted
   |                    v   |                         v
   +--cancel------> cancelled  paused <---pause--- running
                        running --missing input--> blocked --resume--> running
                        running --retry exhausted--> failed
                        running --all gates pass--> completed
                        review-required --reject--> rejected
                        any nonterminal --cancel--> cancelled
```

Every arrow appends an event. Current state is a fold, never an updated row
standing in for history. `completed`, `rejected`, `cancelled`, and `failed` are
terminal. A correction or rerun creates a child mission.

## Step lifecycle and leasing

Each plan step is `pending`, `leased`, `succeeded`, `review-required`,
`rejected`, `retryable-failure`, `failed`, `cancelled`, or `skipped`. A lease
contains correlation ID, adapter name, attempt number, acquisition time, and a
short expiry. Expiry makes the step inspectable as `retryable-failure`; it does
not prove the adapter did nothing. Before retry, the coordinator queries the
adapter/native receipt using the same idempotency key.

Only one lease per step is active. Independent read-only steps may run in
parallel later, but V0.1 executes sequentially for inspectability.

## Authority boundary

The coordinator may call read adapters and generation/validation adapters. It
may submit a proposal to a review inbox. It cannot:

- call FleetCore `POST /command` directly;
- approve its own artifact;
- convert interpretation, hypothesis, generated candidate, or lore into
  `verified-state`;
- treat adapter success as human acceptance;
- rewrite or delete Mission Record events;
- infer missing human input.

Any command proposal is an `ArtifactResult` with `requires_review: true`.
After review, the existing bounded component (World Intake, Living Fleet, or a
specific command adapter) submits it and records FleetCore's separate receipt.

## Kraken inquiry sequence

```text
Lieutenant -> Coordinator: create inquiry "What does K-1 evidence justify?"
Coordinator -> Mission Record: mission-created
Coordinator -> FleetCoreReader: observe K-1 snapshot/events (read only)
FleetCoreReader -> Mission Record: verified-state EvidenceRefs
Coordinator -> CognitionAdapter: run stub/live graph with evidence refs
CognitionAdapter -> Mission Record: competing hypothesis artifacts + verifier candidate
Coordinator -> Review Inbox: recommendation review-required
Review Inbox -> Lieutenant: evidence, hypotheses, counterevidence, recommendation
Lieutenant -> Review Inbox: accept/edit/reject
Review Inbox -> Mission Record: human review artifact
Coordinator -> Mission Record: mission-completed (inquiry result only)
Coordinator -> Agent Ops Projection: visible mission/result/evidence links
```

No FleetCore mutation is required for this pilot. If the human later requests
an operational action, that is a child `operation` mission with its own review
and native command receipt.

## Timeouts and recovery

- Read adapter timeout: retry twice with the same cursor/idempotency key, then
  `blocked` if the source is unavailable.
- Model/generator timeout: retain partial receipts, retry only by explicit plan
  policy, then use an honestly labeled stub only when the mission permits it.
- Review timeout: remain `review-required`; never auto-accept or auto-reject.
- Process crash: fold Mission Record, inspect expired lease/native receipt, and
  resume at the first incomplete step.
- Duplicate output: identical artifact ID and content is idempotent; unequal
  content under one ID is a hard failure.
- Late result after cancel: append as `late-receipt`, do not reopen the mission.
- FleetCore cursor rotation: use stable event sequence, never retained-array
  length.
- Projection failure: mission may complete; projection step remains retryable
  and visible as degraded until the Lieutenant can see it.

## Bounded implementation packet outline

1. Add `tools/mission-bus/` standard-library Python package.
2. Implement JSONL Mission Record writer/folder per
   `mission-record-v0.1.md` with file locking and idempotency checks.
3. Implement `create`, `inspect`, `execute`, `pause`, `cancel`, and `resume` CLI
   commands; no daemon.
4. Implement only two adapters for the pilot: read-only FleetCore evidence and
   deterministic stub cognition.
5. Emit a static Agent Ops projection JSON; GLUE-06 defines its registry path.
6. Do not implement FleetCore writes or generalized review until GLUE-05.

Acceptance tests must prove lifecycle transitions, crash/expired-lease resume,
duplicate idempotency, review-required never auto-completes, cancellation with
late receipt, FleetCore read-only behavior, and an end-to-end Kraken inquiry
visible through the projection. Rollback removes the new tool/projection while
leaving append-only pilot records archived as evidence.
