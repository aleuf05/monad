# 2026-07-08 Rock64 to Granite Reverse Proxy Watch

## Objective

Have public `cameronlampley.com` on rock64 reverse-proxy Monad traffic into granite.

## Result

Success. `https://cameronlampley.com/monad/` returns HTTP 200 and serves the Monad command-deck page from granite.

## Route

Internet -> rock64 nginx :443 -> /monad/ -> granite 192.168.0.100:80 -> Caddy -> /var/www/monad

## Safety

Only the static Monad page was exposed.

The following services were not exposed publicly:

- Portainer
- Qdrant
- Docker admin surfaces
- API keys or secrets

## Nginx Change

Rock64 nginx site config:

`/etc/nginx/sites-available/duckdns`

Added a `location /monad/` block proxying to:

`http://192.168.0.100/`

Backup was created before editing:

`/etc/nginx/sites-available/duckdns.bak.20260708-080607`

`sudo nginx -t` passed before reload.

## Doctrine

Public exposure begins with one harmless hatch, not the whole engine room.

## Artifact

Public Monad hatch:

`https://cameronlampley.com/monad/`
