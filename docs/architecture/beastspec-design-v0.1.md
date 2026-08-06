# BeastSpec — Identity-Preserving Creature Design — Architecture Draft v0.1

- **Recorded:** 2026-07-30
- **Status:** Proposed architecture; not implemented. Design-only response to
  the Admiral's handoff packet.
- **Human direction:** Admiral supplied a compact BeastScape handoff packet
  naming the central engineering problem as *"preserve the recognizable
  identity of a creature while allowing its representation and form to
  mutate,"* and asked for a concrete, provider-agnostic MVP design: schema,
  decoder contracts, synthesis algorithm, versioning model, renderer
  compiler interface, evaluation format, UI flow, and one worked example.
- **AI contribution:** Captain expanded the packet into a schema-complete,
  modular design and reconciled it against the live Beastscape apparatus and
  the existing Live Captain Workbench job/capability pattern.

## Relationship to the existing Beastscape apparatus

This is a different research thread from the UMAP/Foundry work in
`docs/research/BEAST_STRUCTURAL_LATENT_SPACE_DRAFT_2026-07-29.md`, not a
replacement of it. That work charts a broad procedural *structural space*
(Open Ocean / Metameric Forge / Symbiotic Reef) and lets a human navigate
continuously through it — the question is "what does this region of
possibility-space contain." BeastSpec answers a different question: "does
*this specific creature* survive being re-rendered in five different ways."
One is exploration of a space; the other is fidelity of a point.

They can share substrate later — a BeastSpec's `morphology` block could be
seeded from a Foundry specimen's descriptor vector, and a Foundry region
could be described in `visual_language`/`invariant_traits` terms — but
nothing below assumes that convergence. This draft treats BeastSpec as its
own module so it does not become entangled with, or accidentally destabilize,
the live Foundry instrument.

BeastSpec's decoders and renderers are **Captain Workbench capabilities** in
the sense already defined in `docs/architecture/live-captain-workbench-v0.1.md`:
narrow named operations with input schema, cost class, timeout, and a human
gate, submitted as jobs and returned as receipts. This draft does not
reinvent a parallel job system — `D_i` and `G_j` below are workbench
capabilities (`beastspec.decode-morphology`, `beastspec.render-image`, etc.);
`B*` lives in workbench-adjacent durable storage the same way a job artifact
does.

## Core loop, restated as a system

```text
R (raw concept)
  |
  v  D_1..D_n  (decoder capabilities, run in parallel, independent)
{B_1..B_n}  (candidate BeastSpec fragments, each with confidence + provenance)
  |
  v  I  (synthesis — deterministic code, not a model call)
B*  (canonical BeastSpec, version 1)
  |
  v  G_1..G_m  (renderer/compiler capabilities, run in parallel)
{V_1..V_m}  (image / diagram / 3D / animation / sim / lore artifacts)
  |
  v  J  (human judgment — the only step with canon authority)
B'  (revised BeastSpec, version n+1, parent = B*)
  |
  (loop: B' becomes the next B* input to G, or back to D if the concept itself changes)
```

Two loop entry points exist and must stay distinguishable in the UI:
**re-render** (B* unchanged, only G runs again — e.g. a new art style) and
**re-derive** (R or a decoder input changes, D runs again, synthesis may
revise B*). Conflating them is how an aesthetic experiment quietly mutates
canon.

## BeastSpec JSON Schema

