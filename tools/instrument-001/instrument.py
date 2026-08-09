#!/usr/bin/env python3
"""Instrument 001 -- frozen-transfer test harness (TEST RUN).

Implements the repaired instrument from
docs/research/INSTRUMENT_001_LIVE_CAPTAIN_ASSESSMENT_2026-08-09.md section 2:
not an invariance detector, but a transfer test with a preregistered freeze.

    derive f-hat from D_A,D_B  ->  FREEZE  ->  fit 2 params on D_C's first 30%
    ->  predict withheld 70%   ->  Q = nRMSE(baseline) - nRMSE(frozen)

Kill conditions K1/K2/K3 and all thresholds are fixed in PREREGISTRATION.md,
written before this file existed. The harness evaluates them automatically
and prints the verdict; it does not get to choose them.

Pure standard library on purpose -- no numpy on this host, and a harness whose
result depends on an optimizer's defaults is harder to trust than one doing a
visible grid search.
"""
from __future__ import annotations

import argparse
import json
import math
import random
from dataclasses import dataclass, asdict

SEED = 20260809

# Thresholds are read from the preregistration, not chosen here.
K1_ZERO_POINT = 0.05   # null-triple Q above this = instrument reports phantom transfer
K3_SURROGATE_PARITY = 0.8


# ---------------------------------------------------------------------------
# Domains. Each is (xs, ys). Generated so ground truth is known.
# ---------------------------------------------------------------------------

@dataclass
class Domain:
    name: str
    xs: list[float]
    ys: list[float]
    note: str


def _noise(rng, scale):
    return 1.0 + rng.gauss(0.0, scale)


def logistic_growth(rng, n=60) -> Domain:
    """D_A: closed-culture population growth. Sigmoid saturation."""
    K, r, x0 = 1.0e6, 0.55, 9.0
    xs = [20.0 * i / (n - 1) for i in range(n)]
    ys = [K / (1.0 + math.exp(-r * (x - x0))) * _noise(rng, 0.02) for x in xs]
    return Domain("logistic_population", xs, ys, "closed culture, sigmoid saturation")


def queue_saturation(rng, n=60) -> Domain:
    """D_B: throughput vs offered load. Hyperbolic saturation at capacity."""
    K, tau = 500.0, 120.0
    xs = [1000.0 * i / (n - 1) for i in range(n)]
    ys = [K * x / (x + tau) * _noise(rng, 0.02) for x in xs]
    return Domain("queue_throughput", xs, ys, "offered load vs throughput, hyperbolic")


def scaling_curve(rng, n=60) -> Domain:
    """D_C: performance vs resource. Same saturating family, different field,
    wildly different units and scales."""
    K, tau = 0.92, 3000.0
    xs = [20000.0 * i / (n - 1) for i in range(n)]
    ys = [K * x / (x + tau) * _noise(rng, 0.02) for x in xs]
    return Domain("resource_scaling", xs, ys, "performance vs resource budget")


def precipitation_null(rng, n=60) -> Domain:
    """Null D_A: daily rainfall. No trend, no saturation."""
    xs = [float(i) for i in range(n)]
    ys = [rng.gammavariate(2.0, 3.0) + 0.5 for _ in range(n)]
    return Domain("precipitation", xs, ys, "gamma-distributed daily rainfall, no trend")


def zipf_null(rng, n=60) -> Domain:
    """Null D_B: character frequency by rank. Decreasing power law."""
    xs = [float(i + 1) for i in range(n)]
    ys = [1000.0 / (i + 1) ** 1.05 * _noise(rng, 0.05) for i in range(n)]
    return Domain("char_frequency", xs, ys, "Zipf-like frequency by rank")


def random_walk_null(rng, n=60) -> Domain:
    """Null D_C: driftless random walk, kept positive so the power-law
    baseline stays defined (avoids a mid-run deviation from prereg)."""
    xs = [float(i + 1) for i in range(n)]
    y, ys = 100.0, []
    for _ in range(n):
        y += rng.gauss(0.0, 2.0)
        ys.append(max(y, 1.0))
    return Domain("random_walk", xs, ys, "driftless positive random walk")


