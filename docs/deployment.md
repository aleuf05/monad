# Monad Deployment

Granite serves the Monad public site through Caddy, directly from the repo. There is no deploy step.

## Paths

- Granite repo path: `~/dev/monad`
- Live web root: `~/dev/monad/web` (Caddy's `root *` directive in `/etc/caddy/Caddyfile` points here directly)

## Deployment

There isn't one. Editing any file under `web/` changes what `https://cameronlampley.com/monad/` serves immediately — Caddy reads straight off disk, no copy, no reload, no script.

As of 2026-07-12, Caddy's `root` was repointed from `/var/www/monad` (an rsynced copy, kept in sync by the now-retired `scripts/deploy-web.sh`) to `~/dev/monad/web` itself. `/var/www/monad` is no longer read by anything and can be left alone or removed. Permissions were verified compatible with this before switching: the `caddy` user (`caddy:caddy`) has traversal (`x`) on every ancestor directory down to `~/dev/monad/web` and read access on everything inside it, without needing any group changes.

## Doctrine

- Git carries source, and — as of this change — is also the live source. Editing `web/` on Granite is editing production directly.
- The Portainer reverse proxy path must not be disturbed.

## Public Artifacts

Interactive artifacts that must be reachable under `https://cameronlampley.com/monad/` live inside `web/toys/`. Each is a plain copy of the matching `toys/<name>/` source directory (runtime files only — READMEs, engineering reports, and other docs stay in the repo and are not copied). Re-copy the relevant source directory into `web/toys/<name>/` whenever that toy changes; `web/toys/` does not update itself, and since there's no deploy step, the copy is live the moment it's saved.

- `web/toys/fleet-motion/` — Fleet Motion Mk2, copied from `toys/fleet-motion/`. Depends on `web/toys/shared/fleet-state.js`.
- `web/toys/periscope/` — Periscope Station, copied from `toys/periscope/` (`app.js`, `index.html`, `style.css`, and only the two asset files `ASSET_PATHS` actually loads: `assets/backgrounds/sea-horizon-mk2.png`, `assets/sprites/scout-alpha.png`). Depends on `web/toys/shared/fleet-state.js`.
- `web/toys/bridge/` — Bridge Station's Live Console, copied from `toys/bridge/`, **with one intentional divergence from source**: the Watchbook tab's panel is not an iframe pointing at a Watchbook instance (Watchbook is not deployed publicly — see below) but a static message linking to `web/logs.html`. If `toys/bridge/index.html`'s Watchbook panel markup changes, re-apply that patch by hand rather than doing a raw copy.
- `web/toys/shared/fleet-state.js` — the `MonadFleetState` contract, copied from `toys/shared/fleet-state.js`. Fleet Motion, Periscope, and Bridge Station all depend on this being present and in sync with the source; a stale copy silently breaks cross-instrument selection sync (this happened once — `web/toys/fleet-motion/` sat un-refreshed since the `7003852` schema-v2 refactor until it was caught during the Bridge Station Mk III deploy).
- `web/toys/fleetcore-live/` — copied from `toys/fleetcore-live/`, **with one intentional divergence from source**: `index.html`'s default `#serverUrl` value is `wss://cameronlampley.com/monad/fleetcore-ws/ws` (the public reverse-proxy path below) instead of `ws://localhost:4771/ws`. Unlike every other public artifact here, this one doesn't work from a plain file copy alone — see "FleetCore Live Backend" below for what else has to be running.
- `web/toys/fleetcore-control/` — FleetCore Control Center, copied from `toys/fleetcore-control/` (`app.js`, `index.html`, `style.css`; no README, same as every other toy). **Same intentional divergence as `web/toys/fleetcore-live/` and for the same reason**: `index.html`'s default `#serverUrl` is the public `wss://cameronlampley.com/monad/fleetcore-ws/ws` reverse-proxy path, not `ws://localhost:4771/ws`. Also depends on the "FleetCore Live Backend" section below being reachable, same as `web/toys/fleetcore-live/` — a plain file copy alone does nothing without a real server on the other end of that URL. Command authority (spawning contacts, setting routes) requires whatever `--command-token` the public `fleetcore-serve` instance is running with, entered into this toy's own token field — there is no `?commandToken=` URL passthrough here.
- `web/toys/bridge-station-3.0/` — Bridge Station 3.0, a `vite build` output (not a plain file copy) from `toys/bridge-station-3.0/`. See "Bridge Station" below for the build config it needed to work from a subpath and to reach the public FleetCore WebSocket. Linked from `web/index.html` and `web/command-deck.html`'s "Bridge Instruments" section, alongside (not replacing) the existing `toys/bridge/` "Bridge Station" card.

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

This must live inside the same `cameronlampley.com { ... }` block as the existing `root */file_server`/`/monad/portainer/*` config, not as a separate site block. `handle_path` strips the matched prefix before proxying, so a public request to `/monad/fleetcore-ws/ws` reaches `fleetcore-serve`'s own `/ws` route, and `/monad/fleetcore-ws/snapshot` reaches `/snapshot`. After editing:

```sh
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

**Resolved as of 2026-07-13:** rock64 has been removed from the path entirely — see `docs/deployment/public-hatch.md`. The router forwards ports 80/443 directly to Granite, and Granite's own Caddy terminates TLS (automatic HTTPS via Let's Encrypt) and serves `/monad/*` itself. WebSocket upgrades through the full `wss://cameronlampley.com/monad/fleetcore-ws/ws` path are confirmed working end to end (verified with a real HTTP/1.1 upgrade handshake, `101` response). `http://localhost/monad/fleetcore-ws/snapshot` on Granite itself is still the right first check to isolate Caddy/`fleetcore-serve` from anything upstream, but there is no longer a separate rock64 hop to account for.

**Known limitation, accepted for now:** as of 2026-07-12 there is no command-token gate at all — `fleetcore-serve` grants full command authority to every connection on both `/command` and `/ws` unconditionally (`fleetcore/src/bin/serve.rs`), explicit user request. The live world is shared by every visitor with no per-visitor isolation: anyone who can reach the server (which, through the public reverse proxy, means anyone on the internet) can pause/resume, reset the fleet, despawn vessels, or set any vessel's route. This was an explicit, informed choice, not an oversight; add real auth before treating this as anything more than a single-operator demo.

## Bridge Station — `toys/bridge-station-3.0/`, Public

As of 2026-07-13, Bridge Station 3.0 (real FleetCore data, Vite + React) is the only
surviving generation of the Bridge Station lineage. `toys/bridge-2/` (2.0) and
`toys/bridge-station-2.1/` (mock-data 2.1) have been removed from the repo and their
ad hoc dev-server processes killed — superseded, not needed. `toys/bridge/` (the
original, unrelated "Live Console" — iframe-composited Fleet Motion/Periscope/Radio
Console) is a different toy entirely and is untouched.

Bridge Station 3.0 is deployed the same way as every other public toy: `npm run
build` in `toys/bridge-station-3.0/`, then the `dist/` output copied into
`web/toys/bridge-station-3.0/` — no separate port, no ad hoc process, served straight
through Caddy like the rest of `web/`. Two things this build needed that other,
non-bundled toys don't:

- `vite.config.js` sets `base: './'` so the built `index.html`/asset references are
  relative, not absolute — required because this is served from a subpath
  (`/monad/toys/bridge-station-3.0/` or `/toys/bridge-station-3.0/`, not domain root).
- `src/App.jsx`'s `serverUrl()` now defaults to
  `wss://cameronlampley.com/monad/fleetcore-ws/ws` instead of deriving
  `ws://<page-hostname>:4771/ws` — the latter would have tried to reach port 4771
  directly on `cameronlampley.com` (not open, and blocked as mixed content on an
  `https://` page regardless).

**Command token:** `fleetcore-serve` runs with `--command-token bridge-3-0-lan`
baked into Bridge Station 3.0's client bundle (`COMMAND_TOKEN` in `src/App.jsx`).
This token is not a real secret — see the "FleetCore Live Backend" section above;
`fleetcore-serve` currently grants command authority to every connection
unconditionally regardless of token, so this is presentational only unless real auth
is added later. `web-lan/toys/fleetcore-control/` still exists as a LAN-only copy of
a different toy (`toys/fleetcore-control/`), reachable at
`http://192.168.0.100:8090/toys/fleetcore-control/`, defaulting to
`ws://192.168.0.100:4771/ws` — unaffected by this change.