```json
{
  "$id": "monad.beastSpec.v0.1",
  "type": "object",
  "required": ["identity", "morphology", "invariant_traits", "flexible_traits",
               "forbidden_mutations", "provenance"],
  "properties": {
    "identity": {
      "type": "object",
      "required": ["id", "name", "version", "lineage"],
      "properties": {
        "id": {"type": "string", "description": "stable across all versions"},
        "name": {"type": "string"},
        "version": {"type": "integer", "minimum": 1},
        "lineage": {
          "type": "array",
          "items": {"type": "string"},
          "description": "ordered list of prior version ids, oldest first"
        }
      }
    },
    "invariant_traits": {
      "type": "array",
      "items": {"$ref": "#/$defs/trait"},
      "description": "must survive every G_j; renderer contract violation if absent"
    },
    "flexible_traits": {
      "type": "array",
      "items": {"$ref": "#/$defs/trait"}
    },
    "forbidden_mutations": {
      "type": "array",
      "items": {"type": "string"},
      "description": "plain-language rules a renderer/decoder output must not violate"
    },
    "morphology": {
      "type": "object",
      "properties": {
        "body_plan": {"type": "string"},
        "symmetry": {"type": "string"},
        "scale": {"type": "string"},
        "proportions": {"type": "string"},
        "appendages": {"type": "array", "items": {"type": "string"}},
        "surface_materials": {"type": "array", "items": {"type": "string"}},
        "internal_structure": {"type": "string"}
      }
    },
    "motion": {
      "type": "object",
      "properties": {
        "locomotion_modes": {"type": "array", "items": {"type": "string"}},
        "posture": {"type": "string"},
        "gait": {"type": "string"},
        "speed_range": {"type": "string"},
        "characteristic_movements": {"type": "array", "items": {"type": "string"}}
      }
    },
    "ecology": {
      "type": "object",
      "properties": {
        "habitat": {"type": "string"},
        "energy_source": {"type": "string"},
        "feeding_strategy": {"type": "string"},
        "predators": {"type": "array", "items": {"type": "string"}},
        "prey": {"type": "array", "items": {"type": "string"}},
        "symbioses": {"type": "array", "items": {"type": "string"}},
        "environmental_effects": {"type": "array", "items": {"type": "string"}}
      }
    },
    "behavior": {
      "type": "object",
      "properties": {
        "temperament": {"type": "string"},
        "social_structure": {"type": "string"},
        "sensory_model": {"type": "string"},
        "communication": {"type": "string"},
        "daily_cycle": {"type": "string"},
        "threat_response": {"type": "string"}
      }
    },
    "visual_language": {
      "type": "object",
      "properties": {
        "silhouette": {"type": "string"},
        "dominant_shapes": {"type": "array", "items": {"type": "string"}},
        "landmarks": {"type": "array", "items": {"type": "string"}},
        "texture": {"type": "string"},
        "palette": {"type": "array", "items": {"type": "string"}},
        "lighting_response": {"type": "string"}
      }
    },
    "world_constraints": {
      "type": "object",
      "properties": {
        "terrain_requirements": {"type": "string"},
        "climate": {"type": "string"},
        "spatial_footprint": {"type": "string"},
        "navigation_constraints": {"type": "string"},
        "interaction_rules": {"type": "array", "items": {"type": "string"}}
      }
    },
    "generation_constraints": {
      "type": "object",
      "properties": {
        "required_features": {"type": "array", "items": {"type": "string"}},
        "forbidden_features": {"type": "array", "items": {"type": "string"}},
        "flexible_features": {"type": "array", "items": {"type": "string"}},
        "renderer_specific_notes": {
          "type": "object",
          "additionalProperties": {"type": "string"}
        }
      }
    },
    "provenance": {
      "type": "object",
      "required": ["source_record", "decoder_outputs", "human_decisions"],
      "properties": {
        "source_record": {"type": "string", "description": "raw R, verbatim"},
        "decoder_outputs": {
          "type": "array",
          "items": {"$ref": "#/$defs/decoderOutputRef"}
        },
        "human_decisions": {
          "type": "array",
          "items": {"$ref": "#/$defs/humanDecision"}
        },
        "generated_artifacts": {
          "type": "array",
          "items": {"type": "string", "description": "artifact ids from G"}
        },
        "evaluation_history": {
          "type": "array",
          "items": {"type": "string", "description": "evaluation record ids"}
        }
      }
    }
  },
  "$defs": {
    "trait": {
      "type": "object",
      "required": ["field_path", "statement"],
      "properties": {
        "field_path": {
          "type": "string",
          "description": "dotted path into this BeastSpec, e.g. morphology.symmetry"
        },
        "statement": {"type": "string"},
        "source_decoder": {"type": "string"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1}
      }
    },
    "decoderOutputRef": {
      "type": "object",
      "required": ["decoder", "output_id", "confidence"],
      "properties": {
        "decoder": {"type": "string"},
        "output_id": {"type": "string"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "accepted_fields": {"type": "array", "items": {"type": "string"}},
        "rejected_fields": {"type": "array", "items": {"type": "string"}}
      }
    },
    "humanDecision": {
      "type": "object",
      "required": ["at", "kind", "note"],
      "properties": {
        "at": {"type": "string", "format": "date-time"},
        "kind": {
          "enum": ["invariant-promotion", "invariant-demotion",
                   "conflict-resolution", "variant-selection", "canon-approval"]
        },
        "note": {"type": "string"}
      }
    }
  }
}
```

