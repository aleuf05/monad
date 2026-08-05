# Aegis-Monad Packet Beta — Procedural Rigging Solver Specification

Date: 2026-08-05
Source: Lt. cgl (Admiral), direct chat message.
Epistemic label: **design specification, unimplemented** — a spec for a
3D character-rigging pipeline. No rigging code exists in this repo, and
no riggable geometry exists either (verified below).

## Summary of content

Same four-module template as `AEGIS-MONAD_PRODUCTION_BUILD`, applied to
procedural rigging:

1. **Skeletal Topology Solver** — builds bone hierarchies from semantic
   anchors (`@Root`, `@Head`, `@Spine`, limbs) as a DAG of joints with
   parent-child transforms and rest-pose orientations; rejects chains
   that violate anatomical constraints or invert transformations. Rust
   sketch (`SkeletalSolver::construct_rig`, `verify_acyclic`).
2. **Automated Skinning & Weight Assignment** — vertex-to-bone influence
   weights via linear blend or dual-quaternion skinning, avoiding
   geometry tearing and weight bleeding across disjoint meshes.
   Validates weight sums = 1.0.
3. **Procedural Weight Isolation & Quenching** — new heuristic or ML
   weighting scripts sandboxed against test geometry to detect clipping
   and pinching before integration; Admiral sign-off gate.
4. **Rigging Provenance & Telemetry** — per-pass audit trail linking
   source mesh to rigged asset: weight deltas, joint offsets, parent
   mesh hash.

Closes with the four-item sign-off checklist, all marked complete.

## My read

### The domain content is genuinely competent

Worth separating from the template it arrives in. The technical concerns
named are the real ones, and correctly named:

- **Weight sums = 1.0** is the actual invariant that breaks skinning
  when violated.
- **Weight bleeding across disjoint meshes** is a specific, real failure
  in proximity-based auto-weighting, and naming disjointness as the
  trigger is precise.
- **Linear blend vs dual-quaternion** is the correct axis of choice, and
  the reason (candy-wrapper collapse at twisted joints) is implied by
  putting it next to "tearing."
- **DAG acyclicity** is the right structural check for a joint
  hierarchy.
- **Clipping and pinching** are the artifacts a deformation test should
  actually look for.

Whoever wrote this has done rigging. That is a different and better
signal than the previous pack gave, and it stands on its own regardless
of what happens to the rest.

### What does not exist

Verified directly, not assumed:

- `find . -iname "*.glb"` — 9 files. Every one parsed: **0 skins, 0
  animations, 1 node each.** They are static single-node meshes. There
  is no skeleton, no armature, and no rigged asset anywhere in the repo.
- No rigging, skinning, bone, or armature code under `tools/` (the only
  grep hits were vendored scipy/numba test files under a `.venv`).
- No Rust toolchain in use anywhere in this Python repo.

So Packet Beta specifies a solver for geometry that does not currently
exist in a form it could act on. That is not fatal for a specification —
specs precede their inputs — but it does mean "build this" is not yet a
coherent instruction, and it puts the checklist below in sharper relief.

### The checklist, again

Four items marked `[x]` complete, including **"Novelty Isolated: Sandbox
quarantine active for all heuristic weight solvers."** No sandbox
exists, no weight solver exists, and no geometry exists for one to run
against. Filed as the document's claim about itself; confirms nothing.

Second occurrence of the identical pattern in as many packs. Recorded as
a pattern now rather than an isolated defect: **the sign-off checklist
in this template appears to be part of the template rather than a
statement about the work.** If that is what it is, it would be better
removed than carried, because a reader who does not know it is boilerplate
will read "quarantine active" as a safety guarantee.

### What this does to `MSIR-M3-Q2`

Q2 asked what `D_t` is: documents (A), generated operator code (B), two
separate systems (C), or something else (D).

**Packet Beta is strong evidence for D: 3D assets.** Its operators
operate on meshes, skeletons, and vertex weights — not documents, and
not generic operator code. That is more information about the intended
object than the query itself has drawn out so far.

It is not recorded as the answer. The same restraint applied when
declining to infer **B** from the first pack's Module 3 applies here:
inferring **D** from a second pack would be the same mistake with a
different letter. Q2 stays open, and the Admiral has been asked to
confirm rather than have it read into the record.

If confirmed as D, the practical consequence is significant and worth
stating in advance: M³ cycle v0.1 was built against **A**, and would not
transfer. `Cont`, `V`, and `Q_rev` over a mesh corpus are different
predicates entirely — identity is topological, not titular; recoverability
is not `git checkout`; and the valuation would have to measure something
like deformation quality rather than link resolvability. The existing
cycle would remain valid over documents and simply not be the same system.

## Filing note

Filed as a design specification. No implementation started. `MSIR-M3-Q2`
remains open; pause holds.
