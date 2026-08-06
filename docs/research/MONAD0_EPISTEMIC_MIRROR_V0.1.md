# Monad-0 — Epistemic Mirror

**Status:** Implemented research slice; experimental, not production control
software  
**Implementation:** [`tools/monad0/`](../../tools/monad0/) and
[`monad_zero/`](../../monad_zero/)  
**Specification:** Master Engineering Specification, 2026-08-01

## Purpose

Monad-0 is a deterministic, headless comparative engine for testing whether a
persistent human–AI system is better described by constrained operational flows
than by a static component graph or organizational chart.

The experiment runs four controllers against independently cloned environments
with the same seed:

- **Monad-0:** explicit self-model, causal hypotheses, bounded downward
  intervention contracts, and reflexive revision;
- **Flat Adaptive Control:** direct parameter updates without an explicit
  structural self-model;
- **Decorative Self-Model Control:** descriptive graph and predictions without
  downward parameter authority;
- **Open-Loop Control:** fixed parameter rules without reflexive evaluation.

## Environment

The synthetic sandbox is tick-based and maintains coupled energy, material,
compute, and maintenance pools in `[0.0, 1.0]`. Harvest exploitation decays
future yield; exploration incurs maintenance debt; modeling consumes compute;
and arbitrary tick-indexed perturbations can be injected through the CLI.

## Strange-loop criteria

- **Upward construction (U):** worker actions produce telemetry consumed by the
  self-model.
- **Downward causation (D):** Monad-0 issues a bounded contract that locks one
  worker parameter for a finite evaluation window.
- **Historical persistence (H):** every tick, contract, hypothesis, and model
  revision is emitted as structured event history.
- **Reflexive revision (R):** contract outcomes confirm or refute the associated
  hypothesis and adjust graph confidence/edge weight.

## Metrics

JSON telemetry exposes time-to-recovery after perturbation,
multi-dimensional self-opacity, attribution accuracy, graph node/edge counts,
topology mutation count, and hypothesis calibration index.

Run and test instructions are in [`tools/monad0/README.md`](../../tools/monad0/README.md).
The first implementation is intentionally small so causal legibility and
comparative behavior can be inspected before adding richer simulation.

## Phase 2 Nexus harness

The refinement package adds a typed organism interface and a separate harness
for forward/reverse q sweeps, standardized probes, shadow controls, manifests,
replay digests, and Phase 2A statistical summaries. Advanced GAM and latent
regime fitting remain explicitly deferred to Phase 2B.