Every `trait` carries `field_path` rather than living only as loose prose —
that is what lets synthesis and renderers programmatically ask "is this
field invariant" instead of re-parsing English.

## Decoder input/output contract

All seven decoders (`morphology`, `ecology`, `motion`, `silhouette`,
`behavior`, `world`, `strangeness`) share one contract shape; only their
`focus_fields` and prompt/heuristic differ. This is what makes the set
open — adding an eighth decoder means adding one config entry, not new
plumbing.

```json
{
  "$id": "monad.beastSpec.decoderInput.v0.1",
  "type": "object",
  "required": ["source_record", "decoder", "focus_fields"],
  "properties": {
    "source_record": {"type": "string"},
    "decoder": {"type": "string"},
    "focus_fields": {
      "type": "array",
      "items": {"type": "string"},
      "description": "BeastSpec field paths this decoder is responsible for"
    },
    "prior_spec": {
      "description": "B* from the previous iteration, if this is a re-derive",
      "type": ["object", "null"]
    }
  }
}
```

```json
{
  "$id": "monad.beastSpec.decoderOutput.v0.1",
  "type": "object",
  "required": ["decoder", "output_id", "proposed_fields", "confidence"],
  "properties": {
    "decoder": {"type": "string"},
    "output_id": {"type": "string"},
    "proposed_fields": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["field_path", "value", "confidence"],
        "properties": {
          "field_path": {"type": "string"},
          "value": {},
          "confidence": {"type": "number", "minimum": 0, "maximum": 1},
          "rationale": {"type": "string"}
        }
      }
    },
    "confidence": {
      "type": "number", "minimum": 0, "maximum": 1,
      "description": "overall decoder self-assessed confidence, not the synthesis operator's trust of it"
    },
    "flags": {
      "type": "array",
      "items": {"enum": ["ambiguous-source", "outside-focus-fields",
                          "conflicts-with-prior-invariant", "low-confidence"]}
    }
  }
}
```

A decoder never writes directly into `B*`. It only ever proposes
`decoderOutput` records; only synthesis writes the canonical spec. This is
the same discipline as the Workbench receipt model: a job produces evidence,
a separate accept step promotes it.

The **strangeness decoder** is structurally different from the other six: it
does not propose new fields, it *vetoes*. Its contract adds one field to
`decoderOutput`:

```json
{"objections": [{"field_path": "...", "reason": "generic-fantasy-collapse", "against_decoder": "morphology"}]}
```

Synthesis treats an objection as a required conflict to surface to the
human, never as something it silently overrides.

## Synthesis algorithm (`I`)

Synthesis is deterministic code, not a model call — the packet's warning
against "simple textual averaging" is best satisfied by making this step
inspectable and reproducible rather than another LLM pass. Pseudocode:

