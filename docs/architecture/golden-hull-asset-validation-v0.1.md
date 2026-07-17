# GOLDEN HULL Asset Validation V0.1

Priority: Medium

Scope: Manifest/pipeline hardening only. No FleetCore integration, no
automatic real-world-scale inference.

Doctrine: §16's invariant — "visual assets may not silently redefine
simulation dimensions" — had no enforcement anywhere. Confirmed absent
twice this session (`docs/reports/2026-07-15-feature-matrix.md`'s `GH-01`
row, and a fresh re-check before starting this work): `validate_glb()`
already checked format/texture presence, but nothing checked scale,
collision envelope, orientation, or recorded a real version.

## What "silently redefine dimensions" actually means here

A generated or manually-uploaded `.glb` has no inherent real-world scale —
glTF itself has no mandated unit. Before this order, `manifest.json`
recorded a file path and a timestamp and nothing else; a model could be
30cm or 300m relative to the simulated fleet and nobody would know until
it visibly clipped through something. The fix isn't inferring a "true"
scale automatically — that's not knowable from geometry alone — it's
making the scale claim **explicit and recorded**, with three distinct
states instead of one silent void:

1. A real declared number (`declared_scale_meters: 42.5`).
2. An explicit acknowledgment that it's unknown (`scale_declared_unknown: true`)
   — a deliberate "we checked and don't know," not silence.
3. Neither — which is now a loud `WARNING` at catalog time and a visible
   "Not declared" state in Asset Viewer, not a blank field nobody notices.

## V0.1 decomposition

### 1. Bounding box — computed, not assumed

`compute_bounding_box()` in `tools/img2asset/image_to_asset.py` unions the
`min`/`max` of every POSITION accessor referenced by any mesh primitive.
glTF 2.0 requires POSITION accessors to carry `min`/`max`, so this is read
directly off the file's own JSON chunk (already-parsed via the refactored
`read_gltf_json()`, shared with the pre-existing `validate_glb()`), never
estimated. Recorded in the manifest as `bounding_box: {min, max,
dimensions}`, in whatever local units the GLB itself uses.

### 2. Orientation — soft heuristics, never blocking

`check_orientation()` flags two real patterns, both confirmed against the
4 real GLBs already in this repo's manifest before writing the heuristics
(not designed in the abstract): a dimension that's zero or near-zero
relative to the largest (flat/billboard geometry), and a largest dimension
that isn't on the Y axis (glTF's Y-up convention would expect height to
dominate for an upright model — not necessarily wrong, e.g. for a
horizontal hull, but worth a human glance). One real finding surfaced
immediately: `file_00000000a68c722f9cd29e1996dba4cf.glb`'s largest
dimension is X, not Y — previously unflagged.

### 3. Version — a real integer, not a timestamp comparison

Every manifest write now increments `version` for that model name (1 on
first catalog, +1 on every re-catalog/audit), instead of relying on
`created_at` string comparison to tell revisions apart.

### 4. Explicit scale declaration

New CLI flags on `image_to_asset.py`: `--scale-meters <float>` (a real
declared number) and `--scale-unknown` (explicit acknowledgment),
mutually exclusive. Neither is required — this doesn't break existing
callers (`serve.py`'s HTTP trigger behind Asset Viewer's upload flow still
works with neither, same as before) — but omitting both now produces a
visible `WARNING` at catalog time instead of silence.

### 5. Backfilling what already existed

`tools/img2asset/audit_existing_assets.py` is a separate script (not a mode
of `image_to_asset.py`, since re-auditing an asset already in place is a
different operation from copying a new source file in — the original CLI's
`shutil.copy()` refuses to copy a file onto itself) that re-reads every
already-cataloged GLB, computes real `bounding_box`/`orientation_warnings`,
and bumps `version`. Run once against all 4 real models in this repo with
`--acknowledge-unknown` (an honest choice — their true real-world scale
genuinely isn't known, and guessing a plausible-sounding number would be
worse than an acknowledged unknown) plus `--scale NAME=METERS` support for
declaring a real one later. `manifest.json` bumped to
`schema_version: monad.assetManifest.v2` (additive fields only, nothing
removed or renamed — existing readers of `name`/`glb_path`/`backend`/etc.
are unaffected).

### 6. Visible on the live page

Per this project's "if the Lt. can't see it, it doesn't exist" policy,
`toys/asset-viewer/`'s detail panel now shows Version, Real-World Scale
(distinguishing all three states above), Bounding Box, and an amber
warning block for any orientation findings — not buried in JSON. Verified
live via Playwright: the one model with a real orientation finding shows
the warning; the other three correctly show no warning block.

## Deferred (explicitly not in V0.1)

- **Automatic real-world scale inference.** Not knowable from geometry
  alone without a reference object or human input — deliberately requires
  an explicit human declaration (or explicit "unknown"), not a computed
  guess.
- **Collision envelope beyond the AABB.** The bounding box *is* a basic
  collision envelope; a tighter convex-hull or per-triangle envelope is
  real future work but adds a geometry-processing dependency this pass
  doesn't need.
- **FleetCore runtime-identity linkage** (associating a `.glb` with a
  specific vessel/contact ID). This pipeline is deliberately
  FleetCore-independent ("Contracts-only: this tool never touches
  FleetCore or World state" — the module's own original docstring); adding
  a live link would cross that boundary and needs its own decision.
- **Asset Viewer upload-form UI for `--scale-meters`.** The backend/CLI
  contract supports it now; wiring a form field into the upload flow is a
  small, separate follow-up, not required to close the invariant gap in
  the manifest and pipeline themselves.

## Done evidence

`compute_bounding_box()`/`check_orientation()` run against all 4 real GLBs
already in `web/assets/models/`, not fixtures — real dimensions recorded,
one real orientation finding surfaced that nothing previously flagged.
Forward path (`image_to_asset.py --backend manual --scale-meters 42.5`)
verified against a temp copy, producing a correct `declared_scale_meters:
42.5` entry, then cleaned up (not part of the real catalog). Mutual
exclusivity of `--scale-meters`/`--scale-unknown` enforced. `serve.py`'s
existing call into `run_pipeline()` confirmed unaffected (new params are
keyword-only with backward-compatible defaults). Verified live at
`https://cameronlampley.com/toys/asset-viewer/` via Playwright: Version,
Scale, and Bounding Box render for every model, and the one model with a
real orientation warning shows it while the other three correctly don't.
