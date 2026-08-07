# Doctrine 025 — Capability Retrieval to Integration

**Authority:** Admiral Cameron Lampley, 2026-08-05 — *"log as needs further
engineering create new discipline if needed improve process on the fly"*.

**Status:** Active, provisional discipline.

## Finding

Monad contains prior experiments and capabilities that may be stronger than
their present integration suggests. A remembered success is neither disposable
nor automatically ready for reuse. It becomes an engineering input through a
short evidence-bearing retrieval process.

## The discipline

```text
remembered capability
  → locate artifacts
  → reproduce the result
  → characterize its operating envelope
  → identify the authoritative integration seam
  → build one reversible connection
  → inspect live behavior
  → promote, revise, or preserve as not presently runnable
```

### 1. Locate

Find code, models, data, demonstrations, logs, hardware assumptions, and source
claims. Record real paths and provenance. Do not rebuild merely because the
original is difficult to find.

### 2. Reproduce

Run the smallest representative case in the current environment. Distinguish
historical evidence, present reproduction, and inference about what should
still work.

### 3. Characterize

Measure the capability where it matters: inputs, outputs, latency, stability,
failure behavior, compute cost, dependencies, privacy exposure, and known
limits. Preserve anomalies rather than tuning them out before inspection.

### 4. Integrate minimally

Choose the existing live target and its authoritative state seam. Connect one
useful reversible behavior. Do not create a shadow application or duplicate
pipeline to avoid understanding the real system.

### 5. Promote by evidence

A capability becomes commissioned only when its representative test passes,
the live result is inspected, its stop/correction path works, and its operating
limits are visible. Otherwise mark it accurately as one of:

- `LOCATED_NOT_REPRODUCED`
- `REPRODUCED_NOT_INTEGRATED`
- `NEEDS_FURTHER_ENGINEERING`
- `BLOCKED_BY_MISSING_ARTIFACT_OR_HARDWARE`
- `COMMISSIONED`

## On-the-fly improvement rule

This discipline is intentionally compact. When real retrieval work exposes a
missing step, repair the process in place and record why. Do not require a new
ceremony for every refinement; do require that process changes preserve truth,
reversibility, provenance, and the existing live target.

## First application

`CAP-ARI-004`, the Laptop Live-Lab Sensor and Rich Interaction Node, is the
first named application. Its reported rich hand-gesture capability begins at
Locate, not at integration, and the packet remains `NEEDS_FURTHER_ENGINEERING`
until present evidence supports a more precise state.
