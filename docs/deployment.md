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

**Running the process.** `fleetcore-serve` binds `127.0.0.1` only by default (see the comment on `DEFAULT_BIND_HOST` in `fleetcore/src/bin/serve.rs`), and its write path (`POST /command`, and any command sent over `/ws`) requires a `--command-token` to be configured at all — with none set, the server is fully read-only regardless of what any client presents (see `docs/architecture/fleetcore-api.md`, "Command Authority"). Run it via the systemd unit at `scripts/fleetcore-serve.service` rather than an ad hoc background process, so it survives reboots and restarts on crash:

```sh
cargo build --release --manifest-path fleetcore/Cargo.toml --bin serve
sudo cp scripts/fleetcore-serve.service /etc/systemd/system/fleetcore-serve.service
sudo systemctl daemon-reload
sudo systemctl enable --now fleetcore-serve
sudo systemctl status fleetcore-serve
```

As shipped, `scripts/fleetcore-serve.service` does not set `--command-token`, so the public deployment is read-only by default — visitors can watch the world tick but not touch it. To grant command authority (to yourself, or to anyone you give the token to), edit the unit's `ExecStart` line to add `--command-token <a-real-secret-you-choose>`, then:

```sh
sudo systemctl daemon-reload
sudo systemctl restart fleetcore-serve
```

Whoever holds that token can then paste it into `toys/fleetcore-live/`'s "Command Token" field to unlock the Pause/Resume/time-scale controls. Treat it like any other shared secret — it grants control of the live world for every visitor at once, not just the person holding it.

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

**Why a separate port instead of `/var/www/monad`:** Caddy's `:80` root is reachable both on the LAN directly and publicly through rock64's proxy to `cameronlampley.com/monad/`. There is no path-based way to make something in `/var/www/monad` LAN-only — anything placed there is public too, whether or not it's linked from anywhere. Genuine LAN-only isolation requires a separate process on a port rock64 doesn't forward, so `web/toys/bridge-2/` (and the rest of `web/`, needed for `../shared/fleet-state.js`) is served by its own `python3 -m http.server 8090 --bind 0.0.0.0 --directory web`, independent of the production Caddy instance. Verified after deploying: `https://cameronlampley.com/monad/toys/bridge-2/` returns `404` (never copied to `/var/www/monad`), and port `8090` itself is unreachable from outside the LAN.

**FleetCore's bind changed too, and this affects `fleetcore-serve` globally, not just this toy.** Bridge Station 2.0 needs a live WebSocket connection to `fleetcore-serve`, but that process was loopback-only (`127.0.0.1`) — reachable only from Granite itself, not from other machines on the LAN, since loopback means "this host," not "this network." Restarted it with `--bind-all` (binds `0.0.0.0`) to make LAN access possible at all. This was judged low-risk specifically because no `--command-token` is configured — the server is still fully read-only regardless of bind address (verified: `POST /command` from the LAN IP still returns `401`) — but it does mean `fleetcore-serve` is now reachable by anything on the LAN, not just Bridge Station 2.0, and not just from Granite itself. It is still not reachable from the public internet (rock64 has no reason to forward port `4771`, and this hasn't been verified otherwise). Revisit this bind decision if a `--command-token` is ever added — read-only-to-the-LAN and writable-to-the-LAN are very different risk profiles.

**Durability:** both the LAN web server and `fleetcore-serve --bind-all` are ad hoc `nohup` processes, same caveat as the rest of this doc's "FleetCore Live Backend" section — neither survives a Granite reboot. `scripts/fleetcore-serve.service` (still not installed — needs `sudo`, see above) would need its `ExecStart` updated to include `--bind-all` if this LAN deployment is meant to be durable; there is currently no systemd unit for the LAN web server either.
