# Instrument 001 — preregistration

**Written:** 2026-08-09, **before** the harness existed and before any result.
**Authority:** Admiral order "Continue with Packet payload (Begin Work)".
**Governing analysis:** `docs/research/INSTRUMENT_001_LIVE_CAPTAIN_ASSESSMENT_2026-08-09.md`

This file exists so the kill conditions cannot be adjusted after seeing
numbers. If any threshold below is edited, the run is void and starts over on
a fresh triple. Edits append; they never overwrite.

## What is frozen

The candidate invariant `I` is a **nonparametric normalized shape** `f̂`,
estimated from D_A and D_B only:

1. For each of D_A, D_B: estimate its own scale `K` (asymptote) and `τ`
   (half-saturation abscissa) from that domain's full data.
2. Rescale: `u = x/τ`, `v = y/K`.
3. Average the two rescaled curves on a common `u` grid → `f̂(u)`.

`f̂` is then **frozen**. D_C is not consulted at any point in the above.

## Prediction task

Given only the **first 30%** of D_C's abscissa range, fit exactly two free
parameters `(K_C, τ_C)` in `ŷ(x) = K_C · f̂(x / τ_C)`, then predict the
withheld **70%**. Score = RMSE on the withheld region, normalized by the
withheld region's mean `|y|` (nRMSE), so domains with different units compare.

## Arms (capacity matched at 2 free parameters)

| Arm | Description | Free params on D_C |
|---|---|---|
| **a — Π₁ frozen** | `f̂` from D_A,D_B; fit `K_C, τ_C` | 2 |
| **c — Π₀ baseline** | generic 2-parameter power law `a·x^b`, fit on same 30% | 2 |
| **s — surrogate control** | `f̂` derived from *surrogate* D_A,D_B (structure destroyed, marginals preserved); fit `K_C, τ_C` | 2 |

`Q = nRMSE(c) − nRMSE(a)`. Positive Q means frozen cross-domain structure beat
the baseline. `Q_s = nRMSE(c) − nRMSE(s)` is the same quantity for the
surrogate.

## Preregistered kill conditions

Evaluated automatically by the harness. Any one firing kills the claim.

- **K1 — zero-point failure.** On the null triple (Experiment 0), `Q > 0.05`.
  The instrument reports transfer where no shared structure exists.
- **K2 — no transfer.** On the honest triple (Experiment 1), `Q ≤ 0`.
- **K3 — surrogate parity.** On the honest triple, `Q_s ≥ 0.8 · Q`. The
  transfer came from fitting flexibility, not shared structure.

Thresholds: `0.05` on K1 is a tolerance band for numerical noise around zero,
not a permitted amount of false positive. `0.8` on K3 is taken directly from
the assessment document's §5, written before any implementation.

## Declared in advance

- **Null triple (Exp 0):** gamma-distributed daily-precipitation surrogate;
  Zipf character-frequency surrogate; pseudorandom walk as D_C. No shared
  generative structure by construction.
- **Honest triple (Exp 1):** logistic population growth (D_A); M/M/1-style
  queueing throughput vs offered load (D_B); a resource-scaling performance
  curve (D_C). Shared candidate law: saturating growth under a limiting
  resource.
- **Seed:** 20260809, fixed. Runs must be reproducible.
- **One exploratory reselection** of the honest triple is permitted and must
  be reported as exploratory; the confirmatory run then restarts on a fresh
  triple.

## Honest limitation, recorded before results

The preregistration and the harness were authored in the same working session
by the same agent. What this file can guarantee is that the **thresholds were
fixed before any number was produced**. What it cannot guarantee is
independence between the person choosing the domains and the person choosing
the metric — the deeper defect named in §1 of the assessment. This run tests
whether the instrument has a zero point and whether transfer survives a
surrogate control. It does not resolve the selection problem.

---

## Amendment 1 — 2026-08-09, appended after the first run

Append-only per doctrine 013. Nothing above is altered.

**What happened.** The first test run cleared all three preregistered kill
conditions (Exp1 `Q = +0.3027`). It also produced a signal that should not
occur: the **surrogate** arm, whose structure was deliberately destroyed, also
beat the baseline (`Q_s = +0.1054`). Shuffled data beating a baseline means the
baseline, not the instrument, was doing the work.