# ---------------------------------------------------------------------------
# The candidate invariant: a nonparametric normalized shape f-hat.
# ---------------------------------------------------------------------------

U_GRID = [0.05 * i for i in range(1, 121)]  # u = x/tau, up to 6.0


def estimate_scale(d: Domain) -> tuple[float, float]:
    """K = asymptote (mean of top decile), tau = abscissa where y first
    crosses K/2. Estimated from the domain's OWN data only."""
    ys_sorted = sorted(d.ys)
    top = ys_sorted[int(0.9 * len(ys_sorted)):] or ys_sorted[-1:]
    K = sum(top) / len(top)
    half = K / 2.0
    tau = d.xs[-1]
    for i in range(1, len(d.xs)):
        if (d.ys[i - 1] - half) * (d.ys[i] - half) <= 0 and d.ys[i] != d.ys[i - 1]:
            frac = (half - d.ys[i - 1]) / (d.ys[i] - d.ys[i - 1])
            tau = d.xs[i - 1] + frac * (d.xs[i] - d.xs[i - 1])
            break
    return K, (tau if tau > 0 else max(d.xs[-1], 1e-9))


def interp(xs: list[float], ys: list[float], x: float) -> float:
    """Linear interpolation, clamped at both ends. Clamping at the right end
    encodes the saturating assumption -- and is exactly what should FAIL to
    help on a non-saturating null domain."""
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    lo, hi = 0, len(xs) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if xs[mid] <= x:
            lo = mid
        else:
            hi = mid
    span = xs[hi] - xs[lo]
    if span == 0:
        return ys[lo]
    return ys[lo] + (ys[hi] - ys[lo]) * (x - xs[lo]) / span


def derive_shape(d_a: Domain, d_b: Domain) -> list[float]:
    """f-hat: average the two rescaled curves on a common u grid.
    D_C is never touched here. This is the object that gets frozen."""
    curves = []
    for d in (d_a, d_b):
        K, tau = estimate_scale(d)
        us = [x / tau for x in d.xs]
        vs = [y / K for y in d.ys]
        pairs = sorted(zip(us, vs))
        us = [p[0] for p in pairs]
        vs = [p[1] for p in pairs]
        curves.append([interp(us, vs, u) for u in U_GRID])
    return [(c1 + c2) / 2.0 for c1, c2 in zip(*curves)]


def surrogate(d: Domain, rng) -> Domain:
    """Destroy the x-y relation, preserve the marginal distribution of y.
    Standard surrogate-data control: if f-hat derived from THIS transfers as
    well as the real one, the transfer was fitting flexibility."""
    ys = list(d.ys)
    rng.shuffle(ys)
    return Domain(d.name + "_surrogate", list(d.xs), ys, "y-marginal preserved, structure destroyed")


# ---------------------------------------------------------------------------
# Fitting. Two free parameters everywhere -- capacity matched by construction.
# ---------------------------------------------------------------------------

def _rmse(pred, actual):
    return math.sqrt(sum((p - a) ** 2 for p, a in zip(pred, actual)) / len(actual))


def nrmse(pred, actual):
    denom = sum(abs(a) for a in actual) / len(actual)
    return _rmse(pred, actual) / denom if denom > 0 else float("inf")


def fit_frozen(shape: list[float], xs: list[float], ys: list[float]) -> tuple[float, float]:
    """Fit (K_C, tau_C) in y = K * f_hat(x / tau) by coarse-to-fine grid
    search on the visible 30% only."""
    y_max = max(ys) if ys else 1.0
    x_span = max(xs) if xs else 1.0
    best = (None, None, float("inf"))
    k_lo, k_hi = 0.2 * y_max, 8.0 * y_max
    t_lo, t_hi = 0.01 * x_span, 20.0 * x_span
    for _ in range(4):  # 4 refinement passes
        for i in range(24):
            K = k_lo + (k_hi - k_lo) * i / 23.0
            for j in range(24):
                tau = t_lo * (t_hi / t_lo) ** (j / 23.0)  # log-spaced
                pred = [K * interp(U_GRID, shape, x / tau) for x in xs]
                err = _rmse(pred, ys)
                if err < best[2]:
                    best = (K, tau, err)
        K, tau, _ = best
        k_lo, k_hi = K * 0.6, K * 1.6
        t_lo, t_hi = max(tau * 0.3, 1e-12), tau * 3.0
    return best[0], best[1]


