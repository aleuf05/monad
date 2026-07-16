# Rich Character Voice Engine v1

## Decision

Build one character-performance system with two render tiers:

1. **Rehearsal** — installed Browser Speech, zero API spend, immediate, visibly lower fidelity.
2. **Final take** — Gemini controllable TTS, generated only on explicit demand or approved radio publication, then stored in a content-addressed cache.

Captain is a character test case. It has no privileged voice-engine path.

## End-to-end path

`Living Fleet identity projection -> CharacterSpec -> PerformanceState -> PerformancePlan -> RenderRequest -> cache lookup -> Gemini TTS or browser rehearsal -> AudioArtifact -> playback`

The durable identity system remains Living Fleet. `MonadCharacters` is the browser/runtime projection of character facts, not a competing memory store. `MonadPerformance` owns ephemeral affect continuity. `MonadVoice` owns provider selection and playback.

## Core records

### CharacterSpec

- `character_id`, display name, role
- stable vocal identity: Gemini prebuilt voice name, habitual cadence, vocal weight, pronunciation map
- traits and expressive bounds
- stress, humor, restraint and recovery behavior
- provenance: synthetic/licensed/consenting participant; source and authorization
- revision number

### PerformanceState

- continuous tension, warmth, energy and restraint
- baseline, target, prior state and update time
- intent, audience, public/private setting and pressure
- reason trace and masking/restraint instruction

### PerformancePlan

- exact transcript (never silently rewritten)
- short natural-language direction compiled from character + state + intent
- chosen Gemini voice
- optional sparse audio tags such as pauses or whispers, only when authored/approved
- expected duration and estimated maximum cost
- character/performance/model revisions

### AudioArtifact

- SHA-256 cache key over normalized transcript, CharacterSpec revision, PerformancePlan, provider/model and output format
- audio path, duration, byte length and creation time
- provider receipt and estimated/actual spend
- provenance and disclosure metadata
- immutable; a changed plan creates a new artifact

## Spend boundary

- Rehearsal never calls an API.
- Final generation requires an explicit **Generate rich take** action; slider movement never calls Gemini.
- Debounce is insufficient and is not the spend control. Only the final button crosses the boundary.
- Cache lookup occurs before budget reservation. A hit costs zero and plays immediately.
- One requested take by default. Variants require another explicit action.
- Hard limits: maximum characters and estimated duration per request, daily request count, daily audio seconds and daily USD ceiling.
- Reserve estimated cost atomically before calling; reconcile with the receipt afterward; fail closed when a limit is exhausted.
- Radio uses only cached/approved artifacts. Uncached live chatter falls back to Browser Speech rather than spending automatically.
- Pre-generating recurring/ceremonial lines uses Gemini Batch TTS when available.

At the documented Gemini 2.5 Flash Preview TTS paid rate, output is $10 per million audio tokens and audio is 25 tokens/second: approximately $0.00025/second or $0.015/minute. Batch halves that. These figures are configuration metadata, not constants: pricing/model availability must be revalidated before commissioning.

## Provider contract extension

The existing `MonadVoice` provider interface stays. A rich provider additionally advertises:

- `capabilities.richDirection`, `exactTranscript`, `multiSpeaker`, `audioTags`
- `estimate(request)` without generation
- `render(request)` returning an AudioArtifact receipt
- `lookup(cacheKey)`

The browser never receives the Gemini API key. A same-origin backend endpoint owns the key, budget ledger, cache and provider request. All external generative calls use Gemini.

## API surface

- `POST /voice-api/estimate` — validates and returns cache status, expected seconds and maximum cost; no provider call.
- `POST /voice-api/render` — cache-first, budget-reserved final generation; idempotency key required.
- `GET /voice-api/artifacts/{hash}` — immutable audio and provenance.
- `GET /voice-api/budget` — used/reserved/remaining seconds and currency.

No arbitrary provider prompt is accepted from Radio. Clients submit transcript, character ID/revision, structured intent/state, and an idempotency key; the server compiles the direction from bounded character fields.

## Prompt compiler

Direction is compact and ordered:

1. preserve the selected character voice;
2. state social intent and audience;
3. describe mixed affect in one sentence;
4. specify restraint, pace and emphasis;
5. demand exact transcript recitation;
6. append transcript separately.

Example: `Captain Monad addresses the Lieutenant privately. Warm authority under controlled concern; measured pace, restrained energy, tension still present but recovering. Keep command weight and avoid melodrama. Recite the transcript exactly.`

## Evaluation gate

Architecture is not success. Before Radio rollout, conduct blind listening tests using the same six lines across at least three characters and four intentions.

- character identification above chance and target >= 75%
- intended social meaning target >= 80%
- transcript accuracy 100% for operational lines
- continuity preference over stateless rendering
- caricature flag below 10%
- cache-hit ratio and spend per accepted take reported

If distinct recognition fails, revise voice bindings/CharacterSpec; do not compensate by exaggerating every emotion.

## Delivery sequence

1. **Now:** stable distinct installed-voice bindings and visible device coverage for free rehearsal.
2. **Provider slice:** backend Gemini Flash TTS provider, exact one-line render, immutable cache and hard budget ledger.
3. **Studio slice:** Estimate, Generate rich take, cache-hit/spend/provenance display, A/B against rehearsal.
4. **Evaluation:** blind test fixture and recorded results.
5. **Integration:** Living Captain reads approved/cached rich takes; Radio consumes only cached artifacts and never autonomously spends.

## Explicit non-goals

- cloning or imitating identifiable real people
- a second durable character-memory database
- API generation on every radio event
- hidden automatic retries that multiply cost
- treating prompt prose as a substitute for listening evaluation
