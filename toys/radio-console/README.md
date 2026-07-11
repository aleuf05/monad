# Radio Console

A bridge instrument for ambience, not for information. It plays scripted "in-world" radio chatter — fleet comms, weather, routine maritime traffic — through a console UI, spoken aloud via the browser's `SpeechSynthesis` API over a synthesized static bed and squelch pops built with the Web Audio API.

Requested as a prestige/ambience feature (see `logs/captains/2026/2026-07-11_radio-console-v1.md`): "giving Monad's bridge a lived-in, simulated presence" without requiring any real data feed.

## Run

Open `index.html` directly, or serve the repository root:

```sh
python3 -m http.server 8080
```

Then open `http://localhost:8080/toys/radio-console/`. Click **Power On** — browsers require a real user gesture before audio can play, so nothing happens automatically on load.

## What it does

- A bank of scripted transmission lines across three channels (Fleet Comms, Weather, Traffic), using the same vessel names and callsigns as the rest of Monad's world (`MONAD`, `SCOUT ALPHA/BRAVO/CHARLIE`, and the passive-traffic contacts from `fleetcore/data/seed-world.json` — `Dhow Lantern`, `Gulf Star`, `Pilot Amber`, `Coaster Qeshm`) for continuity, not because it reads that data live.
- A scheduler picks a random transmission from the currently-monitored channels every 6–16 seconds, appends it to the transcript, and speaks it aloud (assigning each named speaker a consistent voice, if more than one is available, so "Scout Alpha" always sounds the same).
- A continuous filtered-noise static bed plays under everything, ducking down while a transmission is "on the air" and rising again during dead air — a squelch pop brackets each transmission.
- Channel chips (multi-select) control which categories are monitored; Volume and Mute control the Web Audio output and speech volume together.

## No FleetCore dependency

This is presentation layer, not world state — it does not read from or write to FleetCore, and works identically whether a live FleetCore server exists, is unreachable, or was never built at all. If a later version wants chatter to reference live fleet state (e.g. an actual position report pulled from a running world), that's an additive read-only consumer of `docs/architecture/fleetcore-api.md`'s `GET /snapshot`, not a change to this toy's core model.

## Graceful degradation

- No `SpeechSynthesis` support, muted, or zero installed voices (common on minimal Linux desktops and headless/sandboxed environments — confirmed while building this) all fall back to the same timed visual cue instead of silently doing nothing: the transcript still updates, the signal meter still animates, and the "Transmitting…" indicator still times itself to roughly how long the line would take to speak.
- A safety timeout also clears the "Transmitting…" indicator if `SpeechSynthesisUtterance`'s `onend` event never fires at all (observed as a possibility in some sandboxed environments even when voices are reported available), so the UI can never get stuck mid-transmission.

## Not yet done

- Not wired into Bridge Station's composited Live Console — it's a standalone instrument for now, matching how `toys/fleetcore-live/` shipped standalone before any Bridge integration decision was made.
- No live-fleet-state-aware chatter (the v2 stretch goal in the original request).
- No real broadcast source integration (the stretch goal in the original request) — deliberately decoupled so this works standalone regardless of whether that's ever built.
