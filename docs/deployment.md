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
