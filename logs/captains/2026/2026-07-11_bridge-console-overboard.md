# Bridge Console Overboard Watch Log

Date: 2026-07-11
Operator: Lt. cgl
Objective: publish Bridge Station's new composited Live Console (Fleet Motion + Periscope) to the public web, following the pattern set in the 2026-07-10 "Toys Overboard" watch log.

## Discovery

`web/toys/` only carried Fleet Motion, and it had drifted: it predated the `MonadFleetState` schema-v2 refactor (`7003852`) and the Arabian Sea reseed, still running schema v1, the old Strait of Hormuz scenario, and no shared-state contract at all. Deploying Bridge Station's Live Console against that stale copy would have shipped a broken cross-instrument sync to the public site, so refreshing it was a prerequisite, not optional polish.

Bridge's Watchbook tab was also a problem for public deployment: Watchbook fetches the repository's actual `logs/` tree (`../../logs/captains/...`), so deploying it as-is would have published the full captain/admiral watch log history — including internal ops/infra logs like the Rock64/Granite reverse-proxy notes — to the public internet. Confirmed with the operator before proceeding: skip publishing Watchbook and `logs/`, and instead point Bridge's public Watchbook tab at the existing `web/logs.html` Ship's Log page.

## Integration

- Refreshed `web/toys/fleet-motion/` from current `toys/fleet-motion/` source (schema v2, `MonadFleetState`, Arabian Sea seed).
- Added `web/toys/shared/fleet-state.js` (the `MonadFleetState` contract) and `web/toys/periscope/` (runtime files plus only the two asset files Periscope's `ASSET_PATHS` actually loads).
- Added `web/toys/bridge/`, copied from `toys/bridge/` with one deliberate divergence: the Watchbook tab panel is a static message linking to `web/logs.html` instead of an iframe pointing at an undeployed Watchbook instance.
- Added homepage entries on `web/index.html`: a "Bridge Station" hero nav link and a second Interactive Artifact card, and corrected the Fleet Motion card's stale "Strait of Hormuz" description to match the current Arabian Sea scenario.
- Documented all of the above, including the Watchbook non-deployment decision, in `docs/deployment.md`.
- Caught and fixed a layout bug during verification: the Watchbook redirect panel initially used `align-content: center`, which centered the message inside Bridge's `.station-deck` row — a box that runs far taller than the visible viewport (Fleet Motion/Periscope fill it edge-to-edge, so nobody had noticed). Centered content in that oversized box landed off-screen below the fold. Fixed by anchoring the message near the top (`align-content: start`) instead of touching the underlying row-height behavior, which is pre-existing and out of scope here.

## Verification

Served `web/` locally on port 8791 and drove it with headless Chromium via Playwright (installed ad hoc for this and the prior verification pass, not added to the repo): confirmed Fleet Motion and Periscope both visible with no click, confirmed the selection-sync pulse and Periscope re-aim work against the refreshed Fleet Motion copy, confirmed the Watchbook tab shows the link-out message correctly positioned (not off-screen) and links to `../../logs.html`, confirmed the new homepage links point at `toys/bridge/`. Captured all console and network-failure events: none.

## Public Deployment

Committed on Granite as `9dd34e0`, pushed to `origin/main`. `/var/www/monad` is owned by `cgl` on this host, so the deploy used a direct `rsync -av --delete web/ /var/www/monad/` rather than `scripts/deploy-web.sh`'s sudo-wrapped version (interactive sudo isn't available in this session). Skipped the script's `caddy validate` / `systemctl reload caddy` steps: the Caddyfile is an unchanged bare `file_server` over `/var/www/monad`, so no config reload is needed for updated static content, and reload requires sudo. Caddy config itself was not touched.

Verified `http://localhost/`, `http://localhost/toys/bridge/`, `http://localhost/toys/periscope/`, and `http://localhost/toys/fleet-motion/` all return HTTP 200, and that `toys/fleet-motion/index.html` now serves `app.js?v=8` (current source) rather than the stale `v=5`. Verified `https://cameronlampley.com/monad/`, `https://cameronlampley.com/monad/toys/bridge/`, and `https://cameronlampley.com/monad/toys/periscope/` all return HTTP 200. Loaded `https://cameronlampley.com/monad/toys/bridge/` in headless Chromium against the live public site: Fleet Motion and Periscope both render side by side, Periscope shows Fleet Motion's shared Arabian Sea contacts, and no console or network errors were emitted.
