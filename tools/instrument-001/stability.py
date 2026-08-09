#!/usr/bin/env python3
"""Instrument 001 -- stability study.

The first test run reported point estimates from a single seed. A single draw
cannot distinguish "the instrument has a zero point" from "that seed happened
to land below threshold." This replaces every headline number with a
distribution over seeds, and replaces the asserted zero point with a measured
**false-positive rate**.

Three things this adds that the first run could not do:

1. **Replication.** N seeds per configuration. Q becomes a distribution with a
   median and an interquartile range, and "detection" becomes a rate.
2. **Multiple null triples.** One null triple tests one null. A false-positive
   rate needs several structurally different ways of having no shared
   structure -- flat noise, a trend, a decay, a walk.
3. **A fairer honest triple.** The first honest triple generated D_B and D_C
   from the same formula, so it tested nothing. H2 below sends the frozen
   shape to a *different* saturating family (Gompertz), which is what
   cross-family transfer would actually have to survive.

Baseline policy follows PREREGISTRATION.md amendment 1: the saturating
baseline is primary, the original power law is reported only for continuity
with the first run. The surrogate-beats-baseline check is promoted here to a
hard precondition -- when it trips, Q is suppressed rather than reported.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import random
import statistics
import sys
import traceback
from pathlib import Path

P = Path(__file__).with_name("instrument.py")
S = importlib.util.spec_from_file_location("instrument", P)
inst = importlib.util.module_from_spec(S)
sys.modules[S.name] = inst  # required before exec_module: instrument.py has a @dataclass
S.loader.exec_module(inst)

Domain = inst.Domain
U_GRID = inst.U_GRID


# ---------------------------------------------------------------------------
# Additional domains. The first run had one null triple and one rigged honest
# triple; neither supports a rate.
# ---------------------------------------------------------------------------

def white_noise(rng, n=60) -> Domain:
    return Domain("white_noise", [float(i + 1) for i in range(n)],
                  [50.0 + rng.gauss(0, 10) for _ in range(n)], "stationary noise")


def linear_trend(rng, n=60) -> Domain:
    return Domain("linear_trend", [float(i + 1) for i in range(n)],
                  [10.0 + 2.0 * i + rng.gauss(0, 3) for i in range(n)], "unbounded linear growth")


def exp_decay(rng, n=60) -> Domain:
    return Domain("exp_decay", [float(i + 1) for i in range(n)],
                  [200.0 * math.exp(-0.05 * i) + rng.gauss(0, 1) + 5.0 for i in range(n)],
                  "exponential decay")


def sawtooth(rng, n=60) -> Domain:
    return Domain("sawtooth", [float(i + 1) for i in range(n)],
                  [20.0 + 15.0 * ((i % 12) / 12.0) + rng.gauss(0, 1) for i in range(n)],
                  "periodic sawtooth")


def gompertz_curve(rng, n=60) -> Domain:
    """A saturating curve from a DIFFERENT family than the hyperbola used for
    D_B. Asymmetric approach to the asymptote -- this is the honest test of
    whether a frozen shape transfers across functional families, not just
    across parameter values of one family."""
    K, b, c = 0.75, 2.5, 0.00035
    xs = [20000.0 * i / (n - 1) for i in range(n)]
    ys = [K * math.exp(-b * math.exp(-c * x)) * inst._noise(rng, 0.02) for x in xs]
    return Domain("gompertz_scaling", xs, ys, "Gompertz saturation, different family from D_B")


TRIPLES = {
    # name: (kind, D_A factory, D_B factory, D_C factory)
    "N1_precip_zipf_walk": ("null", inst.precipitation_null, inst.zipf_null, inst.random_walk_null),
    "N2_noise_saw_walk": ("null", white_noise, sawtooth, inst.random_walk_null),
    "N3_decay_trend_walk": ("null", exp_decay, linear_trend, inst.random_walk_null),
    "N4_walk_walk_walk": ("null", inst.random_walk_null, inst.random_walk_null, inst.random_walk_null),
    "H1_rigged_same_family": ("honest", inst.logistic_growth, inst.queue_saturation, inst.scaling_curve),
    "H2_cross_family_gompertz": ("honest", inst.logistic_growth, inst.queue_saturation, gompertz_curve),
}


# ---------------------------------------------------------------------------
# One trial. Returns Q against both baselines, plus the precondition verdict.
# ---------------------------------------------------------------------------

def saturating_baseline(vis_x, vis_y, hid_x, hid_y):
    """Two-parameter saturating fit on D_C's visible data only. Same inductive
    bias as the frozen arm, zero cross-domain information. This is the
    baseline that matters (amendment 1)."""
    shape = [u / (1.0 + u) for u in U_GRID]
    K, tau = inst.fit_frozen(shape, vis_x, vis_y)
    pred = [K * ((x / tau) / (1.0 + x / tau)) for x in hid_x]
    return inst.nrmse(pred, hid_y)


def trial(name, seed) -> dict:
    kind, fa, fb, fc = TRIPLES[name]
    rng = random.Random(seed)
    d_a, d_b, d_c = fa(rng), fb(rng), fc(rng)

    cut = int(0.3 * len(d_c.xs))
    vis_x, vis_y = d_c.xs[:cut], d_c.ys[:cut]
    hid_x, hid_y = d_c.xs[cut:], d_c.ys[cut:]

    shape = inst.derive_shape(d_a, d_b)
    K, tau = inst.fit_frozen(shape, vis_x, vis_y)
    err_a = inst.nrmse([K * inst.interp(U_GRID, shape, x / tau) for x in hid_x], hid_y)

    shape_s = inst.derive_shape(inst.surrogate(d_a, rng), inst.surrogate(d_b, rng))
    Ks, ts = inst.fit_frozen(shape_s, vis_x, vis_y)
    err_s = inst.nrmse([Ks * inst.interp(U_GRID, shape_s, x / ts) for x in hid_x], hid_y)

    a, b = inst.fit_powerlaw(vis_x, vis_y)
    err_pl = inst.nrmse([a * (x ** b) if x > 0 else a for x in hid_x], hid_y)
    err_sat = saturating_baseline(vis_x, vis_y, hid_x, hid_y)

    # Promoted precondition: if the structure-destroyed arm beats the
    # baseline, the baseline is broken and Q is not interpretable.
    gate_tripped = err_s < err_sat

    return {
        "triple": name, "kind": kind, "seed": seed,
        "nrmse_frozen": err_a, "nrmse_surrogate": err_s,
        "nrmse_baseline_powerlaw": err_pl, "nrmse_baseline_saturating": err_sat,
        "Q_fair": err_sat - err_a,          # primary
        "Q_legacy_powerlaw": err_pl - err_a,  # continuity with run 1 only
        "surrogate_gate_tripped": gate_tripped,
    }


def summarize(rows, key) -> dict:
    vals = sorted(r[key] for r in rows)
    n = len(vals)
    if n == 0:
        return {}
    q = lambda p: vals[min(n - 1, max(0, int(p * (n - 1))))]
    return {
        "n": n,
        "median": round(statistics.median(vals), 5),
        "iqr_lo": round(q(0.25), 5), "iqr_hi": round(q(0.75), 5),
        "min": round(vals[0], 5), "max": round(vals[-1], 5),
        "frac_positive": round(sum(1 for v in vals if v > 0) / n, 4),
        "frac_above_0.05": round(sum(1 for v in vals if v > 0.05) / n, 4),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Instrument 001 stability study")
    ap.add_argument("--seeds", type=int, default=200)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    rows, failures = [], []
    for name in TRIPLES:
        for k in range(args.seeds):
            seed = 20260809 + k
            try:
                rows.append(trial(name, seed))
            except Exception:
                failures.append({"triple": name, "seed": seed,
                                 "error": traceback.format_exc().strip().splitlines()[-1]})

    out = {"seeds_per_triple": args.seeds, "total_trials": len(rows),
           "harness_failures": failures, "by_triple": {}}

    for name, (kind, *_ ) in TRIPLES.items():
        sub = [r for r in rows if r["triple"] == name]
        if not sub:
            continue
        out["by_triple"][name] = {
            "kind": kind,
            "Q_fair": summarize(sub, "Q_fair"),
            "Q_legacy_powerlaw": summarize(sub, "Q_legacy_powerlaw"),
            "surrogate_gate_trip_rate": round(
                sum(1 for r in sub if r["surrogate_gate_tripped"]) / len(sub), 4),
        }

    nulls = [r for r in rows if r["kind"] == "null"]
    if nulls:
        out["false_positive_rate"] = {
            "definition": "fraction of null-triple trials with Q_fair > 0.05 (K1 threshold)",
            "rate": round(sum(1 for r in nulls if r["Q_fair"] > 0.05) / len(nulls), 4),
            "n_null_trials": len(nulls),
            "rate_any_positive": round(sum(1 for r in nulls if r["Q_fair"] > 0) / len(nulls), 4),
        }

    if args.json:
        print(json.dumps(out, indent=2, sort_keys=True))
        return 0

    print(f"\nInstrument 001 stability study -- {args.seeds} seeds x {len(TRIPLES)} triples "
          f"= {len(rows)} trials")
    print(f"harness failures: {len(failures)}")
    print(f"\n{'triple':<28} {'kind':<7} {'Q_fair median':>14} {'IQR':>20} {'det.rate':>9} {'gate':>6}")
    print("-" * 92)
    for name, s in out["by_triple"].items():
        q = s["Q_fair"]
        print(f"{name:<28} {s['kind']:<7} {q['median']:>14.4f} "
              f"{('[%.3f, %.3f]' % (q['iqr_lo'], q['iqr_hi'])):>20} "
              f"{q['frac_positive']:>9.1%} {s['surrogate_gate_trip_rate']:>6.1%}")

    if "false_positive_rate" in out:
        fp = out["false_positive_rate"]
        print(f"\nFALSE POSITIVE RATE (null trials, Q_fair > 0.05): "
              f"{fp['rate']:.1%}  (n={fp['n_null_trials']})")
        print(f"  any positive Q on a null triple:                {fp['rate_any_positive']:.1%}")

    h2 = out["by_triple"].get("H2_cross_family_gompertz", {}).get("Q_fair", {})
    if h2:
        print(f"\nCross-family transfer (H2, the honest test): median Q_fair = {h2['median']:+.4f}, "
              f"positive on {h2['frac_positive']:.1%} of seeds")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