**Diagnosis.** Arms a and c were matched on **parameter count** but not on
**inductive bias**. The Pi_0 baseline is an unbounded power law; D_C saturates.
Extrapolating an unbounded family across the withheld 70% of a saturating
curve fails badly for reasons that have nothing to do with cross-domain
structure. Any frozen shape that is merely *bounded* wins that comparison,
including a shuffled one.

**Exploratory arm c2 (post-hoc, not preregistered).** A 2-parameter
*saturating* baseline `y = K x/(x+tau)` fit on the same visible 30% -- same
inductive bias as arm a, zero cross-domain information.

| Triple | frozen a | preregistered baseline c | saturating baseline c2 |
|---|---|---|---|
| Exp0 null | 0.0604 | 0.0358 | 0.1048 |
| Exp1 honest | 0.2336 | 0.5364 | **0.0234** |

`Q` against the fair baseline on the honest triple: **-0.2102**. The frozen
cross-domain shape is ~10x worse than a two-parameter fit to D_C's own visible
data. **K2 fires under a correctly specified baseline.**

**Consequence, binding on the next run.** The preregistered Pi_0 above is
withdrawn as inadequate. Any confirmatory run must use a baseline matched on
inductive bias, and must restart on a fresh triple -- this triple is now
exploratory and cannot be reused for confirmation.

**Second defect, independent of the baseline.** Exp1's D_B and D_C were both
generated from `K x/(x+tau)`. The shared structure was built in by the author.
Even a clean win would have shown only that the harness detects transfer it was
handed. No real-data triple has been run. The Exp1 row above carries no
evidential weight about the world.

**What does survive.** Exp0's zero-point check is a genuine result: on a triple
with no shared generative structure, the instrument did not report transfer
(`Q = -0.0246`, K1 clear). The instrument has a zero point. That was the
cheapest and most decisive thing to establish, and it held.

---

## Amendment 2 — 2026-08-09, appended after the stability study

Append-only. Nothing above is altered.

**K1 and K2 both fire. Instrument 001 is killed on present evidence.**

1200 trials, 200 seeds x 6 triples, 0 harness failures.
Harness: `tools/instrument-001/stability.py`. Primary metric is `Q_fair`
(against the inductive-bias-matched saturating baseline, per amendment 1).

| Triple | kind | median Q_fair | IQR | Q>0 rate | surrogate gate trip |
|---|---|---|---|---|---|
| N1 precip/zipf/walk | null | +0.1268 | [0.010, 0.163] | 77.0% | 64.5% |
| N2 noise/saw/walk | null | +0.0463 | [-0.007, 0.112] | 71.5% | 74.0% |
| N3 decay/trend/walk | null | +0.1059 | [-0.001, 0.189] | 74.0% | 41.5% |
| N4 walk/walk/walk | null | +0.1223 | [0.032, 0.168] | 82.5% | 83.5% |
| H1 rigged same-family | honest | **-0.1993** | [-0.211, -0.191] | 0.0% | 0.0% |
| H2 cross-family Gompertz | honest | **-1.1394** | [-1.170, -1.108] | 0.0% | 0.0% |

**K1 — zero-point failure. FIRES.** False-positive rate on null triples,
`Q_fair > 0.05`: **63.0%** (n=800). Any positive Q: 76.2%. The instrument
reports transfer on data with no shared generative structure, most of the time.

**K2 — no transfer. FIRES.** Both honest triples are negative on **0 of 200
seeds**. Cross-family transfer (H2) is catastrophic: median -1.139.

**Correction to the first run.** The single-seed Exp0 result was reported as
"the instrument has a zero point." It was a lucky draw. Worse, the signal was
already visible in run 1 and the threshold hid it: Exp0's Q against the *fair*
baseline was **+0.0444** — positive, and under the 0.05 tolerance band only by
accident. The claim that the instrument has a demonstrated zero point is
**withdrawn**.

**Diagnosis — what Q actually measures.** Not the presence of shared structure.
`Q` measures **which of two inductive biases better matches D_C**, and the
direction is set by D_C's shape alone:

- D_C saturating -> the saturating baseline wins -> Q negative (H1, H2).
- D_C walk-like -> the near-flat frozen shape wins -> Q positive (N1-N4).

Whether D_A and D_B share anything with D_C never enters. The surrogate arm
proves it: with the x-y relation destroyed, it still beats the baseline on
41.5%-83.5% of null trials.

This is the §1 critique confirmed by measurement rather than argument — the
verdict is dominated by the instrument's own choices (E, Pi_0), not by the
systems under study.
