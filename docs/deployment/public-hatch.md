# Monad Public Hatch

The public Monad hatch is the `/monad/` path on `cameronlampley.com`.

## Current Route

```text
Internet
  down
rock64 nginx /monad/
  down
granite Caddy
  down
/var/www/monad
```

## Boundary

- rock64 owns public HTTPS.
- granite serves Monad internally over LAN.
- `/monad/` is currently the only public proxy path.
- Admin tools remain LAN-only.
- Portainer is not exposed publicly.
- Qdrant is not exposed publicly.
- Docker admin surfaces are not exposed publicly.
- Future subdomain option: `monad.cameronlampley.com`.

## Doctrine

Git carries source. `/var/www/monad` is deployed output. Public exposure begins with one harmless hatch, not the whole engine room.