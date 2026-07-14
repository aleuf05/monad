# Monad Public Hatch

The public Monad hatch is the bare domain root on `cameronlampley.com`.

## Current Route

```text
Internet
  down
router (port-forward 80/443 -> granite)
  down
granite Caddy (owns public HTTPS directly, Let's Encrypt)
  down
/ -> ~/dev/monad/web
```

As of 2026-07-13, rock64 is no longer in the path. The router forwards ports 80 and 443
directly to granite (`192.168.0.100`); granite's own Caddy terminates TLS (automatic
HTTPS via Let's Encrypt for `cameronlampley.com`) and serves the site directly at the
bare root. Plain HTTP is redirected to HTTPS automatically. rock64 is not otherwise
involved.

As of the same date, the `/monad/` path prefix has been retired for the app itself --
see "History" below. `https://cameronlampley.com/` is the one canonical URL; nothing
public should ever need a `/monad/` segment in it again, with the sole exception of
Portainer's admin path (below), which is explicitly excluded from this cleanup by
standing doctrine ("the Portainer reverse proxy path must not be disturbed").

## Boundary

- Granite owns public HTTPS directly.
- The router forwards only ports 80 and 443 to granite — deliberately not DMZ, so
  nothing else running on granite (Portainer's admin UI over its native port, Docker
  admin surfaces, Qdrant, etc.) is reachable from the internet except through the
  explicit `handle_path` routes in `/etc/caddy/Caddyfile`.
- `ufw` is active on granite as a backstop, allowing only SSH (22), HTTP (80), and
  HTTPS (443) inbound.
- Public proxy paths, per `/etc/caddy/Caddyfile`: bare root (`handle {}`) serves
  `~/dev/monad/web` directly; `/fleetcore-ws/*` reverse-proxies to `fleetcore-serve`;
  `/monad/portainer/*` reverse-proxies to Portainer (kept at its old path deliberately,
  not touched by the `/monad/` retirement).
- Qdrant is not exposed publicly.

## History

Before 2026-07-13, everything public-facing lived under a `/monad/` prefix
(`/monad/*` for static content, `/monad/fleetcore-ws/*` and `/monad/portainer/*` as
reverse-proxied sub-paths), and the bare domain 302-redirected into `/monad/` --
nothing was served at the true root. That prefix was retired because it violated the
"no strange URLs" doctrine (see `docs/deployment.md`): a visitor had to already know
to add `/monad/` to find anything. The static-content and `fleetcore-ws` paths were
moved to the bare root; `/monad/portainer/*` was deliberately left in place, since
Portainer is operator infrastructure, not part of the app, and its reverse-proxy path
is under separate standing protection.

## Doctrine

Git carries source. `~/dev/monad/web` is the live source, read straight off disk by
Caddy (see `docs/deployment.md`). Public exposure begins at the bare domain root, not
the whole engine room.
