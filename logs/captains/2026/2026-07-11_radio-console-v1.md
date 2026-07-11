# Radio Console v1 Watch Log

Date: 2026-07-11
Operator: Commander Claude, Engineering Watch
Requested by: Admiral C, Feature Request "Radio Console" (prestige/ambience)
Objective: implement v1 core scope — scripted/looping simulated chatter, console UI, volume/mute controls — as a standalone bridge instrument with no FleetCore dependency.

## Scope

Admiral C's request split scope into v1 (core: scripted/looping chatter, console UI, volume/mute), v2 (optional: chatter reflects live fleet state if FleetCore is available), and a stretch goal (real broadcast source, e.g. NPR, as a selectable channel). Asked which to start; directed to begin v1 now. This watch covers v1 only — v2 and the stretch goal are explicitly deferred, not attempted.

The request's own architectural notes were followed directly: ambience/presentation layer only, no FleetCore read or write, fits the toy model as a pure observer at most (v1 doesn't even observe — it's fully self-contained).

## Integration

- New toy at `toys/radio-console/`: `index.html`, `app.js`, `style.css`, `README.md`, reusing the same dark/teal/amber CSS custom-property palette as Periscope and FleetCore Live for visual consistency across instruments.
- A hand-authored bank of 18 scripted transmission lines across three channels (Fleet Comms, Weather, Traffic), deliberately reusing the exact vessel names and callsigns already established elsewhere in the project (`MONAD`, `SCOUT ALPHA/BRAVO/CHARLIE` from Fleet Motion/Periscope; `Dhow Lantern`, `Gulf Star`, `Pilot Amber`, `Coaster Qeshm` from `fleetcore/data/seed-world.json`) for continuity — not because v1 reads any of that data live, it's flavor text that happens to match the established world.
- Audio: Web Audio API for a continuous filtered-noise static bed (bandpass around 1500Hz) that ducks down while a transmission is active and rises during dead air, plus a short highpass-filtered noise burst as a squelch pop bracketing each transmission. `SpeechSynthesis` speaks each transmission's text aloud, with a per-speaker consistent voice assignment (hashing the speaker name into the available voice list) so "Scout Alpha" always sounds the same across transmissions.
- A scheduler picks a random transmission from the currently-monitored channels (toggleable chips, multi-select) every 6–16 seconds. Power must be explicitly turned on by a real click — required by browser autoplay policy for both `AudioContext` and `SpeechSynthesis`, and also just fits the console metaphor.
- Frequency readout is a fixed, non-interactive detail: 156.800 MHz, the real marine VHF channel 16 hailing/distress frequency — an authenticity touch, not a functional control.

## Caught during verification: silent degradation with zero TTS voices

Testing in this environment's headless Chromium found `speechSynthesis` exists (the API is present) but `getVoices()` returns zero voices — no system TTS backend installed. The first implementation only had a fallback for "no SpeechSynthesis API at all," so with the API present but voiceless, `speechSynthesis.speak()` silently did nothing: no audio, and no `onstart`/`onend` events ever fired, leaving the visual "Transmitting…" indicator permanently stuck on "Standing by…" even while transmissions were actively appearing in the transcript. Fixed by extending the fallback condition to also cover zero available voices, and added a timeout-based safety net that force-clears the "Transmitting…" indicator if the real speech events never fire at all, regardless of cause. A console this quiet in some environments and not others, with no visible indication of which state it's in, would have read as broken rather than working-but-silent.

## Verification

`node --check` on `app.js`. Playwright-driven, both desktop (1200×900) and mobile (390×844, no horizontal overflow at either) against a local server: Power On requires and respects the click-gesture requirement, `AudioContext` constructs successfully, forcing an immediate transmission (bypassing the 6–16s random scheduler for test speed) correctly appends a properly formatted transcript entry (channel tag, speaker, text, timestamp), toggling a channel chip updates the "Monitoring: N channels" readout, Mute toggles its own label, Power Off cleanly stops everything. Re-verified the speaking indicator specifically: with zero TTS voices (this environment), it now correctly shows "Transmitting…" for a duration estimated from the text length, then clears back to "Standing by…" on its own. Canvas signal meter confirmed to actually draw non-empty content while powered on. Zero console errors or warnings across every run.

## Follow-up

Not deployed to the public site as part of this watch — pending confirmation this is wanted publicly, since (unlike FleetCore Live) this plays audio automatically once powered on, which is a different kind of visitor experience to sign off on deliberately rather than assume. Not wired into Bridge Station's composited console; that's a real design decision (does Radio Console belong inside Bridge's iframe grid, or stay a separate standalone instrument like FleetCore Live) left open rather than decided unilaterally. v2 (live-fleet-state-aware chatter) and the real-broadcast stretch goal remain fully deferred per the original request's own priority note.
