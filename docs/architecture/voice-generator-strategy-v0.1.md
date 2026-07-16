# Voice Generator Strategy V0.1 (proposed)

Status: research/proposed strategy, not adopted. This document is a design
target only — per the Architecture Engine invariants, ceremony (a proposed
strategy) carries no execution authority, and per Gate One (Necessity) this
should be read and judged against the real problem below before any
implementation begins.

## Problem this solves

Two toys speak aloud today — Radio Console (`toys/radio-console/app.js`)
and Living Captain (`toys/living-captain/app.js`, shipped this session).
Both are hardcoded directly to the browser's `window.speechSynthesis` API,
each with its own independent copy of near-identical voice-selection logic
(find an English voice, prefer one with "natural/enhanced/premium" in its
name, handle zero-voices honestly). Two problems follow directly from that:

1. **Every future speaking toy repeats the same ~30 lines of voice-picking
   and zero-voice-fallback logic**, or worse, forgets the zero-voice
   fallback (this session's Living Captain voice feature initially did,
   before being caught in verification — see `docs/reports/`).
2. **Browser `speechSynthesis` is the only option available**, and it is a
   real, known-limited one: voice quality and availability vary wildly by
   OS/browser (this whole session's testing found zero installed voices on
   this dev machine's browsers), there is no way to guarantee a consistent
   "Captain's voice" persona across visitors' different devices, and there
   is no path to a materially better voice without a cloud TTS vendor.

This document proposes a shared, vendor-neutral generator so a) that
duplication stops, and b) a better voice becomes a configuration choice,
not a rewrite.

## Non-goals

- This is not a proposal to require any cloud vendor. Per this project's
  "local-first boundaries remain preferred" invariant, browser
  `speechSynthesis` remains the zero-configuration default for every
  visitor who never touches voice settings.
- This is not a proposal for a server-side voice pipeline, queueing
  system, or audio CDN. Every provider adapter runs client-side, same as
  today.
- This is not a proposal to change what Radio Console or Living Captain
  currently say — only how the "speak this text" step is implemented
  underneath.

## The VoiceGenerator contract

One interface, implemented by every provider adapter:

```js
// toys/shared/voice.js (proposed)
// A VoiceProvider implements:
//   .id            -- stable string, e.g. "browser-speechsynthesis"
//   .label         -- human-readable name for settings UI
//   .requiresKey   -- boolean
//   .capabilities  -- { streaming: bool, ssml: bool, offline: bool, costClass: "free"|"metered" }
//   .isAvailable()             -- sync, cheap: can this provider even attempt to speak right now?
//   .listVoices()              -- async -> [{voice_id, label, lang}], provider-specific
//   .speak(text, options)      -- async -> SpeakHandle {onstart, onend, onerror, stop()}
//                                  options: {voice_id, rate, pitch, volume}
```

