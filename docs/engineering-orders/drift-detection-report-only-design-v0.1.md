# DRIFT-01 Design V0.1 — Report-Only Drift Detection

Status: Design Required / report-only

Queue item: [DRIFT-01](./queue.md#drift-01--drift-detection-report-only-mode-design-required-not-verification)

Date: 2026-07-15

Prepared by: Claude

## Problem statement

The repo already maintains at least one concrete source/deploy mirror pair:
`toys/` is the source tree, and `web/toys/` is the deployed mirror tree.
This session already performed a manual drift sweep on that pair (`TOY-01`),
which means the drift class is real, checkable, and already operationally
relevant.

The gap is not detection in the abstract. The gap is a repeatable, report-only
detector that can tell us when the mirror pair has diverged without changing
anything.

## Drift definition for this order

For DRIFT-01, “drift” means source/deploy divergence between the checked-in
`toys/` tree and the mirrored `web/toys/` tree.

That is the only drift class this order covers.

Out of scope for this order:

- config drift;
- infra drift;
- host/package drift;
- remediation or auto-fix logic;
- any write path that changes source, deploy, or runtime state.

Those are separate future decisions. This order is intentionally narrow.

## Operational value

This detector gives the team a repeatable answer to a simple question:
“Are the source instrument and its deployed mirror still equivalent?”

That matters because the mirror pair is user-visible and already has a history
of manual sync work. Report-only drift detection reduces the chance that a
stale deploy goes unnoticed, while staying inside the current no-remediation
boundary.

## Included scope

The first implementation slice should inspect:

- file presence/absence;
- content hashes for matched files;
- stable path mapping between `toys/` and `web/toys/`;
- per-file report output;
- aggregate summary counts;
- a machine-readable exit/status signal for “clean” vs “drift found”.

The detector may optionally include metadata such as file size and last
modified time in the report, but the source of truth for mismatch detection
should be content, not timestamps.

## Excluded scope

This order does not include:

- any write or repair operation;
- deleting or copying files;
- auto-reconciliation;
- deployment orchestration;
- host inspection;
- package installation;
- generic config/infra sweeps.

If a future order wants those, it must ask for them explicitly.

## Affected components and contracts

Likely touch points for a future implementation:

- `toys/` source tree;
- `web/toys/` deployed mirror tree;
- a small report-only drift utility or script;
- queue/report documentation;
- a fixture set of known-good states for testing.

This design does not change FleetCore canon, persistence, or command handling.
It also does not require new runtime contracts. The detector is read-only.

## Smallest coherent architecture

The minimal report-only design has four pieces:

1. Inventory

   Build a stable list of source paths and their mirror targets.

2. Comparator

   Compare the paired trees deterministically using content hashes and
   presence/absence checks.

3. Reporter

   Emit a concise summary plus per-file mismatches, with enough detail for a
   human to repair the drift manually.

4. Harness

   Run the detector against known-good and known-bad fixtures so false
   positives can be measured before any future remediation proposal exists.

## False-positive measurement plan

The detector must be evaluated against a fixed set of known-good states.
Those states should be exact mirror pairs where `toys/` and `web/toys/` are
intentionally equivalent.

Measurement method:

- choose at least 20 known-good states;
- run the report-only detector against each state;
- count any drift flag on a known-good pair as a false positive;
- compute false-positive rate as `false_positives / known_good_states`.

Pass condition for this order:

- zero false positives across the known-good set.

Recommended sanity check:

- include at least one intentionally mismatched pair in the harness so the
  detector is also proven capable of finding an actual drift condition.

That sanity check is for detection confidence, not false-positive scoring.

## Failure modes

The main failure modes are all report-safety failures, not state-mutation
failures:

- false positive: the detector flags drift when the mirror is clean;
- false negative: the detector misses a real mismatch;
- unstable comparator: the report changes on identical inputs;
- path-mapping bug: a valid mirror pair is treated as unrelated files;
- scope creep: config or infra drift gets folded into the same order
  without a new decision.

Only the first implementation slice should be judged against the repo’s current
`TOY-01` mirror pair.

## Acceptance tests

This order is satisfied when all of the following hold:

- the report names drift explicitly as `toys/` vs `web/toys/` divergence;
- the detector is report-only and contains no remediation logic;
- the report can identify at least one injected mismatch in a known-bad
  fixture;
- the report produces zero false positives across the known-good fixture set;
- the report distinguishes file content mismatches from timestamp noise;
- the report can be rerun without changing any repo state.

## Implementation phases

Phase 1 — define the mirror pair and report format

- fix the scope to `toys/` and `web/toys/`;
- define the path mapping and report schema;
- define the known-good fixture set.

Phase 2 — build the report-only detector

- compare file inventory and content hashes;
- emit a deterministic drift report;
- preserve read-only behavior end to end.

Phase 3 — measure false positives

- run the detector over the known-good set;
- record any false positives;
- tune comparison rules only if the tuning remains report-only.

Phase 4 — future decision gate

- if someone later wants auto-remediation, that is a separate order and a
  separate approval.

## Senior and junior task factoring

Senior work:

- define drift scope;
- choose the comparator semantics;
- decide what constitutes a false positive;
- keep the detector report-only;
- reject any hidden repair path.

Junior work:

- assemble the paired file inventory;
- implement the report formatter;
- prepare the known-good and known-bad fixture cases;
- run and record the measurement harness.

## Rollback strategy

Because this order is report-only, rollback is simple:

- remove the detector from any scheduled or ad hoc invocation;
- delete the report artifact if it is no longer wanted;
- leave source and deployed trees unchanged.

No data migration or reverse write path is required.

## Unresolved command decisions

Still open by design:

- whether config drift should become a separate detector later;
- whether infra drift should be added later;
- whether the report should live in CI, a local tool, or both;
- whether the path mapping should remain limited to the toy mirror pair or be
  generalized after a separate decision.

Those are future scope decisions, not part of DRIFT-01.

## Bottom line

DRIFT-01 should start as a narrow, report-only comparator for the existing
`toys/` ↔ `web/toys/` mirror pair. That gives the repo a concrete drift signal,
keeps the authority boundary intact, and makes false positives measurable before
any remediation proposal is even entertained.
