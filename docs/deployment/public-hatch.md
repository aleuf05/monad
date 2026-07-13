# Monad Public Hatch

The public Monad hatch is the `/monad/` path on `cameronlampley.com`.

## Current Route

```text
Internet
  down
router (port-forward 80/443 -> granite)
  down
granite Caddy (owns public HTTPS directly, Let's Encrypt)
  down
/monad/ -> ~/dev/monad/web
```

As of 2026-07-13, rock64 is no longer in the path. The router forwards ports 80 and 443
directly to granite (`192.168.0.100`); granite's own Caddy terminates TLS (automatic
HTTPS via Let's Encrypt for `cameronlampley.com`) and serves `/monad/*` itself. Plain
HTTP is redirected to HTTPS automatically. rock64 is not otherwise involved.

## Boundary

- Granite owns public HTTPS directly.
- The router forwards only ports 80 and 443 to granite — deliberately not DMZ, so
  nothing else running on granite (Portainer's admin UI over its native port, Docker
  admin surfaces, Qdrant, etc.) is reachable from the internet except through the
  explicit `handle_path` routes in `/etc/caddy/Caddyfile`.
- `ufw` is active on granite as a backstop, allowing only SSH (22), HTTP (80), and
  HTTPS (443) inbound.
- `/monad/` is currently the only public proxy path family (`/monad/*` for static
  content, `/monad/fleetcore-ws/*` and `/monad/portainer/*` as reverse-proxied
  sub-paths — see `/etc/caddy/Caddyfile`).
- Qdrant is not exposed publicly.

## Doctrine

Git carries source. `~/dev/monad/web` is the live source, read straight off disk by
Caddy (see `docs/deployment.md`). Public exposure begins with the `/monad/` hatch, not
the whole engine room.
