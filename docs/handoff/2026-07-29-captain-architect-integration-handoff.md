# Handoff: Captain–Architect session -> integrating Captain

Date: 2026-07-29
Branch: `agent/living-world-intake-v0-1`
HEAD at time of writing: `4b23774cc661b5ede50eaa4e928a17a7d163ef8e`
Working tree: clean (apart from `web/data/*.json`, which are pre-existing
live-service-generated snapshots, unrelated to this work, deliberately
untouched throughout)

This is the single point of discovery for this session's work. Read this
file first; it links to everything else rather than repeating it.

## What this session was

Appointed provisional "Captain–Architect" via a Context Transplant packet
on 2026-07-28. Produced two things: (1) a small, real, tested engineering
artifact (IntentForge v0.0), and (2) the discovery that a separate,
already-running Captain-CLI thread exists on this same branch, which this
session was not coordinating with until found via `git log` archaeology.

## 1. IntentForge v0.0 — `intentforge/`

**Status:** committed, working, tested, not yet claimed by anyone else.

- Start here: `intentforge/README.md` (has its own "Absorption note").
- What it does: `intentforge/demo_fan_bracket.py` takes a structured
  Design Intent Contract (`intentforge/design_intent.py`) for a flat
  bracket (fan mount + existing holes + cable keep-out), generates a
  watertight solid via a hand-written extrusion/triangulation engine
  (`intentforge/mesh.py`, `intentforge/bracket_generator.py`), and writes
  a real binary STL to `intentforge/output/`.
- **Test status:** `cd intentforge && python3 -m unittest
  test_bracket_generator.py -v` — 8/8 passing at last run (2026-07-29).
- **Why pure Python instead of this repo's real libfive backend:**
  `python3 tools/libfive/generate.py status` reports `installed: false`
  on this machine (no exporter binary, no source checkout) — verified,
  not assumed. Writing CSG script against a kernel that can't be run or
  checked here would have been an unverified claim. See
  `intentforge/README.md`'s "Growth path" for the intended eventual swap.
- **Real bugs found and fixed during development** (both now pinned by
  tests, so they can't silently regress): an `is_watertight()` check that
  compared vertex *indices* instead of coordinates (structurally could
  never pass); a hole-wall triangle-winding bug that added volume instead
  of subtracting it (caught by cross-checking the mesh's computed volume
  against an independent hand calculation — off by ~4000mm³ until fixed).
- **Explicitly not core Monad tech** — not under `web/`'s deploy policy,
  lives here for convenience only (Lt. cgl's ruling, 2026-07-28).
- **Not done:** only one part family exists (flat plate + circular holes
  + one edge notch); no natural-language intake; no revision loop; no
  STEP export; nothing physically manufactured or tested (and won't be —
  no printer, simulation-only per standing instruction, 2026-07-29).

## 2. Role/Implementation friction findings — `docs/engineering-orders/CAPTAIN-CLI-ROLE-IMPLEMENTATION-0.1.md`

**Status:** committed. Friction inventoried, smallest reversible next step
proposed, **not built**.

- Concrete friction found (file:line evidence, not assumption): Living
  Captain and the voice engine already have provider-neutral interfaces
  (`ModelProvider`/`Provider` `Protocol`s) but are policy-pinned to Gemini
  by `docs/doctrine/model-api-routing.md`; `legend-pipeline` and
  `cloud-image-demo` have no such seam at all (a real, not just policy,
  binding).
- **Proposed, not built:** `docs/architecture/role-registry.md` — one row
  per role, naming current occupant(s) and whether each binding is
  technical or policy. Zero code change, fully reversible. This is the
  natural next artifact for whoever takes over both halves — it's the
  shared ledger that would have made the discovery in section 3 below
  unnecessary.

## 3. The other Captain-CLI thread — discovered, not reconciled

A separate, already-running thread has been committing to this same
branch throughout 2026-07-28/29, with no live coordination channel to
this session — only found via `git log` (commits `e962d21`, `0cc015d`,
`48fc4f3`, and others). It has:

- its own doctrine: `docs/research/TRUTH_SESSION_V1_DRAFT_2026-07-28.md`,
  section "Product-direction hypothesis: Integrated Captain CLI" (a
  5-stage adoption path: Instrument -> Workbench -> Steward -> Crew
  substrate -> Default);
- shipped real Monad-core features under it: Scientific Claim Laboratory
  (`docs/engineering-orders/packets/SCIENTIFIC-CLAIM-LAB-0.1.md`),
  Geometric Language Laboratory
  (`docs/engineering-orders/packets/GEOMETRIC-INTENT-LANGUAGE-LAB-0.1.md`).

**Assessment on first reading (not exhaustively verified):** the two
doctrine documents are complementary, not contradictory — theirs is a
conversational epistemics protocol (observed/inferred/unknown/next-step
for human<->Captain exchanges), this session's is engineering role
architecture (role vs. occupant). No actual conflict found to escalate.
Full addendum: the note appended to
`CAPTAIN-CLI-ROLE-IMPLEMENTATION-0.1.md` on 2026-07-29.

## What the integrating Captain should probably do first

1. Build `docs/architecture/role-registry.md` (proposed in section 2) —
   the coordination artifact both threads should have had from the start.
2. Read `TRUTH_SESSION_V1_DRAFT_2026-07-28.md` in full (this session only
   sampled it) before treating the "complementary, not contradictory"
   read above as settled.
3. Decide whether IntentForge (section 1) gets folded into whatever this
   integration produces, or stays a deliberately separate, non-core
   track — the role/implementation doctrine doesn't require one answer;
   it requires the decision to be visible once made.
4. Route future Captain-role work through `docs/engineering-orders/queue.md`'s
   existing claim protocol (`AGENTS.md`) instead of silent parallel
   commits — it already exists for exactly this and is currently unused
   for this purpose.

## What was deliberately not done

- No merge of the two doctrine drafts performed unilaterally.
- No role-registry built (proposed only).
- No IntentForge work claimed as integrated with the other thread.
- No physical manufacturing, testing, or simulation beyond geometry
  generation.
