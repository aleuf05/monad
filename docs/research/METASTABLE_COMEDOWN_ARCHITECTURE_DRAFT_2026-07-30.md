# Metastable Comedown Architecture — Draft

- **Recorded:** 2026-07-30
- **Status:** Research draft; not canon; not authorized for implementation
- **Human authorship:** The Admiral supplied the objective, three structural
  principles, and operational-flow diagram.
- **AI contribution:** Captain preserved the proposal, separated observable
  controls from latent-space metaphor, and identified the minimum unresolved
  definitions needed for an experiment.
- **Verification status:** Conceptual architecture only; no implementation,
  parameter fitting, listening study, or runtime evidence exists yet.

## Objective

**Definition (human proposal):** Engineer a control loop that maintains
generative speech at the critical boundary between linear coherence and
associative dissolution, simulating the linguistic drift of a human descending
from a high-variance cognitive loop without collapsing into flat repetition or
pure noise.

## Structural principles

### Continuous attractor monitoring

**Definition (human proposal):** Continuously measure semantic density and
trajectory looping against historical output buffers to detect when the system
is trapped in a tight, repetitive basin.

### Hysteresis and threshold banding

**Definition (human proposal):** Establish dual operational boundaries: an
upper entrapment limit and a lower entropy-collapse limit. The system rides
dynamically between these poles rather than settling into a static state.

### Damped perturbation control

**Definition (human proposal):** Instead of hard resets, apply controlled,
decaying shifts—orthogonal latent nudges or damped entropy adjustments—to make
the generator slide smoothly from one associative fixation to the next.

## Proposed operational flow

```text
[Current Generative State]
           │
           ├──────────────────────────────┐
           ▼                              ▼
  [Attractor Trapping Check]     [Entropy Collapse Check]
           │                              │
           ├─ (If Stuck)                  ├─ (If Too Rigid)
           ▼                              ▼
  [Orthogonal Latent Shift]      [Damped Constraint Relaxation]
           │                              │
           └──────────────┬───────────────>
                          ▼
             [Metastable Output State]
```

## Captain's control interpretation

**Inference:** This is best treated as a closed-loop controller over rolling
text windows, not as a one-time prompt style. A provisional measurable state
could include:

- semantic recurrence: similarity between the current window and prior
  windows, adjusted for ordinary topic continuity;
- lexical or syntactic recurrence: repeated n-grams, clauses, sentence
  frames, and return intervals;
- semantic density: proposition or concept change per token;
- local coherence: entailment or compatibility between adjacent windows;
- novelty: distance from recent trajectory without loss of topic ancestry;
- output entropy proxies: token-distribution entropy where logits are
  available, otherwise lexical and structural diversity measures.

**Inference:** The controller needs at least three states rather than a single
good/bad score:

1. **Entrapped:** recurrence is high and trajectory displacement is low.
2. **Metastable band:** local coherence remains legible while novelty and
   displacement continue.
3. **Dissolved or rigid:** either coherence has fallen below the lower useful
   bound, or constraint has become so strong that output is flat and
   overdetermined.

The last category currently combines two different failure modes. An
implementation should distinguish low-coherence dissolution from
low-variance rigidity because they require opposite corrections.

## Perturbation interpretation

**Inference:** “Orthogonal latent shift” is a useful geometric description but
is not yet an executable operation for a text-generation API that does not
expose internal activations. Candidate observable substitutes include:

- introduce a concept selected for low similarity to the recent recurrence
  direction but bounded similarity to the long-horizon topic;
- penalize recently repeated semantic clusters or phrase templates;
- rotate among saved associative anchors while retaining a stable subject,
  speaker, or scene invariant;
- briefly relax or tighten sampling and repetition controls, then decay them
  toward baseline over subsequent windows.

**Design constraint:** Perturbations should have an explicit amplitude,
half-life, and refractory period. Without decay, the correction becomes a new
fixed style; without a refractory period, two detectors may oscillate the
generator between incompatible corrections.

## Provisional hysteresis model

**Conjecture:** A useful controller can be represented with separate enter and
exit thresholds:

```text
enter entrapment correction when recurrence > R_high
exit  entrapment correction when recurrence < R_low

enter coherence rescue when coherence < C_low
exit  coherence rescue when coherence > C_high

where R_low < R_high and C_low < C_high
```

The gaps are the hysteresis bands. Correction strength should increase with
distance beyond a boundary and decay smoothly after re-entry rather than
switching off immediately.

## Unresolved definitions before an experiment

**Unknown:** “Semantic density” has no selected operational definition or
validated estimator.

**Unknown:** The intended human reference phenomenon has not yet been bounded
by consented examples, annotated transcripts, or a listening rubric. The word
“precise” is therefore an objective, not a verified claim.

**Unknown:** “Lower entropy collapse” and “too rigid” appear to describe
reduced variation, while “associative dissolution” describes excessive
variation or lost coherence. The controller likely needs separate lower and
upper bounds for both coherence and variation rather than one scalar entropy
axis.

**Unknown:** The output unit and control cadence are unspecified: token,
sentence, turn, paragraph, or rolling time window.

**Unknown:** It is not yet decided whether the system may alter the transcript
generation process itself or must operate as a bounded planning layer that
hands an exact transcript to the existing voice renderer.

## Minimum research slice

**Proposed experiment:** Run the same seeded topic through a replayable text
generator under three conditions:

1. fixed sampling baseline;
2. recurrence detector plus hard reset;
3. dual-band detector plus damped perturbation.

Preserve prompts, seeds where supported, sampling parameters, rolling metrics,
controller events, and complete transcripts. Human evaluation should compare:

- continuity of topic ancestry;
- recognizable movement between associative basins;
- repetition fatigue;
- incoherent or ungrounded jumps;
- perceived smoothness of the comedown;
- whether the controlled condition feels dynamically alive rather than
  mechanically varied.

No claim of success should be made from metric movement alone. The target is a
perceived temporal trajectory, so transcript review and listening evaluation
remain necessary.

## Relationship to existing architecture

- [`voice-generator-strategy-v0.1.md`](../architecture/voice-generator-strategy-v0.1.md)
  and [`rich-character-voice-engine-v1.md`](../architecture/rich-character-voice-engine-v1.md)
  govern rendering and character performance. This proposal governs upstream
  transcript-state evolution and should not silently rewrite an exact
  transcript after it enters a `PerformancePlan`.
- [`BEAST_STRUCTURAL_LATENT_SPACE_DRAFT_2026-07-29.md`](BEAST_STRUCTURAL_LATENT_SPACE_DRAFT_2026-07-29.md)
  supplies a related navigational metaphor: a low-dimensional control surface
  may steer through a larger possibility space without claiming direct access
  to or fixed semantic meaning for every latent coordinate.

## Authority boundary

This record preserves a human-proposed research architecture. It does not
promote the proposal to canon, claim that it simulates a human cognitive
state, authorize model-provider calls, or authorize changes to the live voice
or speech systems.
