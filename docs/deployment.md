# Monad Deployment

Granite serves the Monad LAN site through Caddy.

## Paths

- Granite repo path: `~/dev/monad`
- Source web bundle: `web/`
- Live web root: `/var/www/monad`
- Deployment command: `scripts/deploy-web.sh`

## Deployment

Run the deploy script from the Monad repo on Granite:

```sh
scripts/deploy-web.sh
```

The script copies `web/` to `/var/www/monad/` with `rsync --delete`, validates the Caddy config, reloads Caddy only after validation succeeds, and checks `http://localhost/`.

## Doctrine

- Git carries source.
- `/var/www/monad` is deployed output.
- Caddy root should remain `/var/www/monad`.
- The Portainer reverse proxy path must not be disturbed.
- Do not edit the live web root by hand when the repo copy can be deployed instead.

## Public Artifacts

Interactive artifacts that must be reachable under `https://cameronlampley.com/monad/` live inside `web/toys/`. Each is a plain copy of the matching `toys/<name>/` source directory (runtime files only — READMEs, engineering reports, and other docs stay in the repo and are not copied). Re-copy the relevant source directory into `web/toys/<name>/` before running `scripts/deploy-web.sh` whenever that toy changes; `web/toys/` does not update itself.

- `web/toys/fleet-motion/` — Fleet Motion Mk2, copied from `toys/fleet-motion/`. Depends on `web/toys/shared/fleet-state.js`.
- `web/toys/periscope/` — Periscope Station, copied from `toys/periscope/` (`app.js`, `index.html`, `style.css`, and only the two asset files `ASSET_PATHS` actually loads: `assets/backgrounds/sea-horizon-mk2.png`, `assets/sprites/scout-alpha.png`). Depends on `web/toys/shared/fleet-state.js`.
- `web/toys/bridge/` — Bridge Station's Live Console, copied from `toys/bridge/`, **with one intentional divergence from source**: the Watchbook tab's panel is not an iframe pointing at a Watchbook instance (Watchbook is not deployed publicly — see below) but a static message linking to `web/logs.html`. If `toys/bridge/index.html`'s Watchbook panel markup changes, re-apply that patch by hand rather than doing a raw copy.
- `web/toys/shared/fleet-state.js` — the `MonadFleetState` contract, copied from `toys/shared/fleet-state.js`. Fleet Motion, Periscope, and Bridge Station all depend on this being present and in sync with the source; a stale copy silently breaks cross-instrument selection sync (this happened once — `web/toys/fleet-motion/` sat un-refreshed since the `7003852` schema-v2 refactor until it was caught during the Bridge Station Mk III deploy).
- `web/toys/fleetcore-live/` — copied from `toys/fleetcore-live/`, **with one intentional divergence from source**: `index.html`'s default `#serverUrl` value is `wss://cameronlampley.com/monad/fleetcore-ws/ws` (the public reverse-proxy path below) instead of `ws://localhost:4771/ws`. Unlike every other public artifact here, this one doesn't work from a plain file copy alone — see "FleetCore Live Backend" below for what else has to be running.
- `web/toys/fleetcore-control/` — FleetCore Control Center, copied from `toys/fleetcore-control/` (`app.js`, `index.html`, `style.css`; no README, same as every other toy). **Same intentional divergence as `web/toys/fleetcore-live/` and for the same reason**: `index.html`'s default `#serverUrl` is the public `wss://cameronlampley.com/monad/fleetcore-ws/ws` reverse-proxy path, not `ws://localhost:4771/ws`. Also depends on the "FleetCore Live Backend" section below being reachable, same as `web/toys/fleetcore-live/` — a plain file copy alone does nothing without a real server on the other end of that URL. Command authority (spawning contacts, setting routes) requires whatever `--command-token` the public `fleetcore-serve` instance is running with, entered into this toy's own token field — there is no `?commandToken=` URL passthrough here.

### Watchbook is intentionally not public

Watchbook (`toys/watchbook/`) reads the actual `logs/` tree via relative fetches (`../../logs/captains/...`). Deploying it as-is would publish the full captain/admiral watch log history — including internal ops/infra logs — to the public site. That has not been done. The public site's own Ship's Log page (`web/logs.html` / `web/assets/js/logs.js`) is the intentional, separate public-facing equivalent, and is what Bridge Station's Watchbook tab links out to instead of embedding Watchbook.

Note also that `web/bridge.html` is a separate, older, hand-built public "Bridge" page (different codebase, reads `web/bridge-state.json`) and is not related to `web/toys/bridge/`. Both are linked from `web/command-deck.html` under different labels ("Bridge" vs. "Bridge Station"). `web/index.html` is no longer that homepage — see below.

## Site Root Is the Front Door — Links to Every Toy

