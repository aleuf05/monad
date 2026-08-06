# Speech-to-Intent Architecture — Comparative Research (High-Level)

Date: 2026-08-04

Prepared for: Admiral

Scope: pure conceptual research requested following a submitted packet
("VENNA / AROMONAS ENGINE" speech-to-intent directive). Admiral confirmed
directly: "this is pure research... doesn't quite touch system yet." No
target system named VENNA/AROMONAS exists in this repo (see
`docs/engineering-orders/packets/VENNA-SPEECH-TO-INTENT-REFUSED.md` for the
verification), and this host has no discrete GPU (Intel integrated
graphics only, confirmed via `lspci`) — so nothing below assumes or
targets this machine's own hardware. This is a general engineering
assessment against the packet's own stated hypotheses and constraints,
treated as a hypothetical target spec, not a claim about Monad
infrastructure. Nothing here is built; filed per
[[monad-transmission-posture]] as reference research, same shape as
`2026-08-03-microcontroller-acceleration-research-packet.md`.

Evidentiary note: grounded against live web search where checkable (model
VRAM figures, VAD/STT latency data, current API pricing), not recalled
from training data alone, per this repo's evidentiary standard. Sources
listed at the end; a few figures below are flagged explicitly as
unverified where search didn't return specific enough data.

---

## 1. The three hypotheses, assessed against real data

### Hypothesis Alpha — The Unified Beast (single audio-LLM, one forward pass)

**Claim:** a quantized audio-LLM (Audio Flamingo 2 0.5B/3B, Qwen2-Audio)
natively transcribes + reads prosody + infers intent in one pass, <300ms,
within 4GB VRAM.

**What's verifiable:** Qwen2-Audio is a real, shipping model — but it's a
7B-class model, not 0.5B/3B. Quantized VRAM figures found: roughly
5-16GB depending on quantization level, with the low end (~5GB) requiring
aggressive Q4 quantization. That already exceeds a strict 4GB ceiling
before accounting for KV-cache growth during a multi-turn conversational
session (activation memory grows with context length, on top of the
static weight footprint).

**What's unverified:** search did not return specific VRAM figures for
"Audio Flamingo 2" at 0.5B/3B scale specifically — NVIDIA has published
small Audio Flamingo variants in this size class, but this research pass
could not confirm quantized VRAM/latency numbers for them against a
4GB/300ms target. Flagging this as **unverified, not confirmed-false** —
unlike Qwen2-Audio, absence of a specific figure isn't the same as a
contradicted claim.

**Assessment:** plausible in principle for a genuinely small (0.5B-class)
purpose-built audio model, unproven for anything in the Qwen2-Audio
class. The <300ms latency target is the harder constraint than VRAM —
a single forward pass through even a small transformer over several
seconds of raw audio, on CPU fallback, realistically lands well above
300ms; GPU is doing real work in this hypothesis, not an optional
accelerant.

### Hypothesis Beta — The Decoupled Coalition (VAD + DSP + fast STT + fusion)

**Claim:** Silero VAD + pYIN DSP (F0/energy/pauses) + Moonshine/sherpa-onnx
STT gives <30ms, zero-cost, deterministic, under 1GB VRAM.

**What's verifiable, and solid:** Silero VAD is genuinely near-free —
documented at **sub-1ms per 30ms audio chunk on a single CPU thread**,
no GPU required at all. This part of the claim is not just plausible, it's
conservative if anything. Moonshine's published word-error-rate sits
around **4.5%**, meaningfully behind a comparable model like Parakeet
(~1.7% WER) — a real, documented speed/accuracy tradeoff, not free
lunch: Moonshine's speed advantage costs real transcription accuracy.
sherpa-onnx pairing with Silero VAD for offline ASR pipelines is
standard, well-documented practice, not a novel proposal.

**What's harder than claimed:** the <30ms figure is credible for the VAD
stage alone, not for the full VAD+STT+fusion pipeline. One general
CPU-based voice-agent benchmark found found time-to-first-audio in the
**1-4 second range** and explicitly concluded "true <5s real-time not
achievable on CPU" for a complete pipeline (VAD+STT+downstream
processing+response). The individual components are each fast; a full
pipeline's end-to-end latency is not simply their sum minimized, and the
30ms figure likely describes one stage, not the coalition as a whole.

