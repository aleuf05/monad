# Aegis Rigging — findings

Date: 2026-08-05
Scope: everything the rigging investigation established about this geometry
corpus. Written because the knowledge was spread across fifteen commit
messages, which is a poor index — you cannot find a number in them.

Action lives in the queue; truth lives here.

---

## 0. The corpus

Nine static assets, 4,454,579 vertices, no rigged assets at the start of the
day. All single-primitive — the multi-primitive limit in the solver never
bit and was never needed.

Every asset is heavily fragmented into disjoint shells:

| Asset | Vertices | Shells |
|---|---|---|
| `kraken_tripo_v1` | 1,076,978 | 1,831 |
| `the-monad` | 315,157 | 4,676 |
| `file_00000000a68c…` | 284,844 | 3,634 |
| `uss-rubber-ducky` | 282,840 | 1,764 |
| `end-to-end-manual` | 282,840 | 1,764 |
| `gasket` | 29,378 | 395 |
| `20260729T123905Z…` (mike-rocketry) | 28,586 | 133 |

Fragmentation is the corpus's defining property and drives most of what
follows.

## 1. Per-shell weighting eliminates pinching entirely

Packet Beta named weight bleeding across disjoint meshes as the failure mode
of proximity auto-weighting. The solver's answer: a shell whose axial span is
shorter than one bone span is bound **rigidly to one joint**. It moves as a
unit or not at all.

**Result: 0 collapsed, 0 inverted, 0 torn faces on gasket at every angle
tested (15°, 30°, 45°, 60°).** Max weight error 2.98e-8.

Caveat found later: on `the-monad`, the most fragmented asset, 3 inverted
faces appear at 15°. Small but not zero. The "zero inversion" claim is true
of gasket and was over-generalised to the corpus.

## 2. The collision metric was wrong, and most of the problem was imaginary

The deformation probe originally counted **any** pair of shell bounding
boxes that newly touched under pose. On gasket at 45° it reported 334
"collisions."

Measured by overlap *depth*: the median contact was **8% of the smaller
part's volume**, and only **28 pairs exceeded 50%**. On a bending articulated
model, adjacent parts legitimately approach each other — that is what
bending is. The metric was conflating articulation with clipping.

**Corrected baseline, gasket at 8 joints:**

| Bend | In contact | Genuinely interpenetrating |
|---|---|---|
| 15° | 160 | 9 |
| 30° | 261 | 18 |
| 45° | 334 | 28 |
| 60° | 399 | 33 |

The probe now reports `deep_clipping` separately, with contact as a
denominator rather than a defect count.

## 3. Shell grouping does not work — documented negative result

The obvious fix for inter-part collision was to group touching shells so
neighbours share a joint. It is implemented, tested, and **disabled by
default** (`ADJACENCY_FACTOR = 0.0`).

Why it fails: union-find is transitive, and in interlocking geometry one
chain of overlapping bounding boxes swallows everything. **Every epsilon
from 0.0005 to 0.04 collapsed all 395 shells into a single group.** Clipping
did not improve even then — 337 versus 334 — because a merged group that
still blends across joints still has relative motion.

A real attempt would need vertex-level proximity via a spatial grid, not box
overlap. Kept rather than deleted so nobody spends the same afternoon.

The degenerate case is pinned by
`test_solver.py::test_generous_epsilon_collapses_everything`, because a
single group scores *zero* collisions on a rig that no longer articulates —
and the original acceptance criteria would have called that a win.

## 4. Bone density controls deformability, not collision

Sweeping joint count on gasket:

| Joints | Rigid / blended shells | Interpenetrating |
|---|---|---|
| 4 | 395 / 0 | 9 |
| 8 | 374 / 21 | 9 |
| 12 | 310 / 85 | 9 |
| 16 | 257 / 138 | 10 |
| 24 | 166 / 229 | 11 |

More joints transforms how much of the mesh **can move** — from nothing to
most of it. It does nothing for collision and slightly worsens it. Two
independent problems; conflating them cost several hours.

## 5. The skeleton was the wrong shape on 7 of 9 assets

`solve_skeleton` picked the spine by longest bounding-box side. On gasket
that is the **arm span** — the robot's arms are outstretched, so it measures
1.00 wide and 0.68 tall — and the chain was threaded from the left hand,
through the chest, to the right hand.