`web/index.html` was briefly a redirect straight into `toys/bridge/` (see git history if that behavior is ever wanted back). It's the homepage again: mission/doctrine/fleet roster/Ship's Log content, plus an "Interactive Artifact" section (`#artifacts`) linking every deployed public toy — Radio Console, FleetCore Live, Bridge Station, Fleet Motion, Periscope Station, Reaction-Diffusion Painter. `web/command-deck.html` is kept as an identical mirror (same content, distinct `<title>`) so the old URL still works — **update both together**, `web/index.html` is not the single source of truth here. Add a new `.artifact-launch-layout` card to both whenever a new toy gets deployed publicly.

## FleetCore Live Backend

`web/toys/fleetcore-live/` is a thin client with no simulation of its own — it needs a real `fleetcore-serve` process running and reachable, unlike every other public artifact in this repo, which are all fully self-contained static pages.

**Running the process.** `fleetcore-serve` binds `127.0.0.1` only by default (see the comment on `DEFAULT_BIND_HOST` in `fleetcore/src/bin/serve.rs`), and its write path (`POST /command`, and any command sent over `/ws`) requires a `--command-token` to be configured at all — with none set, the server is fully read-only regardless of what any client presents (see `docs/architecture/fleetcore-api.md`, "Command Authority"). Run it via the systemd unit at `scripts/fleetcore-serve.service` rather than an ad hoc background process, so it survives reboots and restarts on crash:

```sh
cargo build --release --manifest-path fleetcore/Cargo.toml --bin serve
sudo cp scripts/fleetcore-serve.service scripts/monad-lan-web.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now fleetcore-serve monad-lan-web
sudo systemctl status fleetcore-serve monad-lan-web
```

As of 2026-07-13, `scripts/fleetcore-serve.service`'s `ExecStart` already ships with `--bind-all --command-token bridge-3-0-lan` — command authority and LAN reachability are both on by default when this unit is installed, matching what's actually been live on this box, not the more conservative loopback-only/read-only configuration it originally shipped with. `scripts/monad-lan-web.service` is the LAN-only static web server's own unit, serving `web-lan/` on port `8090`.

Whoever holds `bridge-3-0-lan` can paste it into `toys/fleetcore-live/`'s, Bridge's, or FleetCore Control Center's "Command Token" field to unlock write access — treat it like any other shared secret, since it grants control of the live world for every visitor at once. **This one specifically is not a real secret**: it's committed in plaintext across this repo's own git history (watch logs, this file, past commit messages), and the public `/monad/fleetcore-ws/` reverse proxy was finished without rotating it first — see the Bridge Station 2.1/3.0 section below for the full history. If you ever want real command-authority isolation, rotate to a token that isn't committed anywhere and update this file's `ExecStart` (then `sudo systemctl daemon-reload && sudo systemctl restart fleetcore-serve`) — deliberately not done as part of installing durability, since that's a separate decision from "does the process survive a reboot."

**Exposing it publicly.** Add a `handle_path` block to `/etc/caddy/Caddyfile`, matching the existing `/portainer/*` pattern, so the public path proxies to the loopback-only server:

```caddyfile
handle_path /monad/fleetcore-ws/* {
    reverse_proxy http://localhost:4771
}
```

This must live inside the same `:80 { ... }` block as the existing `root */file_server`/`/portainer/*` config, not as a separate site block. `handle_path` strips the matched prefix before proxying, so a public request to `/monad/fleetcore-ws/ws` reaches `fleetcore-serve`'s own `/ws` route, and `/monad/fleetcore-ws/snapshot` reaches `/snapshot`. After editing:

```sh
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

**Unverified:** `cameronlampley.com` reaches Granite through a separate reverse proxy on rock64 (see the "Public Hatch" note in `web/command-deck.html`), which this deployment doc doesn't have visibility into. Whether rock64 passes WebSocket upgrade requests through to Granite's Caddy is not confirmed — if `wss://cameronlampley.com/monad/fleetcore-ws/ws` doesn't connect after the steps above, check rock64's proxy config for WebSocket support before assuming Caddy or `fleetcore-serve` is at fault. `http://localhost/monad/fleetcore-ws/snapshot` on Granite itself is the right first check to isolate Caddy/fleetcore-serve from rock64.

**Known limitation, accepted for now:** the live world is shared by every visitor, and the `--command-token` gate is all-or-nothing — there's no per-visitor isolation and no way to give one person pause/resume without also giving them everything else in the `Command` surface. Anyone holding the token affects every connected visitor at once. This was an explicit, informed choice (not an oversight) when deploying this artifact; add per-token scoping before treating this as anything more than a single-operator demo.

## Bridge Station 2.0 — LAN-Only Deployment

`toys/bridge-2/` (see `logs/captains/2026/2026-07-11_bridge-station-2-scope.md`) is deployed to the LAN only, deliberately not through the public Caddy/rock64 path. Reachable at `http://192.168.0.100:8090/toys/bridge-2/` from any machine on Granite's LAN.

