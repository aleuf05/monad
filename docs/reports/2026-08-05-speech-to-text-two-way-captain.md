# Speech-to-Text for two-way operator ↔ Captain interaction

Date: 2026-08-05
Prepared for: Admiral
Scope: **buildable research.** Unlike `2026-08-04-speech-to-intent-architecture-research.md`,
this one has a real target.

---

## 0. Why this is different from yesterday's research

The 2026-08-04 speech-to-intent research closed with an explicit condition:

> *"If this is ever scoped as real Monad work, it needs its own packet naming
> an actual target (what would consume the resulting `Intent`, on what real
> hardware) before becoming buildable."*

**That condition is now met.**

- **What consumes it:** the Live Captain. Running, unpaused, accepting turns
  at `/api/turn`, with a conversation store and a kernel.
- **On what hardware:** this host, verified today.
- **What completes the loop:** the Captain already *speaks* — verified, its
  own words, its own voice, 19.52s of rendered audio.

Speech-out is done. This is speech-in.

## 1. Host reality, checked not assumed

| | |
|---|---|
| GPU | **Intel 3rd Gen integrated only.** No discrete GPU — confirms yesterday's `lspci` finding |
| `ffmpeg` | **absent** |
| Capture nodes | 2 present under `/dev/snd/` |
| Existing audio out | browser `speechSynthesis` + Gemini TTS via `rich-voice` |
| Existing audio in | **none** |

**The GPU absence rules out the whole local-model branch of yesterday's
research** — Whisper, Qwen2-Audio, anything needing VRAM. That is not a
constraint to design around; it is a constraint that eliminates most of the
option space, which is useful.

## 2. The option that is already installed

**The browser is the microphone, exactly as it is already the DAC.**

We use `speechSynthesis` for the Captain's voice. Its twin,
`SpeechRecognition`, is in the same API and the same page:

- Chrome/Chromium 25+ on every desktop platform and Android
- Safari 14.1+ macOS, 14.5+ iOS, via `webkitSpeechRecognition`
- Firefox behind a flag; Chrome streams audio to Google's recognition service
- Supports `continuous` and `interimResults` — live partial transcripts as
  you speak, which is what makes it feel like conversation rather than
  dictation

**Cost: zero.** No API key, no server, no model, no GPU, no `ffmpeg`, no
install. It runs in the page that already exists at `/root`.

This is the same shape as the Little Buddy conclusion: §2A of that packet
wanted an ESP32 and a DAC, and the browser already *was* the DAC. Here it is
already the microphone.

**Its real limitations, stated:**

- **Not local.** Chrome sends audio to Google. For a single-operator console
  behind a password that is an acceptable trade; it is worth naming rather
  than discovering.
- **Vendor-prefixed and non-standard.** `webkitSpeechRecognition` in most
  browsers; the spec has never fully landed.
- **Firefox effectively unsupported.** Which does not matter for a
  single-operator system, and would matter for anything public.

## 3. The escalation path, if accuracy ever binds

Gemini already has our key, our budget ledger, and our failover discipline.
Audio understanding is on the *same* `generateContent` endpoint the TTS
provider now uses:

- Audio passed as `inline_data`, max **20 MB** per request
- Accepts WAV, MP3, AIFF, AAC, OGG, FLAC
- Transcription is prompted (*"Transcribe this audio"*), not a distinct mode
- Billed as ordinary input tokens, roughly **$0.10–$2.00 per million**
- Flash is faster; Pro is more accurate

Because the WAV path already exists in `rich-voice`, the same artifact
handling works in reverse. **This is an escalation path, not a primary
one** — same verdict yesterday's research reached about the SaaS route, and
it survives contact with the new target.

## 4. Recommended architecture

