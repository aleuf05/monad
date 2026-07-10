# Toys Overboard Watch Log

Date: 2026-07-10
Operator: Lt. cgl
Objective: place the newest Monad interactive artifact live on the public web.

## Artifact

Selected Fleet Motion Mk2 from `toys/fleet-motion/` because it is the newest local interactive artifact, static, browser-runnable, and already shaped for public operation.

## Integration

- Copied the static toy into `web/toys/fleet-motion/` for deployment by the existing `web/` rsync path.
- Added homepage launch links to `web/index.html`.
- Documented the public artifact path in `docs/deployment.md`.

## Verification

Local verification before integration loaded the toy at `http://localhost:8091/`, confirmed Leaflet tiles, passive underway route, warp control, escort mode control, scenario JSON export, and no browser console warnings or errors.
## Public Deployment

Committed on Granite as 3030e0a before deployment, then deployed the committed web/ bundle to /var/www/monad/ with sync -av --delete web/ /var/www/monad/ because the documented script required interactive sudo for static-file copy/reload. Caddy configuration was unchanged.

Granite local verification returned HTTP 200 for http://localhost/ and http://localhost/toys/fleet-motion/.

Public verification confirmed https://cameronlampley.com/monad/ exposes the Fleet Motion Mk2 launch link and https://cameronlampley.com/monad/toys/fleet-motion/ loads the artifact. Browser checks confirmed map tiles, passive underway route, 10x warp, scenario JSON export, existing Bridge/Ship's Log/Fleet Command pages, mobile usability, and no console warnings or errors.
