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

### Watchbook is intentionally not public

Watchbook (`toys/watchbook/`) reads the actual `logs/` tree via relative fetches (`../../logs/captains/...`). Deploying it as-is would publish the full captain/admiral watch log history — including internal ops/infra logs — to the public site. That has not been done. The public site's own Ship's Log page (`web/logs.html` / `web/assets/js/logs.js`) is the intentional, separate public-facing equivalent, and is what Bridge Station's Watchbook tab links out to instead of embedding Watchbook.

Note also that `web/bridge.html` is a separate, older, hand-built public "Bridge" page (different codebase, reads `web/bridge-state.json`) and is not related to `web/toys/bridge/`. Both are linked from `web/command-deck.html` under different labels ("Bridge" vs. "Bridge Station"). `web/index.html` is no longer that homepage — see below.

## Site Root Redirects to Bridge Station

`web/index.html` is a redirect page (instant meta-refresh plus a JS fallback and a visible manual link), not the homepage. It sends visitors straight into `toys/bridge/`. The former homepage content — mission, doctrine, fleet roster, Ship's Log entry form — is preserved intact at `web/command-deck.html` and reachable from the redirect page's fallback link. Update `web/command-deck.html` (not `web/index.html`) when changing homepage copy or adding new artifact launch cards.

## FleetCore Live Backend

`web/toys/fleetcore-live/` is a thin client with no simulation of its own — it needs a real `fleetcore-serve` process running and reachable, unlike every other public artifact in this repo, which are all fully self-contained static pages.

**Running the process.** `fleetcore-serve` binds `127.0.0.1` only by default (see the comment on `DEFAULT_BIND_HOST` in `fleetcore/src/bin/serve.rs`) — its command channel has no authentication, so anyone who can reach it can pause the world or spawn contacts for every connected client, and binding all interfaces would make that reachable the moment any firewall/NAT in front of the host allowed the port through. Run it via the systemd unit at `scripts/fleetcore-serve.service` rather than an ad hoc background process, so it survives reboots and restarts on crash:

```sh
cargo build --release --manifest-path fleetcore/Cargo.toml --bin serve
sudo cp scripts/fleetcore-serve.service /etc/systemd/system/fleetcore-serve.service
sudo systemctl daemon-reload
sudo systemctl enable --now fleetcore-serve
sudo systemctl status fleetcore-serve
```

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

**Known limitation, accepted for now:** the live world is shared by every visitor and has no authentication — pausing the clock, changing time scale, or any future write-capable control affects everyone connected, and there's no per-visitor isolation. This was an explicit, informed choice (not an oversight) when deploying this artifact; add auth before treating this as anything more than a demo.
