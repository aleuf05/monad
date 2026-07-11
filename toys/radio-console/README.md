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

## Live Mode (FleetCore)

Every page load attempts a read-only WebSocket connection to `fleetcore-serve` (Admiral's call, 2026-07-11: live is the default now, no longer opt-in) — see `docs/architecture/fleetcore-api.md`. If one lands, event-driven chatter replaces the scripted random scheduler: transmissions fire only when a snapshot shows something actually happened — a vessel's status transition (underway, arrived, holding, ...) or an explicit `RecordWatchEvent` message — rather than on a random timer. The static bed, squelch pop, mute/volume, and channel filters are unchanged; only what triggers a transmission and what it says differs. There's no live "Weather" channel — FleetCore has no weather concept — so that channel simply produces nothing while live (still toggleable, just silent).

If nothing answers in time (no reachable `fleetcore-serve`, or the public reverse-proxy path isn't finished — see `docs/deployment.md`), this stays exactly what it always was: presentation layer, not world state, scripted chatter on a random timer, no FleetCore dependency. `?fleetcoreServer=ws://host:port/ws` overrides the server URL if the default (derived from the page's own origin) isn't right. Making the connection attempt unconditional rather than opt-in means a failed attempt now logs a browser-native console error no application code can suppress on any page load where FleetCore isn't reachable — an accepted tradeoff, not an oversight; see `docs/deployment.md` for why.

## Graceful degradation

- No `SpeechSynthesis` support, muted, or zero installed voices (common on minimal Linux desktops and headless/sandboxed environments — confirmed while building this) all fall back to the same timed visual cue instead of silently doing nothing: the transcript still updates, the signal meter still animates, and the "Transmitting…" indicator still times itself to roughly how long the line would take to speak.
- A safety timeout also clears the "Transmitting…" indicator if `SpeechSynthesisUtterance`'s `onend` event never fires at all (observed as a possibility in some sandboxed environments even when voices are reported available), so the UI can never get stuck mid-transmission.

## Not yet done

- No real broadcast source integration (the stretch goal in the original request) — deliberately decoupled so this works standalone regardless of whether that's ever built.
