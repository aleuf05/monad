# FleetCore Control Center Landing/Bridge Linking Watch Log

Date: 2026-07-12
Operator: Lt. cgl
Objective: surface FleetCore Control Center (shipped local-only in the prior watch) from Bridge Station's Unified Access rail and the public landing page's Interactive Artifact grid, and deploy the toy itself so those links resolve.

## Changes

- `toys/bridge/index.html`: added a "FleetCore Control Center" entry to `.station-links`, alongside Fleet Motion/Periscope/Watchbook.
- `web/index.html` and `web/command-deck.html` (kept as identical mirrors per `docs/deployment.md`): added a new "Newest Toy" artifact card for FleetCore Control Center at the top of the Interactive Artifact grid, demoting Radio Console's card to "Toy".
- `web/toys/fleetcore-control/` (new): deployed copy of the toy (`app.js`, `index.html`, `style.css`; no README, matching every other `web/toys/` entry).
- `web/toys/fleetcore-control/index.html`: applied the same intentional divergence `web/toys/fleetcore-live/` already has — `#serverUrl` defaults to the public `wss://cameronlampley.com/monad/fleetcore-ws/ws` reverse-proxy path instead of `ws://localhost:4771/ws`. Caught by checking `docs/deployment.md`'s existing fleetcore-live entry before assuming a raw copy was sufficient; a raw copy would have shipped a control panel whose default server URL doesn't work for anyone but a local developer.
- `web/toys/bridge/index.html`: hand-added the same new station-link line (not a raw copy — that would have silently dropped the Watchbook panel's documented redirect divergence again, the same mistake caught and fixed in the prior sync watch).
- `docs/deployment.md`: added a `web/toys/fleetcore-control/` bullet documenting both the deployment and the server-URL divergence, matching the existing `web/toys/fleetcore-live/` entry's format.

## Verification

Playwright against a local server over `web/` (the pre-deploy tree, not yet pushed live):

- `web/index.html` and `web/command-deck.html`: confirmed the new card exists on both with the correct `href="toys/fleetcore-control/"`.
- Clicked the card's launch button from `index.html`: landed on the toy, confirmed `#serverUrl` defaults to the public `wss://` path (not localhost).
- `web/toys/bridge/`: confirmed `.station-links` includes the new entry, and confirmed the Watchbook tab still shows its redirect message (not silently reverted to a broken iframe again).
- Pointed the deployed `web/toys/fleetcore-control/` copy at the real local dev `fleetcore-serve` (overriding its public default, the way a developer testing locally would) with the dev command token: connected live, authority granted, saw all 15 vessels currently in that world (including the test spawns from the prior watch).
- Zero console errors, zero failed requests, across every step.

## Not done

- Not pushed to production. Everything above is staged in the local `web/` tree and verified against it, same gate as the prior deploy watch — `scripts/deploy-web.sh` needs an interactive sudo password this session cannot supply.
- Did not fix a pre-existing, unrelated issue noticed in passing: `web/toys/bridge/index.html`'s `.station-links` "Watchbook" entry still points at `../watchbook/`, which 404s publicly (Watchbook is intentionally not deployed — see `docs/deployment.md`'s "Watchbook is intentionally not public" section). The historical Watchbook divergence patch (commit `da98d7f`) only ever touched the tab panel's markup, not this sidebar link. Flagged, not fixed, since it's outside what was asked this watch.

## Updated

- `toys/bridge/index.html`
- `web/index.html`
- `web/command-deck.html`
- `web/toys/bridge/index.html`
- `web/toys/fleetcore-control/index.html` (new)
- `web/toys/fleetcore-control/app.js` (new)
- `web/toys/fleetcore-control/style.css` (new)
- `docs/deployment.md`
