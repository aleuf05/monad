# Monad-0 Phase 2 — Nexus Harness

This package separates the tested organism from the experimental harness.

## Component A: `monad_zero.organism`

Provides:

- validated `ArchitectureVector` updates queued for tick boundaries;
- standardized, single-occupancy perturbation receptor with reversible patches;
- versioned `CycleTelemetry` and typed closure components;
- normalized recovery distance with a five-tick persistence requirement;
- architecture-update and perturbation provenance events.

## Component B: `monad_zero.harness`

Provides:

- canonical forward/reverse q schedule and SLOW/MEDIUM/FAST rates;
- standardized probe execution;
- six shadow-control factories and invariant metadata;
- immutable manifests and replay digests;
- formal telemetry schema at `schemas/telemetry.schema.json`;
- Phase 2A telemetry ingestion, M0/M2 fitting, descriptive M1/M3 summaries,
  and hysteresis calculation.

Advanced GAM, latent-state, nested cross-validation, mixture, and metastability
analysis remain Phase 2B work. The organism and harness have no GUI or external
side effects.

Run a small harness experiment:

```text
python3 -m monad_zero.harness --seed 5 --points 3 --ticks-per-step 1
```

Run tests:

```text
python3 -m unittest monad_zero.tests.test_phase2 tools.monad0.test_engine
```
