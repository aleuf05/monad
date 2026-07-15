# Current Failure Modes — Repo Scan

Date: 2026-07-15T18:53:41Z

Prepared by: Claude

Scope: concrete failure modes visible in the current repo state, with no
speculation and no remediation logic.

## What is actually open

There are no open implementation tasks left in the radio-console slice.
The only queue items still open are human-gated decisions or access
blockers:

- `HUMAN-01`
- `HUMAN-02`
- `HUMAN-03`
- `HUMAN-04`

Those are not code defects. They are decision or access dependencies.

## Concrete failure modes

### 1. Browser speech can be absent while the console is otherwise healthy

The radio console is designed to fall back to timed visual transmission when
`SpeechSynthesis` is missing or has no usable voices. In that environment the
transcript, indicators, and queue still work, but audio does not. That is an
acceptable degradation, but it is still a failure mode operators should know
about.

### 2. `DRIFT-01` is intentionally narrow

The drift design now names `toys/` ↔ `web/toys/` mirror divergence only.
Config drift, infra drift, and host/package drift remain out of scope by
design. That is not a bug, but it is a boundary that can be mistaken for a
broader drift detector if it is not documented.

### 3. Human-gated queue items can stall progress indefinitely

The queue currently contains four blocked human items. If those decisions do
not arrive, the queue will remain partially open even though no agent-side work
is outstanding.

### 4. Report-only detectors cannot repair drift

`DRIFT-01` is intentionally read-only. It can report mismatches, but it cannot
heal them. If an operator expects self-correction, that expectation will be
wrong.

## Bottom line

The repo is not carrying an active implementation defect in the current radio
slice. The real remaining issues are bounded degradations and blocked human
decisions.
