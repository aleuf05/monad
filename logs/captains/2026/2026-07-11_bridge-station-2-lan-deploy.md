# Bridge Station 2.0 LAN Deployment Watch Log

Date: 2026-07-11
Operator: Commander Claude, Engineering Watch
Directed by: Admiral C — deploy Bridge Station 2.0 internally on the LAN only.
Objective: make `toys/bridge-2/` reachable from Granite's LAN without exposing it publicly.

## Problem

`toys/bridge-2/` needs a live connection to `fleetcore-serve` to be anything more than an empty page — it has no local simulation, that's the entire point of the toy. Two separate obstacles stood between "commit the source" and "a LAN visitor can actually load and use this":

1. **Caddy's `:80` root is not LAN-scoped.** `/var/www/monad` is reachable both on the LAN directly and publicly through rock64's proxy to `cameronlampley.com/monad/`. There is no path-based way to put something in that directory and have it be LAN-only — anything placed there is public too, whether or not it's linked from any nav. Genuine LAN-only isolation needed a separate process on a port rock64 has no reason to forward.
2. **`fleetcore-serve` was loopback-only.** Bound to `127.0.0.1` since the FleetCore API 1.0 sprint (deliberately, to close the exposure gap caught before that server was ever public). Loopback means reachable only from Granite itself — a browser on any other LAN machine cannot open a WebSocket to `127.0.0.1:4771`, because that address means "this machine," not "this network," from the browser's own perspective. Not a config oversight this time — a real prerequisite that had to be deliberately changed for a LAN-facing toy to work at all.

## Integration

- Copied `toys/bridge-2/` into `web/toys/bridge-2/`, matching the standard deploy-bundle pattern (in case this is ever promoted to the public site later via the same pipeline).
- Started a dedicated static server for the whole `web/` bundle (needed for `../shared/fleet-state.js`) on its own port, bound to all interfaces: `python3 -m http.server 8090 --bind 0.0.0.0 --directory web`, independent of the production Caddy instance. Verified afterward: `https://cameronlampley.com/monad/toys/bridge-2/` returns `404` (never copied to `/var/www/monad`), and port `8090` itself is unreachable from outside the LAN.
- Restarted `fleetcore-serve` with `--bind-all` (was `--port 4771` only, loopback default). Judged low-risk specifically because no `--command-token` is configured on this process — read-only regardless of bind address. Verified: `POST /command` from the LAN IP still returns `401`, same as it did from loopback. This does mean `fleetcore-serve` is now reachable by anything on the LAN, not only Bridge Station 2.0 and not only from Granite itself — a real, if low-stakes, change in exposure, documented in `docs/deployment.md` rather than left implicit.

## Verification

Confirmed via `curl` from the LAN IP that both `GET /snapshot` (200) and `POST /command` (still 401, no token) behave correctly post-rebind. Playwright loaded `http://192.168.0.100:8090/toys/bridge-2/` — deliberately the LAN address, not `localhost`, to exercise the exact `window.location.hostname` a real LAN visitor's browser would resolve — and confirmed the link status reaches "Live" and 8 map markers render, with zero console errors. Confirmed the public site does not serve this toy (`404`) and the LAN-only port is not externally reachable.

## Follow-up

Neither the LAN web server nor `fleetcore-serve --bind-all` survive a Granite reboot — both are ad hoc processes, not systemd units. Making either durable needs `sudo`, same blocker as `scripts/fleetcore-serve.service`'s own installation from the FleetCore API 1.0 watch. If `fleetcore-serve` ever gains a `--command-token`, the `--bind-all` decision should be revisited — read-only-to-the-LAN and writable-to-the-LAN are very different risk profiles, and this watch's low-risk judgment was specifically contingent on staying read-only.
