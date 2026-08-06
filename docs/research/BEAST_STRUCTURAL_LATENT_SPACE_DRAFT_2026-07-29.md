# Beast Structural Latent Space — Draft

- **Recorded:** 2026-07-29
- **Status:** Research draft; not canon
- **Human direction:** Admiral proposed treating Beast Lab sliders as a
  dimensionality-reduction interface for exploring broad subspaces of a much
  larger, richly diverse structural domain.
- **AI contribution:** Captain analysis and proposed model decomposition.

## Governing purpose

**Project doctrine (human ruling, 2026-07-29):** Beastscape is primarily a
laboratory, not a tool or product. Its purpose is to explore and compare
different approaches to defining, reducing, navigating, evaluating, and
interpreting structural possibility spaces. Each working approach is an
instrument for gathering evidence that helps chart a better course.

Success is therefore not measured by accumulating editor features or
stabilizing one early method. It is measured by:

- making alternative approaches runnable and comparable;
- revealing what each representation preserves, distorts, or cannot express;
- preserving specimens, transitions, failures, and human judgments as
  evidence;
- allowing methods to be replaced when the evidence supports a better course;
- converging insights into one coherent living laboratory without mistaking
  temporary implementations for final architecture.

## Research-apparatus ruling — 2026-07-29

**Project doctrine (human ruling):** Beastscape and its Captain integration
must be designed as a research apparatus, not as a user product. Interface
elements exist to expose the experiment: known state, unknown state, method,
inputs, observations, timing, artifacts, failures, and comparative evidence.
They should not simulate certainty, smooth over provider silence, or optimize
primarily for reassuring product-style progress.

Consequences:

- experimental method and charting strategy remain visible;
- observed events are distinguished from estimates and interpretations;
- missing telemetry is reported as unknown rather than replaced with animation
  that implies measured progress;
- temporary implementation limitations remain inspectable;
- comparable runs should preserve enough evidence to evaluate approaches;
- usability serves experimental control and legibility, not product polish or
  premature robustness.

## Intent-led construction ruling — 2026-07-29

**Project doctrine (human insight):** As generative agents increasingly absorb
coding and architectural synthesis, the central human contribution moves
upstream. The essential work is to imagine what may be possible, identify the
reality worth producing, express intent effectively, and judge whether the
result embodies that intent.

For this laboratory, intent is not a vague feature request. Effective intent
names:

- the phenomenon to make possible;
- the experience or observation sought;
- what must remain true;
- what uncertainty should remain visible;
- which tradeoffs are acceptable for the experiment;
- and what evidence would demonstrate that the imagined system exists.

Captain may derive and revise implementation architecture rapidly from that
intent. Architecture remains important, but it is treated as a provisional
instrument rather than the primary human artifact. Human authority remains
concentrated in possibility, purpose, course selection, and evaluation.

## Beastscape Foundry first comparative slice — 2026-07-29

**Implemented experiment:** The master apparatus now compares three candidate
Beastscapes rather than treating one grammar as the territory:

- **Open Ocean:** balanced `seed → differentiate → branch → repeat → fuse →
  terminate` baseline;
- **Metameric Forge:** repetition-first `seed → repeat → segment →
  differentiate → branch → terminate` hypothesis;
- **Symbiotic Reef:** multicore `seed → bud → fuse → differentiate → membrane
  → terminate` hypothesis.

Each candidate has 720 deterministic structural soundings, all six current
topological regimes, its own 24-dimensional descriptor distribution, and an
independently fitted three-dimensional UMAP Passage. The same 12-anchor
continuous decoder and renderer make the candidates directly explorable under
controlled interface conditions.

**Caution:** These first grammars specialize a common procedural substrate.
They prove comparative Foundry mechanics and produce ecological differences,
but they are not yet independently expressive developmental engines. Human
testing must determine whether the differences are structurally meaningful
enough to justify deepening the grammar language.

## Core reframing

**Superseded proposal:** Treat each slider as a human-readable semantic axis
that coherently moves named lower-level structural variables.

**Project doctrine (human correction, 2026-07-29):** A slider is not a control
over a named set of features. It is an abstract navigation instrument for
charting a course through an otherwise unmanageable high-dimensional
structural space. Its structural effect may be entangled and context-dependent.
The slider exposes a traversable direction, not a biological explanation.

**Project doctrine (human ruling, 2026-07-29):** The editor does not modify
one creature type. It selects a unique specimen from a broad, heterogeneous
space of possible structures. “Radial hydra” describes one implemented region
of that space, not the identity or outer boundary of the instrument.

**Metaphor:** The full beast space is an ocean; the visible controls are
currents. A current should carry the explorer through a recognizable region,
not expose every coordinate of the water.

The current radial-hydra recipe is a small explicit parameter space:
symmetry, branch depth, reach, curl, irregularity, terminal organ, and seed.
That makes it legible and deterministic, but most controls currently map
almost one-to-one onto renderer variables. The proposed lab instead needs a
larger generative grammar plus a smaller set of semantically meaningful
navigation axes.

