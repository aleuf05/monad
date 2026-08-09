# Instrument 001 — first test run

**Date:** 2026-08-09 · **Run type:** TEST RUN, quick pass, Admiral-authorized
**Harness:** `tools/instrument-001/instrument.py` (seed 20260809, deterministic)
**Preregistration:** `tools/instrument-001/PREREGISTRATION.md` + amendment 1
**Analysis of record:** `docs/research/INSTRUMENT_001_LIVE_CAPTAIN_ASSESSMENT_2026-08-09.md`

## Headline

**The instrument has a zero point. The transfer claim does not survive a fair
baseline.**

Both halves matter. The first is the thing worth having; the second is the
first real failure the instrument has produced, and it was produced in about
four minutes of compute.

## Results

```
EXP0  null calibration    D_A=precipitation  D_B=char_frequency  D_C=random_walk
      nRMSE  frozen 0.0604   powerlaw-baseline 0.0358   saturating-baseline 0.1048
      Q = -0.0246

EXP1  honest triple       D_A=logistic  D_B=queue_throughput  D_C=resource_scaling
      nRMSE  frozen 0.2336   powerlaw-baseline 0.5364   saturating-baseline 0.0234
      Q = +0.3027    Q_surrogate = +0.1054    Q vs fair baseline = -0.2102
```

| Preregistered kill condition | Result |
|---|---|
| K1 zero-point failure (Exp0 `Q > 0.05`) | clear |
| K2 no transfer (Exp1 `Q ≤ 0`) | clear *(against an inadequate baseline)* |
| K3 surrogate parity (`Q_s ≥ 0.8·Q`) | clear |

**All three cleared, and the pass is not real.** See below.

## What went wrong with the pass

The tell was in the run-1 output: `Q_surrogate = +0.1054`. The surrogate arm's
structure is destroyed by construction — shuffled y-values against the original
x. It should not beat anything. It beat the baseline.

Diagnosis: arms were matched on **parameter count** but not on **inductive
bias**. The preregistered Π₀ is an unbounded power law; D_C saturates.
Extrapolating an unbounded family across the withheld 70% of a saturating curve
fails for reasons having nothing to do with cross-domain structure, so *any*
bounded frozen shape wins that comparison — including a shuffled one.

The exploratory arm (2-parameter *saturating* baseline, same inductive bias,
zero cross-domain information) settles it: **0.0234 vs the frozen arm's
0.2336.** The frozen cross-domain shape is about ten times worse than a
two-parameter fit to D_C's own visible data. K2 fires on a fair baseline.

## The transferable methodological finding

> **Q is only as meaningful as the baseline's inductive bias. Parameter-count
> matching is not sufficient, and a weak Π₀ manufactures positive Q.**

This generalizes past this run and past this instrument. It is a concrete,
checkable addition to the §1 critique: the original argument was that Π₁ cannot
fail because T is chosen freely. This adds that Π₁ can also appear to succeed
because Π₀ is chosen badly — and unlike the T problem, this one has a
mechanical detector. **A surrogate arm that beats the baseline is a signal that
the baseline is broken.** That check costs nothing and should be standard.

## Second defect, independent of the first

Exp1's D_B and D_C were both generated from `K·x/(x+τ)`. The shared structure
was built in by the author. Even a clean win would have demonstrated only that
the harness detects transfer it was handed. **No real-data triple has been
run, and the Exp1 row carries no evidential weight about the world.**

## What actually survives

Exp0. On a triple with no shared generative structure — gamma-distributed
rainfall, Zipf frequencies, a driftless random walk — the instrument did not
report transfer (`Q = -0.0246`). That was the cheapest and most decisive check
available, it was run first, and it held. An instrument with a demonstrated
zero point is worth more than one with an unreplicated positive result.

## Binding consequences for the next run

1. The preregistered Π₀ is **withdrawn as inadequate**. Baselines must match
   inductive bias, not just parameter count.
2. This triple is now **exploratory and cannot be reused** for confirmation.
   A confirmatory run restarts on a fresh triple.
3. The next triple must use **real data**, not author-generated curves.
4. The surrogate-beats-baseline check should be promoted to a standing
   precondition, evaluated before Q is even reported.

## Reproduce

```sh
python3 tools/instrument-001/instrument.py          # human-readable
python3 tools/instrument-001/instrument.py --json   # raw record
```

Deterministic under seed 20260809; two runs produce identical output.

## Files

- `tools/instrument-001/instrument.py` — harness
- `tools/instrument-001/PREREGISTRATION.md` — thresholds + amendment 1
- this report

## Honest limitation

Preregistration and harness were authored in the same session by the same
agent. The thresholds were fixed before any number existed, which is what the
freeze can guarantee. It does not guarantee independence between whoever chose
the domains and whoever chose the metric — the deeper defect in §1 of the
assessment, still unresolved.