**Assessment:** the most grounded of the three hypotheses component-by-
component (real, cheap, well-documented building blocks), but the
end-to-end latency claim needs its own dedicated benchmark before being
trusted at face value — this pass found real evidence for the pieces,
not for their sum.

### Hypothesis Gamma — The SaaS Bridge (managed cloud API)

**Claim:** offloading to a managed API (Qwen-Audio/DashScope, Gemini 2.5
Flash Audio, Deepgram+DeepSeek) eliminates local VRAM limits within
$60/month.

**What's verifiable:** Gemini 2.5 Flash prices audio input at **$1.00 per
million tokens** (3.3x the text input rate). Google's documented audio
tokenization runs at roughly 25-32 tokens per second of audio (a figure
this pass did not independently re-verify against current docs — treat
as an estimate, not confirmed this session). At that rate, one minute of
audio is roughly 1,500-1,900 tokens, i.e. a small fraction of a cent per
minute of input — a $60/month budget would cover many hundreds of hours
of audio input alone at that rate, before counting output tokens. This
pass did not price DashScope or Deepgram specifically (no dedicated
search run for those) — flagged as a gap, not asserted.

**Assessment:** budget is very unlikely to be the binding constraint for
this hypothesis at any realistic usage volume for a single-operator
system; the real tradeoffs are latency (network round-trip on top of
inference), availability (no offline path), and data leaving the local
machine — none of which this pass has grounds to quantify without a real
target deployment.

---

## 2. VRAM & Latency trade-off matrix (qualitative, grounded where marked)

| | VRAM | Latency | Cost | Confidence |
|---|---|---|---|---|
| **Alpha** (unified beast) | Exceeds 4GB for any verified model (Qwen2-Audio); unverified for smaller Audio Flamingo variants | Likely well above 300ms without a real GPU; unverified below that | $0 (local) | Low — the one hypothesis with a directly contradicted premise (VRAM, for the one model this pass could check) |
| **Beta** (coalition) | VAD: verified near-zero. Full pipeline: plausible under 1GB but end-to-end latency unverified as a whole | VAD stage: verified sub-ms. Full pipeline: benchmark evidence suggests 1-4s+ realistically, not 30ms | $0 (local) | Medium — solid parts, unverified sum |
| **Gamma** (cloud bridge) | N/A (no local VRAM use) | Network-bound, not benchmarked here | Verified cheap relative to $60/mo at plausible volumes | Medium-high on cost, unverified on latency |

---

## 3. Formalizing the "Monadic State Transformer"

The packet's `IntentMonad(S, A) = S -> (A, S, Certainty)` is, read
precisely, a **State monad carrying an uncertainty channel** — a
well-established functional-programming pattern, not a novel invention,
and it formalizes cleanly:

```
type Certainty = Float  -- 0.0 to 1.0

newtype IntentMonad s a = IntentMonad { runIntent :: s -> (a, s, Certainty) }

instance Monad (IntentMonad s) where
  return a = IntentMonad (\s -> (a, s, 1.0))          -- pure action, full certainty
  m >>= f  = IntentMonad (\s ->
    let (a, s',  c1) = runIntent m s
        (b, s'', c2) = runIntent (f a) s'
    in  (b, s'', c1 * c2))                             -- certainty composes multiplicatively
```

This gives real, checkable properties, not just notation:

- **Monad laws hold** as long as `certainty` composition is associative
  and has a real identity (1.0) — multiplication satisfies both, so the
  standard left-identity/right-identity/associativity laws carry over
  unchanged from the plain State monad. This matters practically: it
  means pipeline stages (`VAD >>= STT >>= Fusion`) can be freely
  regrouped/refactored without changing overall behavior, which is the
  actual engineering payoff of using the monadic form instead of an ad-hoc
  callback chain.
- **Certainty degrades monotonically** by construction (product of values
  in [0,1] never increases) — a coalition pipeline's final confidence is
  mechanically bounded by its weakest stage, which matches the real
  failure mode of cascaded ASR/NLU pipelines (a bad VAD segment boundary
  caps everything downstream, no matter how good the STT is on that bad
  segment).