The fit gate measures this directly: what fraction of mass sits more than
15% of span from the proposed spine. Above 35%, a single chain is the wrong
shape.

| Asset | Axis | Off-axis | Verdict |
|---|---|---|---|
| `end-to-end-manual` | Y | 84% | fail |
| `uss-rubber-ducky` | Y | 84% | fail |
| `file_00000000a68c…` | X | 83% | fail |
| `kraken_tripo_v1` | Z | 65% | fail |
| `gasket` | X | 58% | fail |
| `20260729T123905Z…` | Y | 18% | **pass** |
| `the-monad` | Y | 11% | **pass** |

**Choosing a better axis does not fix it.** Scoring all three axes by mass
changes the answer on exactly one asset of nine (`file_0000`, X→Z, 83%→77%,
still failing). Gasket's three axes score X 58%, Y 78%, Z 99% — X was
already the best available. There is no good single axis, because a robot is
not a chain at any orientation.

## 6. Branching skeletons — the fix, and its limit

Lobe-finding groups shells by centroid proximity. On gasket at radius 0.05
of span, six lobes appear with a 3.6× gap to the next, and they read as
anatomy:

| Lobe | Fraction | Reads as |
|---|---|---|
| 0.27 | | right track |
| 0.20 | | left track |
| 0.09 | | right shoulder |
| 0.08 | | left shoulder |
| 0.07 | | head / upper torso |
| 0.02 | | debris |

The radius is not tuned: at 0.12 the robot is one blob, at 0.02 it is 306
fragments, at 0.05 the anatomy appears.

The tree roots in the **most central** lobe, not the largest — the largest is
a track, and rooting a robot in its own foot gives a body that swings from
its ankle.

**Result:**

| Asset | Chain | Tree | |
|---|---|---|---|
| `gasket` | 58% off-spine | **22% off-bone** | pass |
| `the-monad` | 11% off-spine | 43% off-bone | **worse** |

The tree is much better on branching geometry and much worse on coherent
geometry. `the-monad` is one 95% lobe plus a 3% fragment — lobe-finding has
nothing to bite on, and the tree degenerates to a stub reaching for debris.

**So neither is the default.** `write_rigged(shape="auto")` asks the fit
gate, fits a tree only when the chain fails, and keeps it only when it
actually scores better. Corpus result: gasket → tree, the-monad → chain,
mike-rocketry → chain.

The tree carries a stronger anti-bleed rule than the chain: **a vertex may
only be influenced by joints of its own lobe, or by the root.** A track
cannot be pulled by a shoulder because a shoulder joint is not in its list.

## 7. Performance

Rust for the numeric kernels, Python for glTF I/O (doctrine 015). Measured:

| Asset | Vertices | Python | Rust | Speedup |
|---|---|---|---|---|
| `gasket` | 29,378 | 136 ms | 22 ms | 6.2× |
| `the-monad` | 315,157 | 1,515 ms | 228 ms | 6.6× |
| `kraken_tripo_v1` | 1,076,978 | 5,793 ms | 799 ms | 7.2× |

Whole corpus rigged and probed end to end in **35 seconds**.

## 8. What is still unknown

- **Interpenetration is unexplained.** `the-monad` passes the fit gate at
  11% and has 2,935 interpenetrating pairs — the worst in the corpus.
  `gasket` fails at 58% and has 9. Fit does not predict clipping.
  Fragmentation is the leading suspect and has not been tested.
- **Dual-quaternion vs linear blend** has never arisen — no rig in the
  corpus has a twisting joint.
- **Tree rigs are not in the corpus run.** `rig_corpus.py` still uses the
  chain path; only ad-hoc runs have exercised `shape="auto"`.
- **Deformation quality of the tree is unmeasured.** It scores better on
  fit. Whether it *deforms* better has not been probed.

## 9. Standing numbers

- 9 of 9 assets rig, 0 refusals, 0 errors
- Max weight error across all runs: 2.98e-8
- 23 solver tests, 6 Rust/Python parity tests, all green
- Rigged output is derived, not source: 373 MB, gitignored, regenerated
  byte-identically by `python3 tools/aegis-rig/rig_corpus.py 8`