```text
function synthesize(prior_spec, decoder_outputs, human_priorities):
    proposals = flatten(decoder_outputs)  # one row per (field_path, value, decoder, confidence)
    groups = group_by(proposals, field_path)

    for field_path, group in groups:
        if len(distinct_values(group)) == 1:
            record AGREEMENT(field_path, value, decoders=group.decoders)
        else:
            record CONFLICT(field_path, candidates=group)

    objections = collect_objections(decoder_outputs, decoder="strangeness")
    for objection in objections:
        upgrade CONFLICT(objection.field_path) with a veto entry, or open one
        if the field wasn't already conflicted

    # Nothing here is auto-resolved. Auto-resolution is exactly the
    # "textual averaging" failure mode the packet warns against.
    if conflicts is non-empty:
        return SynthesisResult(status="unresolved-conflicts",
                                agreements=agreements, conflicts=conflicts)

    draft = apply(prior_spec or empty_spec, agreements)
    draft.invariant_traits = carry_forward(prior_spec.invariant_traits)  # never silently dropped
    return SynthesisResult(status="ready-for-review", draft=draft,
                            agreements=agreements)
```

`human_priorities` (from `θ` in the packet) is a small ranked list —
e.g. `["strangeness", "morphology", "ecology"]` — used only as a *display
order* for presenting conflicts, never to auto-pick a winner. Canon
promotion of a resolved conflict is always the `J` step below, recorded as
a `humanDecision`.

Minority proposals are not discarded at this stage: every candidate value in
a `CONFLICT` group remains visible in the returned `SynthesisResult` even
after the human picks one, because `provenance.decoder_outputs` retains all
of them. "Preserve minority proposals when distinctive and compatible" is
implemented as *never delete*, not as a scoring heuristic that tries to
guess compatibility algorithmically.

## Versioning model

- `identity.id` is stable for the creature's whole life; `identity.version`
  increments by exactly 1 on every canon promotion (never on a re-render).
- `identity.lineage` is the ordered list of ancestor version ids — append-only,
  same discipline as the Workbench's append-only job transitions.
- A version is immutable once promoted. A "revision" is always a new version
  object with `lineage` extended, never an in-place edit.
- `invariant_traits` can only move to `flexible_traits` (or vice versa)
  through a `humanDecision` of kind `invariant-demotion` /
  `invariant-promotion` — this is deliberately friction-full, since loosening
  an invariant is the one action that can silently destroy identity across
  future renders.
- Two versions can be diffed by field_path set difference; the diff itself is
  worth storing (`B*_n` → `B*_{n+1}` diff) so "what changed and why" survives
  independent of prose changelog discipline.

## Renderer / compiler interface (`G`)

One interface, many implementations — this is the seam that keeps the
design provider-agnostic per the packet's instruction.

```json
{
  "$id": "monad.beastSpec.rendererRequest.v0.1",
  "type": "object",
  "required": ["renderer_kind", "spec_id", "spec_version"],
  "properties": {
    "renderer_kind": {
      "enum": ["image", "diagram", "orthographic-3d", "mesh-constraints",
               "animation-rig", "simulation-params", "lore"]
    },
    "spec_id": {"type": "string"},
    "spec_version": {"type": "integer"},
    "style_directive": {"type": "string", "description": "the only thing that may legally vary a re-render"},
    "provider": {"type": "string", "description": "opaque adapter id, e.g. gemini-image, tripo, libfive"}
  }
}
```

Contract every renderer implementation must satisfy:

1. Compile only from `invariant_traits` + `flexible_traits` +
   `generation_constraints` + the fields in its own `renderer_specific_notes`
   entry — never from raw `source_record` directly (that would let a
   renderer silently reinterpret identity that decoders/synthesis already
   fixed).