Every existing call site's shape survives unchanged: `speak(text,
options)` returns something with the same `onstart`/`onend`/`onerror`
lifecycle Radio Console and Living Captain already branch on, so adopting
this is a like-for-like swap under each toy's existing `speak()` /
`speakCaptainStatus()` function, not a rewrite of their calling code.

## Provider adapters

| Provider | `requiresKey` | Notes |
|---|---|---|
| `browser-speechsynthesis` | no | Wraps the existing logic verbatim (voice-preference search, zero-voice honest failure). Always registered, always the fallback of last resort. |
| `elevenlabs` | yes | Best quality-per-dollar for a consistent character voice today; metered per character. |
| `openai-tts` | yes | Simple REST call, same key shape as the Cognition Graph already handles (bring-your-own, see below). |
| `google-cloud-tts` / `azure-tts` | yes | Included for completeness/choice, not because either is preferred — Gate One (Necessity) says don't add a provider without someone actually wanting it. |

Provider adapters beyond `browser-speechsynthesis` are **not built in this
pass**. This document specifies the contract each would implement; actual
implementation is its own bounded packet per provider, built only when a
real need names which vendor (Gate One again: "does this solve a real and
defined problem," not "could someday be useful").

## Configuration model

Per-speaker voice profile, not one global voice — Radio Console already
has multiple named speakers (Bridge, Engineering, Traffic, Monad Actual,
individual scouts); Living Captain has one. A profile is:

```json
{
  "schema_version": "monad.voiceprofile.v0.1",
  "speaker": "captain.monad",
  "provider_id": "browser-speechsynthesis",
  "voice_id": null,
  "rate": 0.96,
  "pitch": 1.0,
  "fallback_provider_id": "browser-speechsynthesis"
}
```

Default configuration ships with every profile pointing at
`browser-speechsynthesis` — adopting the shared module changes nothing
about default behavior for any visitor who hasn't configured anything,
same principle the Cognition Graph's mock-mode default already
established for this project.

### Known speakers today, mapped to distinct profiles

Not hypothetical entities — every one of these already exists as a named
`speaker` value in a real toy's transcript. Diversity of voice is a
per-speaker profile assignment, not a new mechanism per entity:

| Speaker (as it appears today) | Source | Proposed distinct voice treatment |
|---|---|---|
| Monad Actual (flagship) | Radio Console, `speakerNameFor()` | Distinct from scouts -- the one voice a listener should always recognize as "the ship itself." |
| Scout Alpha / Bravo / Charlie | Radio Console, per-vessel `speakerNameFor()` | Each already has a distinct name; `voiceForSpeaker` (Map, `app.js`) already exists to pin a consistent voice per name once assigned -- this strategy's `voice_id` field slots directly into that existing map instead of leaving it to whatever the browser picks first. |
| Bridge | Radio Console, most status/watch lines | The "announcer" voice -- distinct from any specific vessel, since it's reporting about vessels, not speaking as one. |
| Engineering / Traffic / Weather | Radio Console, station-specific lines | Each a distinct station identity today only in text (channel tag); no voice distinction currently exists. A real candidate for the first non-default profiles once a second provider is added. |
| Diagnostics | Radio Console, `runTestMessage()` | Deliberately generic/neutral -- a test message representing no one, should never be mistaken for a real speaker. |
| NPR Newswire | Radio Console, `speakNewswireHeadline()` | Already deliberately kept in its own voice/pipeline, separate from fleet radio (existing doctrine, `NPR-HEADLINE-READER-1.0` packet) -- this strategy preserves that separation, it doesn't unify it. |
| Living Captain | Living Captain, `speakCaptainStatus()` | A command-presence voice, distinct from Bridge's announcer role -- this is the captain speaking in first person about their own observation, not a report about someone else. |

This is the concrete argument for per-speaker profiles over one global
voice: these seven-plus identities are already textually distinct in this
project's existing transcripts. A single shared voice for all of them
would be a regression in clarity, not a simplification.

## Credential handling

Any cloud provider needs an API key. This site has no auth gate and no
server-side secret store for public toys (per `CLAUDE.md`'s accepted
security posture) — the exact problem already solved once this session
for the Cognition Graph. **Reuse that solution rather than inventing a
second one:**

- A per-provider key, entered by the visitor into a "Voice Settings"
  panel, stored only in that browser's `localStorage`
  (`monad.voice.<provider_id>.key`), never written into any toy's served
  source, never sent anywhere but directly to that provider's own API.
- No key configured for a chosen provider → the generator automatically
  falls back to `browser-speechsynthesis`, with the fallback itself
  visible in the UI (never a silent downgrade) — same "connected is not
  the same as heard" honesty this whole session's Radio Console
  diagnostics work already established.

## Fallback chain

```
1. Try the speaker's configured provider, if isAvailable() and (a real
   key is present OR requiresKey is false).
2. On failure (network error, missing key, provider outage) -> fall back
   to fallback_provider_id (default: browser-speechsynthesis).
3. If browser-speechsynthesis also has zero voices -> the existing honest
   "No TTS voices installed" message, not silence.
```

No step is allowed to fail silently — every step either speaks or reports
why it didn't, matching this session's Radio Console Audio Path Status
panel and Living Captain's zero-voice fix.

## Migration plan for existing toys

Deliberately incremental, not a flag-day rewrite of two already-tested,
working toys:

1. Extract `toys/shared/voice.js` with exactly the `browser-speechsynthesis`
   provider, behaviorally identical to what Radio Console's `speak()` /
   `speakNewswireHeadline()` and Living Captain's `speakCaptainStatus()`
   already do today (same voice-preference search, same zero-voice
   message). No new capability yet — pure extraction.
2. Swap Radio Console and Living Captain's internal calls to use the
   shared module. Acceptance: existing behavior is byte-for-byte
   equivalent from a user's perspective — same voice selection, same
   fallback text, verified live the same way this session verified
   everything else (headless-browser click-through + direct function
   tracing, not just a visual check).
3. Only after step 2 is verified with zero regression, add a second
   provider adapter (whichever a real request names) and the Voice
   Settings panel.

Steps 2 and 3 are separate packets. Nothing here authorizes touching
Radio Console's or Living Captain's already-working speech code until a
step-1 extraction exists and passes the same verification bar the rest of
this session's work did.

## Open questions deferred to implementation packets

- Does a shared voice module belong in `toys/shared/` (matching
  `fleet-state.js`'s existing precedent) or somewhere new? This document
  assumes `toys/shared/` given the direct precedent.
- Should Newswire's "From NPR News Headlines" attribution voice differ
  from fleet Bridge chatter's voice, now that per-speaker profiles exist?
  Not decided here — a real design choice for whoever picks up step 3,
  not assumed.
- Cost visibility for a metered provider (ElevenLabs/OpenAI TTS) — this
  document specifies bring-your-own-key parity with the Cognition Graph,
  but doesn't design a spend meter. Living Captain's existing
  `spend_boundary` pattern (`tools/living-captain/captain.py`) is a real
  in-repo precedent worth reusing if/when this becomes a real requirement.
