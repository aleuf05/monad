# FleetCore v3 Engineering Report

## Summary

FleetCore v1 proved the deterministic world model works and replays exactly, explicitly scoped to never run live. FleetCore v2 lifted that restriction: `fleetcore-serve` (`src/bin/serve.rs`) wraps the same library in a tokio runtime, ticking a `World` in real time and serving it over HTTP and WebSocket.

FleetCore v3 implements `Sprint.md` ("Engineering Packet: FleetCore API 1.0"), a mission packet that reached this repo after v2 was already built and deployed. Its acceptance criteria are now met: `GET /snapshot` and a new `POST /command` form a plain JSON-over-HTTP read/write API, and — its sharpest requirement — the server is **read-only by default**, with **explicit grant required for command authority** via a `--command-token` flag. Before this, any client that could open the WebSocket could issue any command, including pausing the world for every connected visitor; this was flagged as a known limitation in the v2 report and is now closed. `docs/architecture/fleetcore-api.md` is the API contract doc Sprint.md's Deliverable 5 asked for, aimed at a future toy author who doesn't need to read `World`'s internals.

**Flag for Captain T** (per Sprint.md's own reporting instruction to flag scope conflicts rather than resolve them silently): Sprint.md lists "Networking beyond what v1 requires (no push/WebSocket commitment yet)" as explicitly out of scope. FleetCore v2's WebSocket transport was already built, verified, and deployed to `toys/fleetcore-live/` before this packet was read. Removing it now would regress a working, deployed feature to satisfy a scope line for functionality that already exists and is in use. It was kept, and the plain JSON-over-HTTP contract Sprint.md actually asks for (`GET /snapshot`, `POST /command`) was added alongside it as a first-class, independent transport — not a WebSocket-only workaround. If that reconciliation is wrong, it's a command-intent question, not one this report can resolve on its own.

## Created Artifacts

- `docs/architecture/fleetcore-api.md`

## Modified Artifacts

- `fleetcore/src/bin/serve.rs`
- `fleetcore/README.md`
- `fleetcore/ENGINEERING_REPORT.md`
- `toys/fleetcore-live/index.html`
- `toys/fleetcore-live/app.js`
- `toys/fleetcore-live/style.css`
- `toys/fleetcore-live/README.md`

## Implementation Notes

- `AppState` gained `command_token: Option<Arc<str>>` and an `authorized(&self, presented: Option<&str>) -> bool` method: `None` for either side of the comparison (no token configured, or none presented) is always unauthorized — there is no way to be "open" by omission. `Arc<str>` rather than `String` because the token is cloned into every `AppState` handed to every connection handler but never mutated.
- **HTTP write path:** `POST /command` reads `Authorization: Bearer <token>` via a `bearer_token(&HeaderMap)` helper, checks it against `state.authorized()`, and on success runs the same `apply_and_broadcast()` helper the WebSocket path uses — the two transports cannot drift in what "applying a command" means, because they share one function. Responses: `401` unauthorized, `400` invalid JSON, `422` a valid command `World::apply_command` rejected, `200` with the new `WorldSnapshot` on success.
- **WebSocket auth:** the token travels as a `?token=` query parameter on the `/ws` connect URL, extracted via an `axum::extract::Query<WsAuthParams>` extractor, checked once at connection time (not per-message). The result is captured in a `bool` closed over by that connection's `handle_socket`/`handle_client_message` calls. A new `ServerMessage::Connected { command_authority: bool }` is sent once, immediately after connecting and before the first snapshot, so a client knows its own authority level without inferring it from whether a command happens to succeed.
- An unauthorized WebSocket connection still receives every broadcast snapshot (reads stay open) — only `handle_client_message` short-circuits, replying with a plain-language `error` message ("read-only connection: reconnect with a valid ?token= to gain command authority") instead of attempting to parse or apply anything it sends.
- `--bind-all` was added alongside the token work, not because Sprint.md asked for it, but because building and testing the token gate meant running the server with a real secret for the first time — which made the pre-existing `0.0.0.0` bind (a leftover default from v2, never actually exposed publicly) impossible to justify leaving in place a moment longer. Default is now `127.0.0.1`; `--bind-all` opts back into `0.0.0.0` explicitly. See "Caught During This Sprint" below — this was found and fixed before the token gate existed, as a prerequisite to trusting the token gate at all.
- `toys/fleetcore-live/`'s UI gained a password-type "Command Token" field and an "Authority" status readout (`#authorityStatus`, "Read-only" or "Command"). Control-enabled state (`updateControlsEnabled()`) now requires both a live connection *and* command authority — previously it only required a connection, which meant a read-only visitor would have seen live-looking, clickable Pause/Time-scale controls that the server would silently reject. `commandAuthority` is set from the `Connected` message, not inferred.

## Caught During This Sprint: 0.0.0.0 bind before any auth existed

Deploying FleetCore Live's backend for the first time (before this sprint's token work began), the server was started with its v2 default bind of `0.0.0.0` on a host (Granite) with no local firewall (`ufw` disabled, confirmed via `ufw status` / `/etc/ufw/ufw.conf`). At that point there was no `--command-token` yet — meaning an unauthenticated, fully-open command channel would have been reachable from outside the host the instant any firewall/NAT in front of it allowed the port through, which could not be verified from Granite alone (the public domain routes through a separate rock64 host whose port-forwarding rules aren't visible here). The process was killed within the same watch before any browser ever connected to it publicly, the code changed to bind `127.0.0.1` by default, and the process restarted loopback-only before deployment continued. This predates and is independent of the `--command-token` work above; token auth on top of a loopback-only bind is defense in depth, not a replacement for it — a public bind with a token would still trust the reverse proxy/network path entirely, which isn't yet reviewed for this deployment.

## Validation Performed

- `cargo fmt --check`, `cargo clippy --all-targets -- -D warnings`, `cargo test` (existing `determinism.rs` unaffected) all clean after the auth changes, same as after the v2 changes.
- HTTP: `curl`-verified all four `POST /command` outcomes against a scratch server started with `--command-token secret123`: `GET /snapshot` with no auth succeeds; `POST /command` with no `Authorization` header returns `401`; with the wrong token returns `401`; with the correct token returns `200` and the command visibly takes effect (confirmed clock state flips to `paused` in a follow-up `GET /snapshot`).
- WebSocket: a throwaway Node script (Node 24's built-in `WebSocket`) connected three times — no token, wrong token, correct token — and for each: read the `connected` message's `command_authority` value, then always attempted to send a command regardless. No-token and wrong-token connections both reported `command_authority: false` and got the read-only `error` message back, never applying the command. The correct-token connection reported `command_authority: true` and the command was applied (`time_scale` changed to `7` in the next broadcast).
- Also verified against a server started with **no** `--command-token` flag at all (the true out-of-the-box default, not just an unmatched token): `POST /command` with an arbitrary bearer token still returned `401` — confirming there's no way to accidentally leave the gate open by only half-configuring it.
- Browser: installed Playwright's Chromium (already cached from the v2 sprint), drove `toys/fleetcore-live/` against a scratch auth-enabled server twice — once with no token entered, once with the correct token. Read-only run: "Authority" showed "Read-only," the Pause button was disabled, and it was not clicked. Authorized run: "Authority" showed "Command," the Pause button was enabled, clicking it paused the clock and the UI reflected it. Zero console errors or warnings across both runs.
- Restarted the actual production `fleetcore-serve` process on Granite with the new binary (no `--command-token`, matching the read-only default) and confirmed via its own `/snapshot` that the real persisted world (tick count continuous across the restart, not reset) survived the upgrade.

## Known Limitations

- The `--command-token` gate is all-or-nothing: no per-client permissions, no scoping to a subset of `Command` variants, no rate limiting, and no revocation short of restarting the process with a different token.
- Error replies (both "invalid command" and "read-only, unauthorized") still go out on the broadcast channel to every connected client, not just the one that triggered them — a pre-existing v2 simplification, not new to this sprint, still not fixed.
- No reconnect-safe command queue; a write attempted while briefly disconnected is dropped, matching v2.
- Event-log growth remains unbounded per tick of uptime, matching v2.
- Fleet Motion, Periscope, and Bridge still run their own client-side simulations and don't talk to FleetCore; unchanged from v2.

## Recommended Next Direction

1. Per-client/per-token scoping (e.g. a read/pause-only token distinct from a full-control token) if multiple people need different levels of access to the same live world.
2. Fix error-reply targeting so a rejected or unauthorized command only replies to its own connection, not every connected client.
3. Everything already listed in the v2 report's "Recommended FleetCore v3 Direction" that this sprint didn't address (event-log rotation, an existing toy becoming a live FleetCore client) still applies — renumber as v4 direction now that v3 has shipped.