2. Must not omit an invariant trait from its compiled prompt/constraint set;
   if a renderer's medium structurally cannot express a given invariant
   (e.g. a 2D silhouette can't show internal structure), it must say so in
   its receipt's `unexpressed_invariants` field rather than silently drop it.
3. Returns a `V_j` artifact plus a receipt in the existing Workbench receipt
   shape (`monad.captainWorkReceipt.v0.1`), extended with:

```json
{"unexpressed_invariants": ["internal_structure"], "spec_id": "...", "spec_version": 3}
```

This makes a renderer swap (new image model, new 3D backend) a matter of
writing one new adapter against the same request/receipt pair — nothing
upstream changes.

## Evaluation record format (`S(V,B)`)

```json
{
  "$id": "monad.beastSpec.evaluation.v0.1",
  "type": "object",
  "required": ["spec_id", "spec_version", "artifact_id", "scores", "weights", "total"],
  "properties": {
    "spec_id": {"type": "string"},
    "spec_version": {"type": "integer"},
    "artifact_id": {"type": "string"},
    "scores": {
      "type": "object",
      "properties": {
        "identity": {"type": "number", "minimum": 0, "maximum": 1},
        "morphology": {"type": "number", "minimum": 0, "maximum": 1},
        "ecology": {"type": "number", "minimum": 0, "maximum": 1},
        "physical": {"type": "number", "minimum": 0, "maximum": 1},
        "novelty": {"type": "number", "minimum": 0, "maximum": 1},
        "aesthetic": {"type": "number", "minimum": 0, "maximum": 1}
      }
    },
    "weights": {"type": "object", "additionalProperties": {"type": "number"}},
    "total": {"type": "number"},
    "evaluator": {"enum": ["human", "decoder-self-check"]},
    "invariant_violations": {
      "type": "array",
      "items": {"type": "string", "description": "field_path of a violated invariant"}
    },
    "note": {"type": "string"}
  }
}
```

`identity` is computed, not judged: `1 - (violated invariants / total
invariants)`. The other five scores are `evaluator: "human"` ratings in the
MVP; a `decoder-self-check` evaluator is a named but deferred extension
(would need its own bias-disclosure, not built here). `invariant_violations`
double-writes into `provenance.evaluation_history` on the spec so a spec's
page can show "3 of 5 renders preserved identity" without recomputation.

## Minimal UI flow

1. **Compose** — human enters `R` (text; sketch/image upload deferred).
2. **Decode** — the seven decoders run as parallel Workbench jobs; UI shows
   each job's state (queued → running → done) independently, not a single
   spinner. `strangeness` is visually distinguished since it can only object.
3. **Review synthesis** — UI shows agreements (collapsed by default) and
   conflicts (expanded, one per field_path, candidate values side by side
   with source decoder + confidence). Human resolves each conflict with one
   click; unresolved conflicts block promotion.
4. **Declare traits** — human-editable three-column view
   (invariant / flexible / forbidden) seeded from decoder proposals but
   always human-editable before first promotion.
5. **Promote** — writes `B*` version 1, immutable from here.
6. **Render** — human picks one or more `renderer_kind`s + optional
   `style_directive`; jobs run in parallel; each returns a `V_j` with its
   receipt inline (including any `unexpressed_invariants`).
7. **Evaluate & select** — human scores each `V_j` (or accepts a default of
   "not evaluated"); marks 0+ as favorites. This is `J`.
8. **Revise** — "propose revision" reopens step 1 pre-filled with `B*` as
   `prior_spec` plus the human's notes on what should change; produces `B'`
   as version n+1 once promoted. A revision must state whether it's a
   re-render (no new version) or re-derive (new version) before running —
   the UI should make the wrong choice hard, not just possible to correct.

Non-goals for the MVP UI: no multi-user concurrent editing, no automatic
scheduling of re-renders, no push notifications — this is a workbench, not a
product surface, consistent with the research-apparatus ruling already
governing Beastscape.

## Worked example — "Tideglass Warden"

**R (raw record):**
> "A slow, six-legged reef guardian built like drifting glass. Its shell is
> transparent and shows the tide moving inside it. One eye, suspended in the
> center, never blinks. It doesn't attack — it just gets between you and the
> nest."

**Decoder outputs (abridged, confidence in parens):**

- `morphology` (0.82): `body_plan="radial, shell-enclosed"`,
  `symmetry="radial"`, `appendages=["six load-bearing legs"]`,
  `internal_structure="visible fluid chamber, tide-synced"`.
- `motion` (0.74): `gait="slow deliberate hexapod"`,
  `characteristic_movements=["interposes between threat and nest"]`.
- `silhouette` (0.9): `silhouette="dome shell over six thin legs, one central orb"`,
  `landmarks=["suspended central eye"]`.
- `behavior` (0.71): `temperament="non-aggressive, blocking"`,
  `threat_response="body-blocks, does not attack"`.
- `ecology` (0.65): `habitat="reef nest perimeter"`,
  `feeding_strategy="unspecified — flag for human"` (low confidence).
- `world` (0.6): `spatial_footprint="wide, low"`, `navigation_constraints="slow; herds around a fixed nest point"`.
- `strangeness` (0.88): objection: none raised — flags
  `["do not let renderers add facial features besides the one eye"]`
  as a forbidden-mutation candidate.

**Synthesis:** all seven agree on `symmetry=radial`, `eye_count=1`,
`gait=slow`, `threat_response=non-aggressive/blocking` → agreements. One
conflict: `ecology.feeding_strategy` has only one low-confidence candidate
vs. no competing proposal — synthesis still routes it to the human as
`status: needs-input` rather than guessing.

**Human resolution:** sets `feeding_strategy="filter-feeds tidal debris"`,
promotes traits:
- **invariant:** radial six-leg shell body plan; single unblinking suspended
  central eye; slow deliberate gait; non-aggressive blocking threat response;
  transparent shell showing internal tide motion.
- **flexible:** shell color/tint, leg length, nest terrain, exact tide
  pattern inside the shell.
- **forbidden:** bilateral symmetry, additional eyes or facial features,
  aggressive attack behavior, opaque shell.

`B*` v1 promoted.

**Render:** `image` (field concept-art style), `silhouette` (monochrome),
`diagram` (anatomical) all requested. The `diagram` renderer's receipt sets
`unexpressed_invariants: []` (it can show the fluid chamber); a
low-poly-3D renderer, if run, would be expected to report
`unexpressed_invariants: ["visible fluid chamber, tide-synced"]` unless it
implements a translucent shell material.

**Evaluate:** human scores the image variant `identity=1.0` (no invariants
violated), `aesthetic=0.8`; rejects a second image variant that gave it a
second eye — `identity` auto-computes to `0.8` (1 of 5 invariants violated)
regardless of how good it looked, which is the point of separating
`identity` from `aesthetic`.

**Revise:** human requests a `B'` that adds a bioluminescent variant of the
tide fluid as a new flexible trait — re-derive path, `B*` → v2.

## MVP acceptance boundary

Following the same discipline as the Workbench draft's acceptance section —
the pattern isn't proven merely because one creature got one nice image:

- a second, unrelated creature concept can go through the full loop without
  code changes, only new decoder/renderer config;
- a conflict a decoder set disagrees on is never auto-resolved without
  appearing to the human first;
- an invariant trait, once promoted, cannot be silently dropped by any
  renderer — violation is measurable (`identity` score) not just anecdotal;
- version lineage survives a restart the same way Workbench job state does;
- swapping one renderer's underlying provider requires touching only that
  renderer's adapter, nothing upstream.

## Explicitly deferred

- Sketch/image input to decoders (packet's `R` is text-first for MVP).
- `decoder-self-check` automated evaluation.
- Any convergence with the Foundry/UMAP structural-space work — a real
  question, not resolved here.
- Multi-creature world-placement interactions (`world_constraints` is
  captured per-creature only; cross-creature ecology is out of scope).
- Auto-scheduling or batch re-rendering.
