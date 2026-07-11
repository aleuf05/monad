# FleetCore Live Server Watch Log

Date: 2026-07-11
Operator: Lt. cgl
Objective: give FleetCore a real live serving mode (WebSocket + HTTP) instead of only exporting static JSON, and ship a browser client that proves it — Monad's first running backend process instead of a static file tree.

## Problem

FleetCore v1 was explicitly scoped to never run live: its own README said "FleetCore v1 does not implement networking... WebSockets," and its engineering report's own "Recommended v2 Direction" said to keep networking deferred until the file-contract integration was proven. That integration (Fleet Motion -> `MonadFleetState` -> Periscope/Bridge, landed across `7003852` and the Bridge Mk III sprint) is now proven and deployed. Meanwhile every "shared" state in Monad is still three independent browser-side simulations gluing themselves together through `localStorage` polling in one tab — there is no real shared world, just an illusion of one. FleetCore's own library (`World`, `Command`, `snapshot`, `persistence`) was already cleanly separated from its CLI's I/O layer, which made it a natural candidate to wrap in a live process without touching any simulation logic.

## Integration

- Added `fleetcore/src/bin/serve.rs`, a second binary (`fleetcore-serve`) sharing the existing library crate. Holds one `World` in `Arc<Mutex<...>>`, ticks it once per `--tick-ms` (default 1000ms) via the same `apply_command(Command::Step { ticks: 1 })` path the CLI's `step` command already used, and broadcasts a fresh `WorldSnapshot` to every connected WebSocket client after each tick or applied command.
- `GET /snapshot` (CORS-open) and `GET /ws` (WebSocket). A client sends the existing tagged `Command` JSON shape over the socket (e.g. `{"type":"pause-clock"}`) to mutate the world; the server replies with `{"type":"error","message":"..."}` on a bad command instead of dropping the connection.
- Added `tokio`, `axum` (`ws` feature), and `futures-util` to `fleetcore/Cargo.toml` — no `tower-http`; CORS on `/snapshot` is one manually attached header, and `/ws` doesn't need it since WebSocket connections aren't subject to the browser's same-origin policy.
- Persistence cadence deliberately differs from the CLI: `save_world` runs every tick (cheap, single file, atomic write), but numbered checkpoints and the on-disk `snapshots/snapshot.json` export only run every 60 ticks, so a server left running doesn't flood the checkpoints directory at one-tick-per-second.
- Added `toys/fleetcore-live/`, a new standalone toy: a Leaflet map plus vessel list and watch-event log, driven entirely by server-pushed snapshots with no local simulation of its own — unlike every other toy in the repo. Includes Pause/Resume and time-scale controls that send `Command`s back over the socket, and reconnect-with-backoff on disconnect.
- Left Fleet Motion, Periscope, and Bridge untouched. `fromFleetCoreSnapshot()` in `toys/shared/fleet-state.js` remains unused; wiring an existing toy to FleetCore instead of its own physics loop was scoped out as a v3 follow-up rather than risking a regression in a toy that's already live on the public site (this was an explicit operator decision, not a default — see engineering report).

## Verification

No Rust toolchain existed in this environment. Installed one via `rustup` into `~/.cargo` (user-space, no sudo — `apt`'s cargo/rustc needed a password this session didn't have). Confirmed the pre-existing crate still built before changing anything.

After adding the server: `cargo fmt --check` (found and fixed one diff), `cargo clippy --all-targets -- -D warnings` (clean), `cargo test` (the existing `determinism.rs` test still passes unmodified).

Started `fleetcore-serve` against a scratch state directory. `curl http://127.0.0.1:4771/snapshot` returned a valid snapshot with the tick advancing between calls. Wrote a throwaway Node script using Node 24's built-in `WebSocket` client to drive the `/ws` protocol directly: initial snapshot on connect, `pause-clock` froze `tick` across subsequent broadcasts, `set-time-scale` changed `time_scale` in the next snapshot, `resume-clock` un-froze it, and a deliberately invalid command (`set-route` for an unknown vessel id) came back as a clean `{"type":"error",...}` rather than closing the socket. Confirmed `world.json` and `events.jsonl` were being written to the scratch directory throughout.

Installed Playwright's Chromium (browser binary only; `--with-deps` needed `sudo` this session didn't have) and drove `toys/fleetcore-live/` end-to-end against the running server: link status reached "Live", 8 vessel markers rendered matching the seed world (flagship + 3 scouts + 4 passive contacts), clicking a vessel in the list highlighted it and opened its map popup, Pause held the tick number steady across a 2.5s wait, and Resume with time scale 10 advanced the tick again afterward. Captured all browser `console` and `pageerror` events across the run: none were emitted.

## Follow-up

Recommended v3 direction (recorded in `fleetcore/ENGINEERING_REPORT.md`): make Fleet Motion a live-mode FleetCore client using its existing `persistenceSuspended` kill switch, so Periscope and Bridge inherit real multi-tab/multi-device sync for free without any changes of their own. Also flagged: unbounded event-log growth on a long-running server, and no auth on the live server's write path (any connected client can pause the fleet for everyone).
