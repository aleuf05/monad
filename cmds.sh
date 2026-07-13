#!/usr/bin/env bash
# Pending ops for the Lt. to run -- each needs sudo, which Claude can't do
# in this environment. Safe to run as `sudo ./cmds.sh` or `./cmds.sh` (each
# command prompts for sudo itself either way).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "== retiring /monad/ -- swapping Caddyfile, validating, reloading =="
sudo cp "$REPO_ROOT/scripts/Caddyfile" /etc/caddy/Caddyfile
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy

echo "== stopping the retired LAN-only web server =="
sudo systemctl stop monad-lan-web
sudo systemctl disable monad-lan-web

echo "== done =="