**Why a separate port instead of `/var/www/monad`:** Caddy's `:80` root is reachable both on the LAN directly and publicly through rock64's proxy to `cameronlampley.com/monad/`. There is no path-based way to make something in `/var/www/monad` LAN-only — anything placed there is public too, whether or not it's linked from anywhere. Genuine LAN-only isolation requires a separate process on a port rock64 doesn't forward, so a dedicated `web-lan/` directory at the repo root (distinct from `web/`, which is what actually gets rsynced to `/var/www/monad`) is served by its own `python3 -m http.server 8090 --bind 0.0.0.0 --directory web-lan`, independent of the production Caddy instance. `web-lan/` holds its own copies (`toys/bridge-2/`, `toys/shared/`, `toys/fleetcore-control/`) — same "does not update itself, re-copy runtime files by hand" rule as `web/toys/`. Verified after deploying: `https://cameronlampley.com/monad/toys/bridge-2/` returns `404` (never copied to `/var/www/monad`), and port `8090` itself is unreachable from outside the LAN.

**`web-lan/toys/fleetcore-control/`** — LAN-only copy of `toys/fleetcore-control/`, reachable at `http://192.168.0.100:8090/toys/fleetcore-control/`. Same divergence pattern as the public copies: `index.html`'s `#serverUrl` defaults to `ws://192.168.0.100:4771/ws` (the LAN IP fleetcore-serve's `--bind-all` already listens on) rather than `localhost` or the public `wss://` reverse-proxy path. Verified live with write access using the existing `bridge-3-0-lan` command token — see the security note immediately below before assuming that token is LAN-scoped in practice.

**FleetCore's bind changed too, and this affects `fleetcore-serve` globally, not just this toy.** Bridge Station 2.0 needs a live WebSocket connection to `fleetcore-serve`, but that process was loopback-only (`127.0.0.1`) — reachable only from Granite itself, not from other machines on the LAN, since loopback means "this host," not "this network." Restarted it with `--bind-all` (binds `0.0.0.0`) to make LAN access possible at all. This was judged low-risk specifically because no `--command-token` is configured — the server is still fully read-only regardless of bind address (verified: `POST /command` from the LAN IP still returns `401`) — but it does mean `fleetcore-serve` is now reachable by anything on the LAN, not just Bridge Station 2.0, and not just from Granite itself. **This paragraph's risk analysis is now stale** — see the Bridge Station 2.1/3.0 section below: a `--command-token` was later added, and separately, the public `wss://` reverse-proxy path was finished without rotating that token first, so as of 2026-07-12 the same token grants write access from the LAN, from `cameronlampley.com`, and to anything else that has read this file's git history. Revisit this bind decision now, not "if a `--command-token` is ever added" — one already was.

**Durability:** see "Running the process" above — `scripts/fleetcore-serve.service` and the new `scripts/monad-lan-web.service` cover both this box's `fleetcore-serve` and the LAN web server. Until those are installed, both remain the ad hoc `nohup` processes they've been all along and do not survive a Granite reboot.

## Bridge Station 2.1 and 3.0 — LAN-Only React Deployments

`toys/bridge-station-2.1/` (mock data, `http://192.168.0.100:8080/`) and `toys/bridge-station-3.0/` (real FleetCore data, `http://192.168.0.100:8070/`) are the first build-toolchain projects in this repo (Vite + React + `lucide-react`). Each is `npm run build` then `npx serve -s dist -p <port>` as an ad hoc `nohup` process, same durability caveat as everything else on this page — no systemd unit, doesn't survive a reboot. `serve`'s `-l 0.0.0.0:8080` syntax (as might be assumed from other tools) errors; `serve` already defaults to binding `0.0.0.0`, so `-p <port>` alone is correct.

**The bind-decision revisit flagged in the Bridge Station 2.0 section above has happened.** `fleetcore-serve` now runs with `--command-token bridge-3-0-lan` (previously no token at all, fully read-only) so Bridge Station 3.0's Set Waypoint can actually write. This is a real, if LAN-scoped, change in risk profile: read-only-to-the-LAN and writable-to-the-LAN are different postures, and this crossed that line deliberately, not by accident. Verified before treating it as safe: `GET /snapshot` (what `toys/bridge-2/` and `toys/fleetcore-live/` both rely on) is completely unaffected; `POST /command` still 401s with no token or the wrong one; only the correct token succeeds.

The token is baked into Bridge Station 3.0's client bundle (`COMMAND_TOKEN` in `src/App.jsx`) — acceptable under the "LAN is the trust boundary, no login" scope both the 2.1 and 3.0 packets stated explicitly, not acceptable as a real secret, and shared with anything else that knows it. Notably, `toys/fleetcore-live/`'s own "Command Token" field (currently deployed publicly at `https://cameronlampley.com/monad/toys/fleetcore-live/`, but not yet reachable there since the Caddy reverse-proxy step above is still pending) would also accept `bridge-3-0-lan` and gain full write access, since it's the same `fleetcore-serve` process — if that public reverse-proxy step is ever finished while this token is still live, this token effectively becomes a public secret at that point, not a LAN one. Rotate or remove it before finishing that proxy step, not after.
