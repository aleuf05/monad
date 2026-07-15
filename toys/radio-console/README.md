# Radio Console

A bridge instrument, fully FleetCore-connected: it speaks real fleet chatter — vessel status transitions, explicit watch notes — through a console UI, spoken aloud via the browser's `SpeechSynthesis` API over a synthesized static bed and squelch pops built with the Web Audio API. No scripted fallback: while disconnected from `fleetcore-serve`, the console shows "Offline — reconnecting" rather than substituting invented chatter.

Originally requested as a prestige/ambience feature (see `logs/captains/2026/2026-07-11_radio-console-v1.md`) with a scripted fallback for when no data feed was available; the fallback was removed (Admiral's call, ambitious-scope pass) so the instrument never presents invented chatter as real.

## Run

Open `index.html` directly, or serve the repository root:

```sh
python3 -m http.server 8080
```

Then open `http://localhost:8080/toys/radio-console/`. Click **Power On** — browsers require a real user gesture before audio can play, so nothing happens automatically on load.

## What it does

- Speaks real fleet chatter through a console UI, using the same vessel names and callsigns as the rest of Monad's world (`MONAD`, `SCOUT ALPHA/BRAVO/CHARLIE`, and the passive-traffic contacts from `fleetcore/data/seed-world.json` — `Dhow Lantern`, `Gulf Star`, `Pilot Amber`, `Coaster Qeshm`).
- Transmissions fire only when a live FleetCore snapshot shows something actually happened — a vessel's status transition (underway, arrived, holding, ...) or an explicit `RecordWatchEvent` message — never on a random timer, never invented.
- A filtered-noise static bed plays only while a transmission is "on the air" (ducked quiet under the voice), and stays silent — squelch closed — during dead air, like a real monitored channel. A squelch pop marks the transmission ending (PTT release).
- Channel chips (multi-select) control which categories are monitored; Volume and Mute control the Web Audio output and speech volume together.
- Station chips apply a per-station scope filter before anything airs: Bridge hears everything, Traffic only hears traffic-side observations, and Weather stays effectively silent because FleetCore has no weather model.

## Live connection (FleetCore) — required, not optional

Every page load opens a WebSocket to `fleetcore-serve` (see `docs/architecture/fleetcore-api.md`) and keeps retrying with backoff until it lands — there is no scripted mode to fall back to. Once connected, transmissions fire only when a snapshot shows something actually happened — a vessel's status transition (underway, arrived, holding, ...) or an explicit `RecordWatchEvent` message. The static bed, squelch pop, mute/volume, and channel filters work the same regardless of connection state. There's no live "Weather" channel — FleetCore has no weather concept — so that channel simply produces nothing while connected (still toggleable, just silent).

While disconnected (no reachable `fleetcore-serve`, or the public reverse-proxy path isn't finished — see `docs/deployment.md`), the console shows **"Offline — reconnecting"** and stays silent — it does not substitute scripted chatter. `?fleetcoreServer=ws://host:port/ws` overrides the server URL if the default (derived from the page's own origin) isn't right. A failed connection attempt logs a browser-native console error no application code can suppress — an accepted tradeoff, not an oversight; see `docs/deployment.md` for why.

## Graceful degradation

- No `SpeechSynthesis` support, muted, or zero installed voices (common on minimal Linux desktops and headless/sandboxed environments — confirmed while building this) all fall back to the same timed visual cue instead of silently doing nothing: the transcript still updates, the signal meter still animates, and the "Transmitting…" indicator still times itself to roughly how long the line would take to speak.
- A safety timeout also clears the "Transmitting…" indicator if `SpeechSynthesisUtterance`'s `onend` event never fires at all (observed as a possibility in some sandboxed environments even when voices are reported available), so the UI can never get stuck mid-transmission.

## Not yet done

- No real broadcast source integration (the stretch goal in the original request) — deliberately decoupled so this works standalone regardless of whether that's ever built.
