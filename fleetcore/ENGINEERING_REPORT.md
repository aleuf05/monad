# FleetCore v2 Engineering Report

## Summary

FleetCore v1 proved that the deterministic world model (`World`, `Command`, `snapshot`, `persistence`) works and replays exactly. It was explicitly scoped to never run as a live process — "FleetCore v1 does not implement networking... WebSockets" was a stated non-goal.

FleetCore v2 lifts that restriction. A new binary, `fleetcore-serve` (`src/bin/serve.rs`), wraps the same library in a tokio runtime: it holds one `World` in memory, ticks it in real time, and serves it over HTTP (`GET /snapshot`) and WebSocket (`GET /ws`) so any number of browsers can watch — and, by sending a `Command` over the socket, mutate — one canonical world at once. This is the first time Monad has a real backend process instead of a static file tree. A new reference client, `toys/fleetcore-live/`, consumes it: a Leaflet map plus vessel list and watch-event log driven entirely by server-pushed snapshots, with no local simulation of its own.

The CLI (`src/main.rs`) is unmodified. Both binaries share the same library crate; the live server does not reimplement any simulation logic.

## Created Artifacts

- `fleetcore/src/bin/serve.rs`
- `toys/fleetcore-live/index.html`
- `toys/fleetcore-live/app.js`
- `toys/fleetcore-live/style.css`
- `toys/fleetcore-live/README.md`

## Modified Artifacts

- `fleetcore/Cargo.toml` (added `tokio`, `axum`, `futures-util`)
- `fleetcore/Cargo.lock`
- `fleetcore/README.md`
- `fleetcore/ENGINEERING_REPORT.md`

## Implementation Notes

- `AppState` (`Arc<Mutex<World>>` + `Arc<StorePaths>` + a `tokio::sync::broadcast::Sender<String>`) is shared across the tick loop and every WebSocket connection.
- The tick loop runs on a `tokio::time::interval` (default 1000ms, `--tick-ms`), and only advances the world when `world.clock.is_running()` — matching `pause-clock`/`resume-clock` semantics that already existed in `World::apply_command`. Each tick calls `apply_command(Command::Step { ticks: 1 })`, the same call path the CLI's `step`/`run` commands use, so a tick from the live server produces an indistinguishable `Event` from a CLI-driven one.
- Persistence cadence is deliberately different from the CLI's per-command persistence: `save_world` (a single small file, atomic tmp+rename) runs every tick, but `save_checkpoint` (a new numbered file) and `write_snapshot` (the on-disk `snapshots/snapshot.json` export) only run every 60 ticks. At 1 tick/second, the CLI's original per-command cadence would write a new checkpoint file once a second forever; the live server checkpoints roughly once a minute instead. `events.jsonl` still gets one line per tick, same as the CLI would for an equivalent number of `step 1` calls — event-log growth at ~1 line/second was accepted as reasonable for a prototype/demo server rather than solved with log rotation.
- Wire protocol: server -> client messages are tagged `{"type":"snapshot","snapshot":{...}}` or `{"type":"error","message":"..."}`; client -> server messages are a raw `Command` JSON object using the same `#[serde(tag = "type", rename_all = "kebab-case")]` shape the CLI already parses positional arguments into (e.g. `{"type":"set-time-scale","scale":5}`). No new command vocabulary was introduced — the live server is a new transport for the existing `Command` enum, not a new command surface.
- A malformed or rejected command (e.g. an unknown vessel id) returns an `error` message over the broadcast channel rather than closing the connection or panicking; `World::apply_command`'s existing `Result<Event, String>` already carried enough information for this.
- No CORS middleware dependency was added. WebSocket connections are not subject to the browser's CORS/same-origin policy, so `/ws` needed nothing. `GET /snapshot` gets a manually attached `Access-Control-Allow-Origin: *` header on the response tuple instead of pulling in `tower-http`.
- `toys/fleetcore-live/` intentionally does not go through `MonadFleetState`/localStorage or `fromFleetCoreSnapshot()` — it renders `WorldSnapshot` directly. Fleet Motion, Periscope, and Bridge are untouched by this sprint; wiring one of them to consume the live server instead of running its own local physics loop is out of scope here (see Recommended v3 Direction).

