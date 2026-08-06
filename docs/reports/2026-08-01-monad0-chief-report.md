# Chief Report — Monad-0 Epistemic Mirror

**Date:** 2026-08-01  
**Audience:** Chief  
**Status:** Tested foundational research artifact; corrective increment applied;
not production control software

## Executive finding

Monad-0 now exists as a runnable, headless comparative research engine. It
executes four controller architectures against independently cloned,
four-channel synthetic environments and emits structured tick-by-tick
telemetry.

The artifact is suitable for the next research pass: it makes the proposed
strange-loop criteria concrete enough to inspect, test, and challenge. It is
not yet strong evidence that the full theory is validated.

## What was built

- **Monad-0:** explicit self-model, causal hypotheses, bounded intervention
  contracts, and reflexive revision.
- **Flat Adaptive Control:** direct policy updates without an explicit causal
  self-graph.
- **Decorative Self-Model Control:** descriptive self-model with no downward
  parameter authority.
- **Open-Loop Control:** fixed rule changes without reflexive evaluation.

The environment models energy, material, compute, and maintenance pools with
non-stationary exploitation decay, exploration debt, modeling cost, and
programmable perturbations.

## Tested artifact

- [Engine](../../tools/monad0/engine.py)
- [Tests](../../tools/monad0/test_engine.py)
- [Usage guide](../../tools/monad0/README.md)
- [Research record](../research/MONAD0_EPISTEMIC_MIRROR_V0.1.md)

## Validation performed

```text
python3 -m unittest tools.monad0.test_engine
python3 -m tools.monad0.engine --seed 7 --ticks 24
python3 tools/build-admiralty-archive.py --scan
python3 tools/check-admiralty-archive.py
git diff --check
```

Result: **4/4 engine tests passed.** JSON and JSONL telemetry generation was
also exercised successfully.

The tests cover deterministic replay, scheduled perturbations, four-system
comparability, JSON serialization, bounded contract lifecycle, self-model
revision, topology mutation, and controller boundaries.

## Current measured surfaces

The engine exposes:

- tick-level resource and action telemetry;
- contract issuance and resolution events;
- hypothesis confidence and graph edge changes;
- time-to-recovery slots;
- multi-dimensional self-opacity;
- attribution-accuracy field;
- topology node/edge counts and mutation count;
- hypothesis calibration index.

These fields are instrumentation surfaces. They should not yet be interpreted
as validated scientific measures without calibration experiments.

## Corrective increment applied

The Chief recommendations were implemented after the initial report:

- the seed now controls deterministic per-tick noise and yield variation;
- refuted contracts restore `baseline_value`;
- contract outcomes are evaluated baseline-relatively using declared deltas;
- recovery uses an explicit `equilibrium_viability` threshold (default `0.5`);
- benchmark tests verify replay stability, cross-seed divergence, rollback, and
  explicit recovery semantics.

## Remaining limitations

1. The self-model currently emphasizes one maintenance-debt hypothesis rather
   than a general causal graph.
2. Recovery can remain unrecovered when the synthetic environment's resource
   dynamics cannot return above the declared threshold; this is now explicit
   rather than ambiguous.
3. Durable history exists when JSON/JSONL output is requested; automatic
   archival of every run is not yet enabled.

## Chief recommendation

Treat this as a **research instrument v0.1**, not as a finished theory or
autonomous controller. The next engineering increment should expand the causal
graph, add calibrated benchmark scenarios, and decide whether experiment
outputs should be archived automatically before increasing simulation
complexity.

## Scope and authority

No FleetCore, public UI, deployment, permission, or external-system changes
were made. The artifact is repository-local and headless. It does not authorize
autonomous action or alter Monad command doctrine.
