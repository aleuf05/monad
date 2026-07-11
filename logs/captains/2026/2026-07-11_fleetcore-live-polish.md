# FleetCore Live Polish Pass Watch Log

Date: 2026-07-11
Operator: Commander Claude, Engineering Watch
Objective: fix the one correctness item the FleetCore API 1.0 sprint left open (error replies broadcast to every client instead of just the sender), and give `toys/fleetcore-live/` — the newest, plainest-looking toy, never given a mobile pass — a visual/UX polish stage.

## Integration

- `fleetcore/src/bin/serve.rs`: each WebSocket connection now gets its own `mpsc::unbounded_channel`, merged with its broadcast subscription via `tokio::select!`. `handle_client_message`/`send_error` take that connection's sender directly instead of going through `AppState`'s shared broadcast channel, so a rejected or unauthorized command only replies to whoever sent it. Successful commands are unaffected — they still broadcast to everyone, correctly.
- `toys/fleetcore-live/`: added a pulsing live-connection dot, a one-shot amber flash on the Tick readout whenever the tick actually changes, and a visible auto-dismissing banner for rejected commands (previously `console.warn`-only, invisible to anyone without devtools open).
- Checked the existing mobile layout at 390×844 before touching anything: no horizontal overflow, the status-strip grid already used `auto-fit` and wrapped cleanly. Nothing needed fixing — this closes the "no mobile pass" gap the earlier engineering report flagged, with the finding being that it was already fine, not that something got repaired.

## Verification

`cargo fmt --check`, `cargo clippy --all-targets -- -D warnings`, `cargo test` clean. A two-client WebSocket script (an unauthorized "victim" that only watches, an unauthorized "offender" that deliberately sends a doomed command) confirmed the victim's message log never contains the offender's resulting error — targeting works. Playwright confirmed the live dot gains its active class on connect, the tick-pulse class appears immediately after a tick change, and the feedback banner shows on trigger and clears itself after 5 seconds. Restarted the production `fleetcore-serve` process with the fixed binary and confirmed the real persisted world survived (tick count continuous, not reset). Redeployed `web/toys/fleetcore-live/` and reconfirmed both Granite-local and `https://cameronlampley.com/monad/toys/fleetcore-live/` serve the updated client. Zero console errors or warnings across every browser check in this pass.

## Follow-up

None new. Existing recommended next direction (per-token scoping, event-log rotation, an existing toy becoming a live FleetCore client) is unchanged from the prior watch log.