- **Composes the three hypotheses as one interface**, not three
  incompatible architectures: Alpha is `IntentMonad` with one big opaque
  step; Beta is `IntentMonad` composed from `vad >>= extractProsody >>=
  transcribe >>= fuse`; Gamma is `IntentMonad` with one network-bound
  step. A real implementation could genuinely swap architectures behind
  this interface, which is the one part of the original packet's request
  that's both real engineering value and directly buildable.

---

## 4. High-level implementation spec (for the grounded recommendation)

Given the actual evidence above (Beta's components are cheap and real,
Alpha's premise is unverified-to-contradicted at the stated budget, and
Gamma's cost is a non-issue at realistic volume), the grounded
recommendation is a **hybrid Beta-primary, Gamma-escalation** design, not
a pure pick of one hypothesis:

1. **Always-on local stage** (Beta): Silero VAD gates audio; on a detected
   utterance, run local STT (Moonshine for speed, or a better-WER model if
   the 4.5% figure proves too lossy in practice) plus lightweight DSP
   (F0/energy/pause features) — this stage is confirmed cheap and handles
   the overwhelming majority of unambiguous utterances entirely offline.
2. **Confidence gate**: the `IntentMonad`'s `Certainty` output from stage 1
   is the literal trigger condition — below a tuned threshold (ambiguous
   prosody, low ASR confidence, ambiguous ⟦hesitant/sarcastic⟧-class
   utterances like the packet's own UTT-02/UTT-03 benchmark cases), escalate.
3. **Escalation stage** (Gamma): only low-confidence utterances go to a
   cloud audio-LLM for full prosody+intent reasoning — bounding cost
   naturally to the genuinely hard cases, not every utterance, which is
   what keeps a $60/month budget comfortable even at real usage volume.
4. Alpha (a single local unified beast) is **not recommended** as
   currently specified — its core premise (a 0.5B/3B model in 4GB doing
   this in one pass at <300ms) has no verified supporting evidence this
   pass could find, and the one directly-checkable analog (Qwen2-Audio)
   contradicts the VRAM budget outright.

---

## 5. Go / No-Go verdict

**No-Go on Alpha as specified.** Its central hardware/latency premise is
unverified at best (Audio Flamingo 2 at this scale) and contradicted at
worst (Qwen2-Audio, the one model in this class this pass could check).

**Go on a Beta-primary architecture**, its individual components are
real, cheap, and well-precedented — with the caveat that the end-to-end
latency claim (<30ms for the whole pipeline) needs its own real benchmark
before being trusted; treat it as "fast" not "sub-30ms" until measured.

**Go on Gamma as an escalation path, not a primary path.** Cost is not
the binding constraint at any realistic volume; use it selectively for
low-confidence cases surfaced by stage 1's own `Certainty` output, not as
the default route for every utterance.

**This verdict applies to the hypothetical target as specified, not to
any real Monad system** — no VENNA/AROMONAS system, no AMD RX 460, and no
speech-to-intent pipeline of any kind exist in this repository today. If
this is ever scoped as real Monad work, it needs its own packet under
`docs/engineering-orders/packets/` naming an actual target (what would
consume the resulting `Intent`, on what real hardware) before becoming
buildable — same requirement this repo has applied to every prior
research packet.

---

Sources:
- [Qwen2-Audio 7B: Local Audio-Language Model](https://localaimaster.com/models/qwen-2-audio-7b)
- [Performance Metrics · snakers4/silero-vad Wiki](https://github.com/snakers4/silero-vad/wiki/Performance-Metrics)
- [Silero VAD GitHub](https://github.com/snakers4/silero-vad)
- [We Tried to Run a Production Voice Agent on a 16GB CPU](https://heyneo.com/blog/local-voice-research-assistant-cpu-16gb)
- [Choosing the Best Voice Activity Detection in 2026](https://picovoice.ai/blog/best-voice-activity-detection-vad/)
- [Gemini API Pricing: Full Breakdown of Costs (Jul 2026)](https://developer.puter.com/tutorials/gemini-api-pricing/)
- [Gemini 2.5 Flash API Pricing 2026](https://pricepertoken.com/pricing-page/model/google-gemini-2.5-flash)

## Completion state

**recorded** — reference material only, pure conceptual research per the
Admiral's own framing. No repository or live-service change resulted. No
target system (VENNA/AROMONAS or otherwise) exists in this project. Any
future real work requires its own scoped packet with a concrete Monad
target before becoming buildable.
