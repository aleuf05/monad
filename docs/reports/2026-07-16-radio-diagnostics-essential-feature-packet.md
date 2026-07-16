# Radio Console — Essential Feature Packet, Implemented

Date: 2026-07-16

Source: Captain's Engineering Packet, "RADIO CONSOLE — ESSENTIAL FEATURE
PACKET," operating rule: *"Connected is not the same as heard."*

## What changed

Added a Diagnostics panel to `toys/radio-console/` (synced to
`web/toys/radio-console/`) implementing all six required features:

1. **Radio State** — one of `LIVE` / `IDLE` / `FAULT` / `UNVERIFIED`,
   deliberately conservative: `LIVE` is only ever reached via a *measured*
   audible test-tone pass this session, never merely because content is
   flowing.
2. **Content Queue** — queued count, current message, last accepted
   message (with source tag), content-loop active/idle.
3. **Audio Path Status** — five independently tracked stages (synthesis
   requested, audio generated, stream delivered, playback started,
   audible output verified), each `pending` / `ok` / `fail` /
   `unverified`.
4. **Test Controls** — Play Test Tone, Inject Test Message, Stop
   Playback, each producing a logged, timestamped, reviewable result in
   a Diagnostics Log panel.
5. **Output Controls** — existing mute/volume retained; added an output
   device selector and a real (non-decorative) audio level meter.
6. **Source Identification** — every transcript entry now carries a
   Simulated/Generated/Live/Unknown tag; the existing "Signal" bar
   visualizer's underlying `Math.random()` placeholder was left as
   cosmetic ambiance, but the new dedicated level meter is a genuine
   `AnalyserNode` reading.

## The one real technical constraint, surfaced rather than hidden

Browser `SpeechSynthesis` output is never routed through the Web Audio
graph — there is no API to measure it. This console's `AnalyserNode` can
only prove audio for what actually passes through `masterGain` (the
static bed, squelch, and the test tone). So:

- The **test tone** gives a fully *measured* "audible output verified"
  result — real RMS-over-noise-floor evidence, logged with the actual
  peak value.
- A **real spoken transmission** can only ever reach `unverified` for
  its final stage, explicitly labeled as such, with a tooltip explaining
  why. `onstart` firing proves the browser attempted playback, not that
  anything was heard. Overall Radio State never claims `LIVE` off of
  this alone.

This is the literal implementation of the packet's operating rule, not
just a status label.

## A real bug found and fixed during implementation

The first working version had a race: `transmitEntry()` calls
`resetAudioPath()` unconditionally, and this demo world produces real
content roughly every 1-3 seconds. Clicking Play Test Tone could have
its measured "audible: ok" result overwritten by the next real
transmission within milliseconds — the diagnostic log entry was always
correct, but the live status panel wasn't trustworthy to look at.

Fixed by having the test tone claim the same `state.speaking` /
`currentTransmissionScore` slot `livePump()` already respects (scored
`Infinity`, un-interruptible by any real content), explicitly
interrupting whatever might already be mid-flight first (a real
transmission's own pending completion timer fires independently of who
"owns" the speaking slot, and was found — via direct function-call
tracing — to silently release the lock if not explicitly cancelled), and
holding the result visible for ~1.8s after measurement before releasing
back to real content.

## Verification

Live, against `https://cameronlampley.com/toys/radio-console/`, via
headless-browser (Playwright) sessions this session:

- Full click-through of all three test controls; diagnostics log,
  content queue, and source tags all update correctly; zero console/page
  errors.
- Direct function-call tracing (`transmitEntry`, `completeTransmission`,
  `interruptCurrentTransmission`, `setSpeaking`, `resetAudioPath`,
  `setAudioPathStage`) with real timestamps, confirming the test-tone
  lock is claimed, holds for the full measurement + ~1.8s display
  window, then correctly releases to real content — not just inferred
  from screenshots.
- `node --check toys/radio-console/app.js` — syntax clean.
- `toys/radio-console/` and `web/toys/radio-console/` kept byte-identical
  throughout (the same drift this packet's own diagnostics would have
  caught, per `docs/engineering-orders/packets/ARCHITECTURE-ENGINE-1.0-ASSIGNMENT-ONE.md`).

## Known, accepted limitation

This test environment (headless Chromium, no OS-level TTS voices)
legitimately cannot produce spoken audio at all, so `RADIO FAULT — AUDIO
PATH FAULT` is the honest, correct steady-state reading here — not a
defect. A desktop browser with real TTS voices installed should reach
`RADIO LIVE` after one successful Play Test Tone click.
