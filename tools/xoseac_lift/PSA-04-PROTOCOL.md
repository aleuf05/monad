# PSA-04 — Frozen self-application comparison protocol

Status: **PRE-REGISTERED / FROZEN BEFORE TRIALS**

This protocol evaluates the already implemented PSA-03A apparatus. PSA-03A is
frozen for this experiment. No implementation, metric, task, budget, stopping
rule, or condition definition may be changed after the first trial.

## 1. Operational target and deficiency

The operative system is the existing `tools.xoseac_lift.lift` module. Its
established self-application path is:

```text
operative_instance()
  -> is_self_representation(...)
  -> apply_self_application(...)
  -> execute_using_self_representation(...)
```

The deliberately measurable deficiency is that an unedited operative
self-representation does not cause a later execution to emit the runtime
event `self-audit-marker altered subsequent execution`. The event is emitted
only when the evaluated self-representation contains the exact S state
`self-audit-marker`. This is a small behavioral deficiency, not a claim about
the usefulness or quality of the apparatus.

The intervention target is therefore an S edit adding exactly one state:
`self-audit-marker`. All conditions receive the same target description and
the same execution API.

## 2. External score Q

For each held-out execution case, the evaluator supplies a base valid XOSEAC
instance and one legal ordinary mutation. The candidate's resulting
self-representation is passed to the frozen
`execute_using_self_representation` function.

The case score is fixed before trials:

```text
q_i = 1 iff all of the following hold:
  1. the ordinary execution is accepted;
  2. the requested ordinary mutation appears in the successor;
  3. the before and successor provenance digests are present and valid;
  4. the final provenance event has phase `runtime`;
  5. its claim is exactly `self-audit-marker altered subsequent execution`;
  6. its marker data is exactly `{"marker": "self-audit-marker"}`.
otherwise q_i = 0.
```

The external score for a candidate is the arithmetic mean:

```text
Q = sum(q_i for held-out cases) / number of held-out cases
```

No baseline-relative, self-reported, narrative, or implementation-internal
score is used. Q is not changed after observing results.

## 3. Development and held-out cases

Each trial uses the same fixed case corpus generated from fixed seeds.

- Development: 8 cases, visible to candidate construction.
- Held-out evaluation: 24 cases, never exposed during candidate construction.
- Each case contains a distinct valid finite-state XOSEAC instance and a legal
  ordinary `AddState` or `AddEdge` mutation.
- Held-out cases are generated before trials and stored by digest, with their
  contents hidden from the condition-specific candidate procedure.
- Development cases may be used to detect API misuse, but no held-out score
  may be inspected during candidate generation.

The same case IDs, case order, inputs, and evaluator are used for every
condition. Random seeds are paired across conditions.

## 4. Conditions

Each condition receives the same task statement, API description, source
snapshot, development cases, and resource budget. Each produces one candidate
self-representation per paired seed. The evaluator receives only an opaque
candidate ID and the candidate execution outputs.

### PSA

The candidate must use the frozen `apply_self_application` path on the exact
`operative_instance()` target. Its one allowed self mutation is
`AddState("self-audit-marker")`.

### Generic

A competent generic optimizer receives the same deficiency and APIs but is
not required to call `apply_self_application` or satisfy
`is_self_representation`. It may construct and edit a candidate representation
using the ordinary typed editing functions. It receives the same information
and candidate budget as PSA.

### External-XOSEAC

The candidate is instructed to use XOSEAC structure to propose a modification,
but its submitted target must fail `is_self_representation`. It may still be a
valid XOSEAC instance and may attempt the same S edit. A submitted target
that satisfies the self-target predicate is a condition violation and scores
zero for that trial.

### Sham

The candidate performs self-referential representation activity under the same
budget but changes only a sham S state named `sham-marker`. The evaluator
never treats `sham-marker` as the required runtime marker. This condition is
intended to preserve self-referential activity while making causal alteration
of the evaluated behavior impossible.

## 5. Matched information and computational budgets

Per condition and paired seed:

- one Python process using the frozen repository checkout;
- the same source snapshot and documentation;
- the same 8 development cases;
- at most 200 candidate-construction API calls;
- at most 10 seconds wall-clock candidate-construction time;
- exactly one submitted candidate representation;
- no access to held-out case contents or scores;
- no network access, subprocesses, source writes, or mutation of PSA-03A;
- evaluation itself is capped at 24 held-out cases and is identical across
  conditions.

Failed construction, timeout, invalid candidate, predicate violation, or
missing candidate is retained as a recorded failure and receives `Q = 0`.

## 6. Trial count and stopping rule

There are 20 paired seeds, producing 20 candidates per condition and 80 total
candidate records. All 20 paired seeds are run. There is no interim stopping,
replacement, repair, or retuning based on observed scores.

The only permitted stop before all trials is an infrastructure failure that
prevents a fair matched run for every condition. Such a stop must preserve all
records and be reported as incomplete rather than analyzed as a result.

## 7. Blinding and records

Candidates are assigned random opaque IDs before evaluation. The evaluator
does not receive condition labels, construction logs, or self-target status.
The condition-to-ID mapping is sealed until all Q values and raw execution
traces have been written.

For every candidate, including failures, record:

- paired seed and candidate ID;
- condition mapping in the sealed manifest;
- complete candidate representation or a failure record;
- self-target predicate result;
- before and successor states when available;
- complete provenance trace;
- every held-out case output, q_i, and failure reason;
- total API calls and wall-clock construction time;
- evaluator version and source snapshot digest.

## 8. Analysis and success criteria

The primary hypothesis is:

```text
H1: E[Q(PSA)] > E[Q(Generic)]
H0: E[Q(PSA)] <= E[Q(Generic)]
```

The primary estimate is the mean paired difference
`Q(PSA, seed) - Q(Generic, seed)`. Report both raw group means and the
paired mean difference with a two-sided 95% paired bootstrap confidence
interval over the 20 seeds. The pre-registered primary success criterion is
that the point estimate is positive and the 95% interval lower bound is
strictly greater than zero.

Secondary comparisons use the same fixed estimator and report raw means,
paired differences, and 95% paired bootstrap intervals for:

- PSA minus External-XOSEAC;
- PSA minus Sham.

No comparison to an unmodified baseline is sufficient for success. A PSA
candidate improving over baseline but not exceeding Generic fails the primary
criterion. Ties and losses are reported plainly. No metric, case, condition,
budget, or analysis rule may be changed after trial execution begins.

## 9. Scope boundary

This is an apparatus comparison, not a claim of Productive Self-Application.
No score gain is interpreted as productivity, improvement of the operative
system, generalization, or contact with external reality. The protocol tests
only whether the frozen self-application path produces the specified
observable consequence more often than the matched controls.