def fit_powerlaw(xs: list[float], ys: list[float]) -> tuple[float, float]:
    """Baseline Pi_0: y = a * x^b, closed-form least squares in log-log.
    Two free parameters -- same budget as the frozen arm."""
    pts = [(math.log(x), math.log(y)) for x, y in zip(xs, ys) if x > 0 and y > 0]
    if len(pts) < 2:
        return (sum(ys) / len(ys), 0.0)
    n = len(pts)
    sx = sum(p[0] for p in pts); sy = sum(p[1] for p in pts)
    sxx = sum(p[0] ** 2 for p in pts); sxy = sum(p[0] * p[1] for p in pts)
    denom = n * sxx - sx * sx
    if abs(denom) < 1e-12:
        return (math.exp(sy / n), 0.0)
    b = (n * sxy - sx * sy) / denom
    a = math.exp((sy - b * sx) / n)
    return a, b


# ---------------------------------------------------------------------------
# One experiment = one triple, three arms.
# ---------------------------------------------------------------------------

def run_triple(label: str, d_a: Domain, d_b: Domain, d_c: Domain, rng) -> dict:
    cut = int(0.3 * len(d_c.xs))
    vis_x, vis_y = d_c.xs[:cut], d_c.ys[:cut]
    hid_x, hid_y = d_c.xs[cut:], d_c.ys[cut:]

    # Arm a -- frozen transfer.
    shape = derive_shape(d_a, d_b)
    K, tau = fit_frozen(shape, vis_x, vis_y)
    err_a = nrmse([K * interp(U_GRID, shape, x / tau) for x in hid_x], hid_y)

    # Arm s -- surrogate control.
    shape_s = derive_shape(surrogate(d_a, rng), surrogate(d_b, rng))
    Ks, taus = fit_frozen(shape_s, vis_x, vis_y)
    err_s = nrmse([Ks * interp(U_GRID, shape_s, x / taus) for x in hid_x], hid_y)

    # Arm c -- baseline, same parameter budget, D_C partial only.
    a, b = fit_powerlaw(vis_x, vis_y)
    err_c = nrmse([a * (x ** b) if x > 0 else a for x in hid_x], hid_y)

    # Arm c2 -- EXPLORATORY, added post-hoc after the first run showed the
    # surrogate arm also beating arm c. A power law is unbounded, so it
    # extrapolates badly on saturating data: arms c and a were matched on
    # parameter COUNT but not on inductive bias, which flatters Pi_1. This
    # arm is a 2-parameter *saturating* baseline -- the same bias, none of
    # the cross-domain information. Reported separately and never folded
    # into the preregistered Q. See PREREGISTRATION.md amendment 1.
    Kc2, tc2 = fit_frozen([u / (1.0 + u) for u in U_GRID], vis_x, vis_y)
    err_c2 = nrmse([Kc2 * ((x / tc2) / (1.0 + x / tc2)) for x in hid_x], hid_y)

    Q = err_c - err_a
    Q_s = err_c - err_s
    return {
        "EXPLORATORY_nrmse_saturating_baseline_c2": round(err_c2, 6),
        "EXPLORATORY_Q_vs_saturating_baseline": round(err_c2 - err_a, 6),
        "label": label,
        "domains": {"D_A": d_a.name, "D_B": d_b.name, "D_C": d_c.name},
        "visible_points": cut, "withheld_points": len(hid_x),
        "nrmse_frozen_a": round(err_a, 6),
        "nrmse_surrogate_s": round(err_s, 6),
        "nrmse_baseline_c": round(err_c, 6),
        "Q": round(Q, 6),
        "Q_surrogate": round(Q_s, 6),
        "fitted_K": round(K, 6), "fitted_tau": round(tau, 6),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Instrument 001 frozen-transfer test")
    ap.add_argument("--json", action="store_true", help="emit raw JSON only")
    args = ap.parse_args()

    rng = random.Random(SEED)
    exp0 = run_triple("EXP0_null_calibration",
                      precipitation_null(rng), zipf_null(rng), random_walk_null(rng), rng)
    rng2 = random.Random(SEED)
    exp1 = run_triple("EXP1_honest_triple",
                      logistic_growth(rng2), queue_saturation(rng2), scaling_curve(rng2), rng2)

    # Preregistered kill conditions, evaluated mechanically.
    k1 = exp0["Q"] > K1_ZERO_POINT
    k2 = exp1["Q"] <= 0
    k3 = exp1["Q_surrogate"] >= K3_SURROGATE_PARITY * exp1["Q"] if exp1["Q"] > 0 else False
    verdict = {
        "K1_zero_point_failure": k1,
        "K2_no_transfer": k2,
        "K3_surrogate_parity": k3,
        "any_kill_fired": bool(k1 or k2 or k3),
    }
    out = {"seed": SEED, "run_type": "TEST RUN", "exp0": exp0, "exp1": exp1, "kill_conditions": verdict}

    if args.json:
        print(json.dumps(out, indent=2, sort_keys=True))
        return 0

    for exp in (exp0, exp1):
        print(f"\n=== {exp['label']} ===")
        print(f"  D_A={exp['domains']['D_A']}  D_B={exp['domains']['D_B']}  D_C={exp['domains']['D_C']}")
        print(f"  visible {exp['visible_points']} pts -> withheld {exp['withheld_points']} pts")
        print(f"  nRMSE  frozen(a)={exp['nrmse_frozen_a']:.4f}  "
              f"surrogate(s)={exp['nrmse_surrogate_s']:.4f}  baseline(c)={exp['nrmse_baseline_c']:.4f}")
        print(f"  Q = {exp['Q']:+.4f}      Q_surrogate = {exp['Q_surrogate']:+.4f}")
        print(f"  [exploratory] saturating baseline(c2)={exp['EXPLORATORY_nrmse_saturating_baseline_c2']:.4f}"
              f"  ->  Q vs c2 = {exp['EXPLORATORY_Q_vs_saturating_baseline']:+.4f}")

    print("\n=== PREREGISTERED KILL CONDITIONS ===")
    print(f"  K1 zero-point failure  (Exp0 Q > {K1_ZERO_POINT}) : {'FIRED' if k1 else 'clear'}")
    print(f"  K2 no transfer         (Exp1 Q <= 0)             : {'FIRED' if k2 else 'clear'}")
    print(f"  K3 surrogate parity    (Q_s >= {K3_SURROGATE_PARITY}*Q)          : {'FIRED' if k3 else 'clear'}")
    print(f"\n  Preregistered verdict: {'KILLED' if verdict['any_kill_fired'] else 'SURVIVES THIS PASS'}")

    # The preregistered baseline was found inadequate after run 1 (see
    # PREREGISTRATION.md amendment 1). Printing only the prereg verdict would
    # report a pass the evidence does not support, so the fair-baseline result
    # is surfaced at the same prominence rather than buried in the JSON.
    fair = exp1["EXPLORATORY_Q_vs_saturating_baseline"]
    print(f"  Fair-baseline check (exploratory): Q vs saturating baseline = {fair:+.4f}")
    if fair <= 0:
        print("  >> OVERRIDES THE ABOVE: frozen cross-domain shape LOSES to a 2-param")
        print("     saturating fit on D_C's own visible data. K2 fires on a fair baseline.")
        print("  >> ACTUAL VERDICT: NOT SUPPORTED on this triple.")
    print("  >> Exp1 domains are synthetic and share a generative family by")
    print("     construction; this triple carries no evidence about the world.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
