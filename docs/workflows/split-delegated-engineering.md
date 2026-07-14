# Split Delegated Engineering Workflow

Monad uses split delegation for changes that cross multiple architectural
layers but can be divided into independently testable ownership zones.

The pattern is:

```text
engineering order
    -> durable shared brief
    -> bounded parallel implementation hands
    -> explicit contracts and handoffs
    -> commander-owned integration
    -> combined verification
    -> one publication and completion report
```

## When to use it

Use split delegation when a change has two or more substantial, separable
tracks such as:

- canonical engine and persistence;
- ingestion or service logic;
- operator interface and documentation;
- independent fixtures or verification tooling.

Do not split work merely to create activity. Each delegated hand needs a
concrete deliverable, a non-overlapping ownership boundary, and useful work it
can finish without waiting on another hand's implementation details.

## 1. Preserve the order

Write the engineering order to a repository file before or immediately after
delegation. The durable brief is authoritative when chat context, individual
agent context, or implementation assumptions diverge.

The brief records:

- mission and doctrine;
- scope and explicit exclusions;
- acceptance fixture and tests;
- authority and safety boundaries;
- delegated ownership;
- integration responsibility;
- required completion recommendation.

For Living World Intake V0.1, the brief is
`docs/engineering-orders/living-world-intake-v0.1.md`.

## 2. Divide by architectural ownership

Prefer layer-aligned file ownership over arbitrary feature fragments. A proven
split is:

### Canon hand

Owns the canonical engine, typed commands, domain validation, replay,
persistence, snapshots, and engine-level tests. It does not implement prose
interpretation or operator UI.

### Intake hand

Owns immutable source storage, extraction, resolution, conflict detection,
adjudication records, command compilation, provenance, fixtures, and service
tests. It may generate canonical commands but never writes canonical state.

### Review hand

Owns the operator-facing review surface and operating documentation. It does
not invent validation rules or bypass the intake/canon services.

### Integration commander

Owns contract reconciliation, cross-layer behavior, combined tests, deployment
safety, commits, pull requests, and the final readiness decision. Delegation
does not delegate accountability for the integrated result.

## 3. Establish boundaries before work starts

Each assignment states:

- directories or files the hand owns;
- behavior it must deliver;
- behavior it must not add;
- checks it must run;
- assumptions or contracts it must report at handoff;
- whether it may commit or should leave changes for integration.

Avoid having two hands edit the same file. Shared contracts should be expressed
as schemas or example payloads, then reconciled by the integration commander.

## 4. Parallel hands return evidence, not assurances

A handoff includes:

- files changed;
- implemented semantics;
- exact validation performed;
- unresolved assumptions;
- blockers or limitations;
- whether changes are committed.

The commander treats a reported assumption as an integration task. For
example, if an intake compiler emits `apply-canon-proposal` while FleetCore
implements `apply-canon-change`, neither side is considered complete until the
commander reconciles and tests the wire contract.

## 5. Integrate through the narrowest stable contract

The commander reviews every returned slice and aligns:

- command and response schemas;
- identifiers and idempotency keys;
- provenance fields;
- persistence and replay semantics;
- API paths and UI payloads;
- failure and rejection behavior.

Integration should preserve the original authority boundary. A convenient
cross-layer shortcut is not acceptable if it bypasses validation, event
logging, authentication, persistence, or review.

## 6. Verify twice

Each hand runs focused checks in its own layer. After reconciliation, the
commander runs the combined suite and at least one cross-layer acceptance path.

The combined pass covers:

- formatting and static checks;
- unit and integration suites from every layer;
- exact acceptance-fixture behavior;
- idempotent retries;
- restart/replay persistence;
- rejected-command visibility;
- full provenance traversal;
- compensating-event behavior;
- repository cleanliness.

Layer-local green tests are necessary but not sufficient. Contract mismatches
often appear only after all slices return.

## 7. Publish as one coherent change

Before publication, the commander:

1. confirms unrelated user changes remain untouched;
2. reviews the complete diff and ownership boundaries;
3. records known limitations plainly;
4. commits the integrated behavior intentionally;
5. pushes the branch and opens the appropriate pull request;
6. reports the commit, PR, validation, live state, and exactly one readiness
   recommendation when the order requires one.

Stacked pull requests are acceptable when prerequisite work is already under
review, but dependencies must be explicit.

## Working rule

Parallelize construction. Centralize integration judgment.

Each hand owns its layer. The commander owns whether the assembled system is
true to the engineering order.