## Validation Performed

- No Rust toolchain was present in this environment; installed one via `rustup` (user-space, `~/.cargo`, no sudo) since `apt`'s cargo/rustc required a password this session didn't have.
- Ran `cargo build` on the pre-existing crate first to confirm the v1 baseline still compiled before changing anything.
- Ran `cargo fmt --check` (found and fixed one formatting diff in the new file), `cargo clippy --all-targets -- -D warnings` (clean), and `cargo test` (the existing `determinism.rs` integration test still passes) after adding the server.
- Started `fleetcore-serve` against a scratch `--state-dir` and confirmed with `curl http://127.0.0.1:4771/snapshot` that it returns a valid `WorldSnapshot` and the tick advances between requests.
- Wrote a throwaway Node script using Node 24's built-in `WebSocket` client to drive the `/ws` protocol directly: confirmed the initial snapshot arrives on connect, `pause-clock` freezes `tick` in subsequent broadcasts, `set-time-scale` changes `time_scale` in the next snapshot, `resume-clock` un-freezes it, and a deliberately invalid command (`set-route` for an unknown vessel id) returns `{"type":"error",...}` instead of dropping the connection.
- Confirmed `world.json` and `events.jsonl` were being written to the scratch state directory during the run.
- Installed Playwright's Chromium (browser binary only, no `--with-deps`; system package install via `sudo` wasn't available) and drove `toys/fleetcore-live/` end-to-end against the running server: confirmed the link status reaches "Live", 8 vessel markers render on the map matching the seed world's flagship/3 scouts/4 passive contacts, clicking a vessel in the list highlights it and opens its map popup, clicking Pause holds the tick number steady across a 2.5s wait, and clicking Resume with time scale set to 10 advances the tick again. Captured all `console` and `pageerror` events: none were emitted.

## Known Limitations

- The live server holds exactly one `World` per process: no multi-world routing, no authentication, no per-client permissions or rate limiting. Any client that can open the WebSocket can issue any command, including pausing the clock for everyone.
- No reconnect-safe command queue: a command sent while briefly disconnected is simply dropped (the browser client already implements reconnect-with-backoff for the read path, but there's no retry for in-flight writes).
- `--tick-ms` and the seed's `tick_duration_seconds` are independent knobs that happen to both default to 1000ms/1s; nothing enforces they stay related.
- Event-log growth is unbounded (~1 line/tick/second of uptime) — fine for a prototype/demo run, not for a long-lived deployment.
- `toys/fleetcore-live/` has no mobile-specific layout pass beyond the CSS grid's single-breakpoint stack, unlike Bridge's dedicated mobile verification.
- Fleet Motion, Periscope, and Bridge still run entirely on their own client-side simulations; none of them talk to FleetCore. `fromFleetCoreSnapshot()` in `toys/shared/fleet-state.js` remains unused.

## Recommended FleetCore v3 Direction

1. Pick one existing toy (Fleet Motion is the obvious candidate — it already owns "sole writer" status in the `MonadFleetState` contract) and make it a live-mode FleetCore client: suspend its local physics loop (`persistenceSuspended` already exists as a kill switch) when a FleetCore server is reachable, and relay incoming snapshots through `fromFleetCoreSnapshot()` into `MonadFleetState.write()` so Periscope and Bridge inherit live sync for free without any changes of their own.
2. Add a bounded event-log strategy (rotation or periodic compaction into a checkpoint) before running the live server unattended for long periods.
3. Add minimal auth or a read-only mode for public deployment — right now anyone who can reach `/ws` can pause the fleet.
