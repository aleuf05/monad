#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python3 -m unittest \
  "$REPO_ROOT/tools/living-captain/test_sight.py" \
  "$REPO_ROOT/tools/living-captain/test_captain.py" \
  "$REPO_ROOT/tools/living-captain/test_captain_v02.py"

sudo cp "$REPO_ROOT/scripts/living-captain-status.service" /etc/systemd/system/living-captain-status.service
sudo cp "$REPO_ROOT/scripts/Caddyfile" /etc/caddy/Caddyfile
sudo systemctl daemon-reload
sudo systemctl enable --now living-captain-status
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
sudo systemctl --no-pager --full status living-captain-status caddy

echo "Living Captain status API installed: https://cameronlampley.com/toys/living-captain/"