```
Admiral speaks
      │
      ▼
browser SpeechRecognition        ← free, local to the page, zero install
      │  interimResults → live transcript in the input box
      │  final result   → the utterance
      ▼
POST /api/turn                   ← the path that already exists
      │
      ▼
Captain generates a reply        ← already works
      │
      ▼
/voice-api/render → Kore         ← already works
      │  (falls back to browser voice when the budget is spent)
      ▼
Admiral hears it
```

**Every box except the first already exists and is verified.** The work is
one component and one wire.

### Why not push-to-talk-to-a-server

The obvious alternative — record in the browser, POST the audio to a new
service, run STT there — needs a new unit, a new route, a new port, an
`ffmpeg` install, and either a GPU we do not have or a cloud round trip we
can already do from the page. It is strictly more machinery for the same
result.

## 5. What would actually get built

Small, and honest about it:

1. A **push-to-talk button** at `/root` next to the Captain input. Hold to
   speak, release to send. Push-to-talk rather than always-listening, for
   the obvious reason: an always-open microphone in a room is a decision
   nobody made deliberately.
2. `interimResults` painted into the input box live, so you can see it
   hearing you and correct before sending.
3. On final result, the existing `submitDirective()` path — no new endpoint.
4. Graceful absence: no `SpeechRecognition`, no button. Typing is unaffected.

### Commissioned push-to-talk boot sequence

The input channel is now deliberately single-mode. There is no continuous
microphone toggle and no recognition restart loop.

1. Root Console loads with the microphone closed.
2. An authenticated, ready Bridge accepts `pointerdown` on the visible 🎙
   control, captures that pointer, stops Captain playback, and starts exactly
   one browser `SpeechRecognition` session.
3. While the same pointer remains held, interim hypotheses replace the command
   field. Cumulative provider prefixes are collapsed instead of appended.
4. `pointerup` stops recognition. Its `onend` flush boundary submits once
   through the existing `submitDirective()` path; a 700 ms fallback covers a
   browser that omits `onend`.
5. `pointercancel` or loss of window focus stops recognition and submits
   nothing. Recognition never restarts itself.

Operational invariant: **no held mic button, no live voice input**. Captain
speech output remains independently selectable; it does not open the Admiral's
microphone.

**Estimated: one component, ~60 lines, in `console/`. No new service, no new
route, no new unit, no spend.**

## 6. What this does NOT solve

- **Wake words / hands-free.** Push-to-talk is a button. Always-listening
  needs a VAD stage (Silero, per yesterday's research) and a decision about
  an open microphone that is the Admiral's, not an engineering one.
- **Speaker identity.** The browser transcribes whoever is audible.
- **Noise robustness.** Google's recogniser is decent and untested here.
- **Barge-in.** Interrupting the Captain mid-sentence while it is speaking
  needs the recogniser and the synthesiser coordinated; not in this slice.

## 7. Verdict

**Go, on the browser path.** It is the only option that requires no
hardware this host lacks, no service, no route, no spend, and no install —
and it is the exact mirror of the output path already proven today.

**Gemini audio as escalation only**, if and when accuracy binds. The key,
the ledger, and the failover already exist.

**No-go on local models**, unchanged from yesterday and now for a harder
reason: no GPU, no `ffmpeg`, and a working alternative that costs nothing.

---

## Sources

- [SpeechRecognition — MDN](https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition)
- [Web Speech API — MDN](https://developer.mozilla.org/en-US/docs/Web/API/Web_Speech_API)
- [Web Speech API specification](https://webaudio.github.io/web-speech-api/)
- [A Deep Dive into the Web Speech API](https://blog.addpipe.com/a-deep-dive-into-the-web-speech-api/)
- [Speech recognition in the browser using Web Speech API — AssemblyAI](https://www.assemblyai.com/blog/speech-recognition-javascript-web-speech-api)
- [Audio understanding — Gemini API](https://ai.google.dev/gemini-api/docs/generate-content/audio)
- [Gemini Developer API pricing](https://ai.google.dev/gemini-api/docs/pricing)
- Prior research: `docs/reports/2026-08-04-speech-to-intent-architecture-research.md`