## Three-layer model

### 1. Structural genotype

**Definition:** A high-dimensional, deterministic description of topology and
development. Candidate dimensions include:

- body plan and number of centers;
- radial, bilateral, segmented, colonial, or hybrid organization;
- limb attachment graph;
- branching rules, depth, cadence, and asymmetry;
- repetition, fusion, budding, and termination rules;
- skeletal curvature and torsion;
- local thickness and taper fields;
- organ placement and repetition;
- voids, membranes, shells, joints, and internal supports;
- developmental constraints and symmetry-breaking events.

This layer is the source of truth.

### 2. Explorer manifold

**Definition:** A low-dimensional local chart through which an explorer can
move inside the high-dimensional genotype space without directly managing its
coordinates.

Possible abstract bearings might be displayed as neutral navigational
coordinates rather than trait claims:

- bearing α;
- bearing β;
- bearing γ;
- bearing δ;
- local divergence;
- step scale.

A bearing may change topology, proportions, attachment rules, and organ
distribution together. Its effect is determined by the region currently being
traversed. Moving along α near a radial organism need not produce the same
visible changes as moving along α near a colonial network. What must remain
stable is navigational coherence: small course changes produce traceable local
movement, saved coordinates can be revisited, and crossings into new regions
remain visible.

**Inference:** The interface may need to re-chart or recenter its local
low-dimensional projection as the explorer travels. The controls are closer
to helm, bearing, and scale than to anatomical knobs. A saved specimen must
therefore preserve its high-dimensional location plus the chart/projection
used to navigate there, not merely the visible slider positions.

### 3. Phenotype / interpretation

**Definition:** Geometry, schematic, concept art, and later 3D form derived
from the genotype. These are evidence-bearing interpretations, not the source
of truth.

The schematic should reveal the genotype. The concept renderer should preserve
it while adding flesh, material, lighting, and environmental adaptation.

## Exploration mechanics

**Project doctrine (human ruling, refined 2026-07-29):** Navigational mappings
are chosen, not arbitrary. Small movements may cause radical structural change
because a bearing traverses a high-leverage direction through the manifold,
but the path through the space must remain intelligible. Intelligibility
belongs to the continuity, reversibility, landmarks, and lineage of the
course—not necessarily to a fixed semantic meaning for each slider.

**Design criterion:** Every visible transformation should be attributable to
a reproducible movement through the chart. Nearby positions retain ancestry
even when they cross a structural phase boundary. Randomness may supply local
variation inside the selected region; it must not define the mapping between
control position and structural outcome.

**Project doctrine (human refinement, 2026-07-29):** The three-slider
configuration space is intentionally high-gain. A small change in slider
configuration should commonly select a radically different *type* of
creature, not merely a cosmetic or proportional variant. This does not permit
arbitrary discontinuity: the mapping remains deterministic, the course is
reversible, and the structural event connecting the two specimens is
inspectable. “Nearby” means nearby in navigational coordinates and lineage,
not necessarily visually or taxonomically similar.

**Proposed interaction model:**

1. Enter the structural space at a broad region or saved landmark; family
   labels describe regions encountered rather than permanently constraining
   the editor.
2. Navigate it using 4–8 semantic macro sliders.
3. Observe topology and phenotype update together.
4. Lock traits worth preserving.
5. Mutate only unlocked dimensions.
6. Branch a specimen into nearby alternatives.
7. Save landmarks and interpolate between them.
8. Cross a phase boundary deliberately to enter another family.

Useful additions include a two-dimensional “map of nearby forms,” visible
lineage, parent/child comparisons, distance-from-parent, novelty indicators,
and named regions discovered during exploration.

## Important design distinction

**Technical finding:** A single globally smooth space is unlikely to represent
all interesting structures honestly. Different topologies form separate or
partly connected regions. Seven limbs cannot continuously become eight
without a branching, splitting, budding, or insertion event.

Therefore the system should combine:

- continuous axes for morphology within a topology;
- discrete grammar operations for topology changes;
- explicit transition operators connecting structural families;
- seeded variation fields for reproducible local diversity.

The dimensionality reduction should not erase these discontinuities. It
should make them navigable and visible.

## Evaluation criteria

The richer system succeeds when:

- nearby control positions usually produce related, intelligible forms;
- large moves traverse visibly different structural regions;
- distinct settings do not collapse into cosmetic variants;
- the same genotype regenerates the same skeleton;
- concept and 3D interpretations retain genotype lineage;
- locks and mutations behave predictably;
- explorers can return to saved landmarks;
- surprising forms emerge without becoming arbitrary noise.

## Unknowns

- Whether semantic axes should be hand-authored, learned from generated
  specimens, or hybrid.
- How many families are needed before the space feels genuinely broad.
- Which topology transitions can be made visually continuous.
- Whether an embedding should organize genotypes, rendered images, human
  judgments, or all three.
