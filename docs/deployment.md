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

### Watchbook is intentionally not public

Watchbook (`toys/watchbook/`) reads the actual `logs/` tree via relative fetches (`../../logs/captains/...`). Deploying it as-is would publish the full captain/admiral watch log history — including internal ops/infra logs — to the public site. That has not been done. The public site's own Ship's Log page (`web/logs.html` / `web/assets/js/logs.js`) is the intentional, separate public-facing equivalent, and is what Bridge Station's Watchbook tab links out to instead of embedding Watchbook.

Note also that `web/bridge.html` is a separate, older, hand-built public "Bridge" page (different codebase, reads `web/bridge-state.json`) and is not related to `web/toys/bridge/`. Both are currently linked from `web/index.html` under different labels ("Bridge" vs. "Bridge Station").
