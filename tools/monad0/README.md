# Monad-0 — Epistemic Mirror

Monad-0 is a headless comparative research engine implementing the four-system
matrix in the Master Engineering Specification. It is a synthetic experiment,
not production control software.

## Run

From the repository root:

```text
python3 -m tools.monad0.engine --seed 7 --ticks 60 \
  --output /tmp/monad0-result.json \
  --jsonl /tmp/monad0-events.jsonl
```

The run executes Monad-0, Flat Adaptive Control, Decorative Self-Model
Control, and Open-Loop Control against independently cloned environments with
the same seed and programmable perturbations. The seed controls deterministic
per-tick noise and yield variation; `equilibrium_viability` (default `0.5`) is
the explicit recovery threshold. JSONL telemetry includes the
complete tick state, parameters, actions, model updates, contracts, and
resolution events.

## Test

```text
python3 -m unittest tools.monad0.test_engine
```

The tests cover deterministic seeds, injectably scheduled perturbations, the
four-system matrix, JSON serialization, bounded intervention lifecycle,
reflexive revision, and declared control boundaries.

## Contract interpretation

Monad-0 is the only variant with an explicit causal self-model, downward
intervention contracts, and reflexive hypothesis revision. The other three
variants are controls: direct adaptive updates, descriptive-but-noncausal
self-modeling, and static open-loop rules.
