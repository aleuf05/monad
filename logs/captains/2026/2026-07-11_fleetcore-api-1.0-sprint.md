# FleetCore API 1.0 Watch Log

Date: 2026-07-11
Operator: Commander Claude, Engineering Watch
Authority: Captain T, Command Intent Memo (per `Sprint.md`)
Objective: implement Engineering Packet "FleetCore API 1.0" — stand up FleetCore's live server as a proper JSON-over-HTTP read/write API with read-only-by-default access, closing the exact gap the prior watch's own engineering report flagged as a known limitation.

## Problem

`Sprint.md` landed in the repo (commit `f117dbf`, pushed independently of this watch's earlier work) after FleetCore's live server (`fleetcore-serve`) had already been built, verified, and deployed in an earlier watch this same day. Reading it after the fact rather than before meant reconciling an already-shipped implementation against a spec it wasn't written to, rather than building to spec from a blank slate.

Sprint.md's acceptance criteria, checked against what already existed:
- FleetCore maintains canonical world state — already true.
- A browser instrument retrieves that world through the API — already true (`toys/fleetcore-live/`).
- FleetCore updates the world deterministically — already true.
- Every connected instrument observes the same resulting state — already true (WebSocket broadcast).
- An operator command is accepted through the API — **only over WebSocket**, no plain HTTP write endpoint existed.
- **Read-only default for toys; explicit grant required for command authority — not true at all.** Any client that could open `/ws` could issue any command, exactly the gap flagged as a known limitation in the prior watch's engineering report ("Any client that can open the WebSocket can issue any command, including pausing the clock for everyone").

Deliverable 5 (a short API contract doc for future toy authors) also didn't exist yet.

## Flag for Captain T

Sprint.md lists "Networking beyond what v1 requires (no push/WebSocket commitment yet)" as explicitly out of scope. The WebSocket transport was already built, verified, and deployed before this packet was read — ripping it out now would regress a working, deployed feature to satisfy a scope line written against work that already exists and is in production use. It was kept. The JSON-over-HTTP contract Sprint.md actually specifies (`GET /snapshot`, new `POST /command`) was added as a first-class, independent transport alongside it, not built as a WebSocket-only workaround dressed up as HTTP. Per Sprint.md's own reporting instruction ("flag any point where a v1.0 constraint... blocks a bridge instrument's requirements — that's a command-intent question, not an implementation one"), this is flagged rather than silently decided. If the WebSocket transport should be removed to strictly match the packet, that's a call for Captain T, not one this watch made unilaterally.

## Integration

- `fleetcore/src/bin/serve.rs`: added `--command-token <token>` (server-wide, opt-in; omitted entirely means every write from every transport is rejected, unconditionally — not just "no token matches," but no code path that could accept one). New `POST /command` (HTTP, `Authorization: Bearer <token>`) and WebSocket `?token=` query param both check the same `AppState::authorized()`. A new `Connected { command_authority: bool }` message is sent once per WebSocket connection, immediately after connecting, so a client always knows its own authority level rather than inferring it from whether a command happens to work.
- Refactored the apply/persist/broadcast path into one shared `apply_and_broadcast()` used by both the HTTP and WebSocket write paths, so they can't drift in what "applying a command" means.
- `toys/fleetcore-live/`: added a password-type "Command Token" field and an "Authority" status readout. Pause/Resume/time-scale controls now require both a live connection *and* command authority to enable — previously they enabled on connection alone, which meant a read-only visitor would have seen clickable controls the server would just reject.
- New `docs/architecture/fleetcore-api.md` — Sprint.md's Deliverable 5, aimed at a future toy author, not at explaining FleetCore's internals.
- Caught and fixed separately, ahead of this token work: the server's `0.0.0.0` bind default (from the earlier watch, before any auth existed) was live on Granite with no local firewall (`ufw` disabled) when this watch began. Killed it, changed the default to `127.0.0.1` with an explicit `--bind-all` opt-out, rebuilt, and restarted loopback-only before continuing. This is documented in full in `fleetcore/ENGINEERING_REPORT.md` ("Caught During This Sprint").

## Verification

`cargo fmt --check`, `cargo clippy --all-targets -- -D warnings`, `cargo test` all clean. `curl`-verified all four `POST /command` outcomes (open read, 401 no auth, 401 wrong token, 200 correct token with the command visibly taking effect). A throwaway Node script exercised the WebSocket path with no token, a wrong token, and the correct token — the first two always got `command_authority: false` and a read-only rejection, the third got `command_authority: true` and the command applied. Separately confirmed that omitting `--command-token` entirely (not just presenting a non-matching one) leaves `POST /command` returning `401` for any bearer token presented — there's no half-configured state that accidentally leaves the gate open.

Installed Playwright's Chromium (cached from the earlier watch) and drove `toys/fleetcore-live/` against a scratch auth-enabled server twice: no token entered showed "Read-only" with Pause disabled and left unclicked; the correct token showed "Command" with Pause enabled, and clicking it paused the clock live. Zero console errors or warnings in either run.

Restarted the production `fleetcore-serve` process on Granite with the new binary (no `--command-token`, matching the read-only default) and confirmed via `/snapshot` that the real persisted world survived the restart with its tick count continuous, not reset.

## Follow-up

Recommended next direction is recorded in `fleetcore/ENGINEERING_REPORT.md`: per-token/per-client scoping (right now a token grants unrestricted authority over the entire `Command` surface, not a subset), and fixing error-reply targeting so a rejected or unauthorized command only replies to the connection that sent it rather than broadcasting to everyone connected. Deployment of the `--command-token` flag itself to Granite's systemd unit is deliberately left for Captain T to decide and apply — see `docs/deployment.md`'s "FleetCore Live Backend" section for the exact steps; the public deployment stays read-only until that decision is made.
