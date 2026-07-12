# FleetCore Control Center LAN Deployment Watch Log

Date: 2026-07-12
Operator: Lt. cgl
Objective: get FleetCore Control Center fully live with write access on the LAN, per direct instruction to proceed without further gating on the public-exposure question raised in the prior watch.

## Context

While confirming the public deployment's writes were gated correctly, found that `bridge-3-0-lan` (the LAN dev command token, committed in plaintext across this repo's own docs and watch logs) already grants full command authority through the now-live public `wss://cameronlampley.com/monad/fleetcore-ws/ws` reverse proxy — confirmed via a read-only WebSocket handshake check (`command_authority: true`), no command sent. `docs/deployment.md`'s own Bridge Station 3.0 section had already flagged this exact risk and said to rotate before finishing the public proxy step; that didn't happen. Raised this to the Admiral, who directed: proceed with the LAN deployment as asked, leave the token/exposure question alone for now.

## LAN Deployment

Discovered the actual LAN web server (`python3 -m http.server 8090 --bind 0.0.0.0`, PID confirmed running) serves a dedicated `web-lan/` directory at the repo root, not `web/` as `docs/deployment.md` previously (incorrectly) described — `web-lan/` currently held only `toys/bridge-2/` and `toys/shared/`. Fixed that stale doc claim while adding the new entry.

- `web-lan/toys/fleetcore-control/` (new): copy of `toys/fleetcore-control/` (`app.js`, `index.html`, `style.css`).
- `web-lan/toys/fleetcore-control/index.html`: `#serverUrl` defaults to `ws://192.168.0.100:4771/ws` (the LAN IP, matching `fleetcore-serve`'s `--bind-all` listener) rather than `localhost` or the public `wss://` path — same divergence pattern already used for the public copies, applied for the LAN context instead.
- `docs/deployment.md`: corrected the `web/` → `web-lan/` factual error, added a `web-lan/toys/fleetcore-control/` entry matching the existing format, and updated the Bridge Station 2.0 bind-risk paragraph to stop describing the token exposure as hypothetical ("if a `--command-token` is ever added") since one already exists and already applies beyond the LAN.

## Verification

Playwright against `http://localhost:8090/toys/fleetcore-control/` (this box is on the same network the LAN server binds):

- Page loads, `#serverUrl` correctly defaults to `ws://192.168.0.100:4771/ws`.
- Entered `bridge-3-0-lan`, connected: `Live` / `Command` authority, saw the real world's 15 vessels.
- Fired the Distress Call scenario: vessel count went 15→16, a real write against the shared FleetCore world, confirming this isn't just a UI state change.
- Zero console/page errors.

## Not done

- Did not rotate, remove, or otherwise change the `bridge-3-0-lan` token or the public reverse-proxy exposure found in the prior watch — explicitly deferred per direction, not forgotten. `docs/deployment.md` now says so plainly rather than continuing to describe the old, now-inaccurate "read-only unless LAN" risk model.
- Did not link FleetCore Control Center from `toys/bridge-2/`'s own UI — it has no links to any other toy today, and adding that pattern wasn't part of this ask.

## Updated

- `web-lan/toys/fleetcore-control/index.html` (new)
- `web-lan/toys/fleetcore-control/app.js` (new)
- `web-lan/toys/fleetcore-control/style.css` (new)
- `docs/deployment.md`
