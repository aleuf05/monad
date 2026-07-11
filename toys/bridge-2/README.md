# Bridge Station 2.0

One page, one live view, one data source. A single WebSocket connection to `fleetcore-serve` feeds both a live fleet map and a live optics/bearing panel — there is exactly one `state.snapshot` object in `app.js`, and both panels render from it. That's the whole point: not two toys sharing a nav bar, but one instrument observing one world.

Built from `logs/captains/2026/2026-07-11_bridge-station-2-scope.md`'s "Bridge Station 2.0" scope packet. Deliberately a new, separate artifact — the existing `toys/bridge/` (Fleet Motion + Periscope + Radio Console, iframe-composited, `MonadFleetState`/localStorage-driven) is untouched and keeps running as-is.

## Run

1. Start FleetCore's live server (see `../../fleetcore/README.md`):

   ```sh
   cargo run --manifest-path fleetcore/Cargo.toml --bin serve -- --port 4771
   ```

2. Serve this directory (or the repository root):

   ```sh
   python3 -m http.server 8080
   ```

3. Open `http://localhost:8080/toys/bridge-2/`. It connects to `ws://<page-hostname>:4771/ws` by default; override with `?server=ws://host:port/ws` in the URL.

## What's different from `toys/bridge/`

- **Data source**: this page's map and optics panels read live vessel positions directly from FleetCore's `WorldSnapshot` over WebSocket. `toys/bridge/` composites three separate standalone toys (Fleet Motion, Periscope, Radio Console), each with its own rendering code and, for Fleet Motion, its own local physics simulation writing to `localStorage`.
- **No iframes**: both panels are rendered by this page's own `app.js`, not embedded standalone toys. This is a from-scratch renderer, not a wrapper.
- **No tabs, no extra toys, no write controls**: per the scope packet's "Out of Scope" — read-only observer, Fleet Motion + Periscope only, nothing else competing with the core view.

## Read-only by design

This page never sends a `Command` over the WebSocket and presents no controls that would. It connects without a `?token=`, so even if it tried, FleetCore would reject it (see `docs/architecture/fleetcore-api.md`, "Command Authority"). Watching, not touching, is the whole scope here.

## Known limitations

- Contact labels in the optics panel are decluttered by a simple screen-space collision offset (see `LABEL_COLLISION_PX` in `app.js`), not a true label-placement algorithm — dense contact clusters at certain bearings may still stack more rows than ideal.
- No visual asset investment (no photographic sea-plate, no vessel sprites) — flat canvas rendering only, matching "lean by default." `toys/periscope/`'s photographic/sprite work was deliberately not ported here.
- Internal-facing vs. public-facing is an open question per the scope packet itself — not deployed anywhere as of this build. See the watch log for what that would require (the same pending Caddy reverse-proxy step from FleetCore Live's own deployment).
