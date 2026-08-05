# Ultra-Rich Text / Full-Custom Visual Language — Design Conference Brief

Date: 2026-08-03
Prepared for: design conference with the Captain, following the Admiral's
request to research the maximally fancy end of the rich-text spectrum for
Document Viewer + Live Captain (no filtering for practicality yet -- that
triage happens at the conference, not before it).

Context: a grounded first pass already shipped to `console/documents.html`
(provenance-status tinting + identicons, see today's captain log). This
brief is deliberately the opposite mode -- wide open, technology-grounded,
no cost-cutting -- to give the conference real options to choose from
rather than a pre-narrowed one.

---

## 1. Glyph rendering technology (how symbols actually get drawn)

- **SDF (Signed Distance Field) text** -- glyphs stored as distance fields
  rather than bitmaps or outlines. Infinitely scalable, GPU-cheap, and
  supports real-time per-character effects (glow, outline, distortion,
  dissolve) without re-rasterizing. `troika-three-text` is the mature,
  production-proven library for this in a Three.js/WebGL context. This is
  the realistic path to "every symbol is a living object" without the
  cost of full 3D meshes.
- **Literal 3D glyph meshes** -- extrude actual geometry per character
  (Three.js `TextGeometry`, or hand-modeled glyph meshes). Maximum "3D
  asset" fidelity, maximum cost: a full WebGL scene graph, lighting,
  camera -- and legibility drops fast at reading sizes. Best reserved for
  a small number of hero symbols (e.g. status badges), not body text.
- **Custom font-as-icon-system** -- the cheapest "3D-lite" trick: draw a
  bespoke glyph set as an actual vector font (custom Unicode PUA
  codepoints). Icons then inherit every bit of existing CSS text
  machinery for free -- size, color, flow, selection, copy-paste -- no
  separate render pipeline. This is how most professional icon fonts and
  game UIs (e.g. Destiny's) work. Highest power-to-cost ratio on this
  list.
- **Variable fonts as data-driven typography** -- OpenType variable axes
  (weight, width, slant, and *custom* axes a type designer can define,
  e.g. a "confidence" axis) let a single glyph continuously morph in
  response to live data via `font-variation-settings`, rather than
  snapping between discrete CSS classes. Directly applicable to the
  provenance-tinting work already shipped: confidence could be a
  continuous dial, not four fixed buckets.

## 2. Math & symbolic notation

- **KaTeX** -- fast, static, the practical industry default. Covers the
  overwhelming majority of real LaTeX math notation.
- **MathJax 3** -- slower, but the most complete LaTeX + accessibility
  (screen-reader MathML output) story. Already has one precedent in this
  repo (`web/toys/mike-rocketry-notebook`, CDN-loaded).
- **Custom TeX-style box/glue layout engine, from scratch** -- the actual
  "full custom to the max" option: KaTeX's own internals are already a
  from-scratch reimplementation of Knuth's TeXbook math-mode algorithm.
  Building a Monad-specific variant would allow custom operators/notation
  that don't exist in standard math (e.g. a native glyph for "semantic
  provenance chain" or "influence field") laid out with real TeX-grade
  spacing rules, not just static SVG icons dropped into text.

## 3. Procedural / generative glyphs

- **Seed-driven procedural glyphs** -- extend the identicon idea already
  shipped (hash -> deterministic 5x5 block grid) into full generative
  glyph shapes: Perlin-noise-perturbed strokes, L-systems, or cellular
  automata seeded by entity id, so every document/entity gets a genuinely
  unique, non-repeating visual signature rather than one of a small
  fixed palette. Precedent: generative typography art (Perlin-driven
  letterforms, algorithmic type design experiments).
- **Bespoke semiotic vocabulary** -- rather than reusing emoji/math
  Unicode, design an original small glyph language for Monad-specific
  concepts (packet, doctrine, refusal, provenance-chain, influence
  field) -- closer to alchemical/heraldic symbol systems than to emoji.
  Composable with the custom-font-as-icon-system approach above so it's
  cheap to render once designed.

## 4. Interactive / live documents (the biggest conceptual leap)

This is the category that actually matches "invent new visual languages"
rather than just decorating existing text:

- **Bret Victor's Explorable Explanations** (*Up and Down the Ladder of
  Abstraction*, *Magic Ink*) -- documents where every number is a live
  slider, every diagram is bound to the same underlying data the prose
  describes. Directly relevant to a repo whose whole thesis (per today's
  Semantic Kernel proposal) is "meaning as primary state, text as one
  projection of it."
- **Observable-style reactive notebooks** -- cells that re-execute and
  re-render live as inputs change; a doc isn't static prose, it's a small
  live program.
- **Apparatus / Sketch-n-Sketch** -- direct-manipulation diagram editors
  where dragging the *picture* edits the underlying formula and vice
  versa. The math-manipulation idea from the earlier brainstorm (#5,
  drag an exponent, see it re-typeset) is a small instance of this
  pattern.
- Applied here: a "related packets" graph (already exists as a flat list
  in the right pane) could become a live node graph; clicking a math
  expression in a design proposal could let you drag its parameters and
  watch the prose-described consequence update.

## 5. Field/ambient rendering (ties to "Semantic Physics")

- WebGL fragment-shader backgrounds driven by live document metadata as
  shader uniforms -- e.g. an ambient color/motion field reflecting the
  document's own "semantic physics" influence vectors (calm/urgent,
  confirmed/speculative). Continuous rather than the four discrete CSS
  tints shipped today. Flagged in the earlier brainstorm as the least
  proven idea -- real open question is whether it reads as informative
  or just as noise once it's live and not just described.

## 6. Honest tension, for the conference to weigh

Every item in categories 1 and 4 trades against the tool's actual job:
scanning packets, doctrine, and reports *fast*. GPU-dependent rendering
(WebGL/WebGPU) risks failing or degrading in headless/automated contexts
(a real constraint for this project specifically -- documents get read by
scripted tests and other tooling, not only human eyes). The
font-as-icon-system and variable-font approaches are the standout
exception: nearly all of the visual richness, none of the rendering-
pipeline risk, because they ride on infrastructure that already works
everywhere text works.

## Not yet real

Nothing here is built. This is the wide-open research pass requested
before narrowing -- the conference's job is to pick a direction (or
combination) worth prototyping, the same way #2+#4 from the earlier,
narrower brainstorm were picked and shipped today.