- How Live Captain should propose, name, evaluate, and preserve newly
  discovered regions without silently changing the underlying grammar.

## Model-based dimensionality reduction analysis — 2026-07-29

**Inference:** The best initial architecture is hybrid. An authored
developmental grammar and validity layer defines what can exist. A learned
graph representation estimates structural neighborhoods and useful courses.
Human exploration evidence teaches which courses are interesting. Rendered
pixels remain phenotype evidence and must not define structural distance.

Recommended learning stack:

1. Generate a structural atlas from the grammar, preserving programs, graphs,
   lineage, transitions, and rendered interpretations.
2. Train a graph encoder/decoder into a moderate latent representation rather
   than directly into three dimensions.
3. Train the representation with graph reconstruction, lineage, transition,
   validity, and human similarity/preference evidence.
4. Calculate a local three-bearing chart at the current specimen. Optimize
   bearings for structural gain, mutual independence, valid decoding,
   reversibility, and coverage of nearby phase boundaries.
5. Recenter the chart during travel while preserving the full latent
   coordinate and course history.

**Technical caution:** Unsupervised disentanglement is not identifiable
without inductive bias. UMAP and related manifold methods are useful for
atlases and neighborhoods but do not alone provide a trustworthy generative
inverse. Graph autoencoders provide a more appropriate substrate than image
embeddings, but require explicit geometry/topology preservation and validity
losses. Preference learning should tune interestingness and navigational
utility, not decide structural validity.

**Later research candidate:** Neural cellular automata could provide a learned
developmental substrate with emergence and regeneration, but should follow,
not precede, a legible graph-grammar baseline.

## Atlas-first strategy and personalized embedding — future course

**Terminology correction (human ruling, 2026-07-29):** “Atlas-first” is a
general dimensionality-reduction strategy, not one approach. Beastscape should
eventually compare multiple implementations of that strategy, including
linear, manifold, graph-autoencoding, metric-learning, and other learned
projections. The immediate course should implement one method first rather
than presenting the whole strategy as a single competitor.

**Future concept (human direction):** The explorer does not merely choose
between static embeddings prepared by the system. By using Beastscape, the
explorer creates a personalized embedding. Their landmarks, revisits,
comparisons, rejected directions, continued courses, enhancements, and exports
teach the system which structural distinctions and neighborhoods matter to
them.

**Monadic interpretation:** A common structural atlas may exist, but the
navigable geometry is relational: it develops through the continuing
interaction between one explorer and the space. Different explorers may chart
different meaningful neighborhoods without requiring different underlying
structural truth.

Potential future architecture:

```text
shared structural atlas
  + explorer interaction history
  + personal similarity / interest model
  -> personalized structural metric
  -> continuously updated local embedding
  -> three offered bearings
  -> new interaction evidence
```

Important requirements for that future course:

- landmarks act as durable anchors while the embedding learns;
- prior coordinates and journeys remain reconstructable;
- learning is gradual enough that the chart does not become unintelligible;
- personal preference affects navigation and interestingness, not structural
  validity;
- the system distinguishes exploration evidence from accidental clicks;
- embedding versions preserve provenance so movement in the map can be
  separated from movement of the map itself.

**Status:** Saved for future course. Do not entangle this personalization layer
with the first atlas-first reduction experiment.

## Instrument integration ruling — 2026-07-29

**Project doctrine (human ruling):** Beast Space Navigator may remain a
separate component during rapid research, but the intended system is one
coherent Beastscape tool. Abstract navigation, structural truth, anatomical
interpretation, Captain enhancement, atlas landmarks, lineage, fitness
evidence, and later learned guidance must converge on one shared specimen
identity and structural source of truth. The current split is experimental
scaffolding, not product architecture.

## Fitness and interestingness — 2026-07-29

**Project doctrine (human ruling):** Navigation requires an account of why
some creatures are interesting and others are not.

**Inference:** Beastscape should not use a single scalar fitness objective.
That would optimize toward one dominant creature basin and erase the diversity
the instrument exists to explore. Use a quality-diversity archive with:

- hard validity gates;
- several separately visible quality measures;
- structural novelty relative to the archive;
- surprise relative to predicted local development;
- coverage of underexplored structural niches;
- learned human curiosity/preferences;
- penalties for degeneracy, duplication, and incoherent transitions.

Candidate admission can be expressed as a vector:

```text
interest(x) = {
  valid,
  coherent,
  structurally_novel,
  developmentally_surprising,
  richly_organized,
  underexplored,
  human_selected
}
```

The search process should preserve multiple local elites rather than rank the
entire Beastscape on one ladder. Human saves, revisits, comparisons, and course
continuations provide stronger preference evidence than an isolated like
button. The model may learn an interestingness prior from this evidence, but
novelty and coverage must remain independent pressures so taste does not
prematurely collapse the space.
