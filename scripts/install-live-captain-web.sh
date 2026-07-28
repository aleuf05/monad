#!/usr/bin/env bash
set -euo pipefail

repo="/home/cgl/dev/monad"
auth_file="/home/cgl/.config/monad/live-captain-web.env"

if pgrep -f '[l]ive_captain_cli.py' >/dev/null; then
  printf 'STOP: a terminal Live Captain is running. Enter /quit there, then run this handoff again.\n' >&2
  exit 1
fi

if [[ ! -s "${auth_file}" ]]; then
  python3 "${repo}/tools/living-captain/configure_web_auth.py"
fi

python3 -m unittest discover -s "${repo}/tools/living-captain" -p 'test_*.py'
sudo caddy validate --config "${repo}/scripts/Caddyfile"

if [[ -f /etc/caddy/Caddyfile ]]; then
  sudo cp /etc/caddy/Caddyfile /etc/caddy/Caddyfile.pre-live-captain-v1
fi
sudo install -m 644 "${repo}/scripts/Caddyfile" /etc/caddy/Caddyfile
sudo install -m 644 "${repo}/scripts/live-captain-web.service" /etc/systemd/system/live-captain-web.service
sudo systemctl daemon-reload
sudo systemctl enable --now live-captain-web.service
sudo systemctl reload caddy

sudo systemctl --no-pager --full status live-captain-web.service
curl --fail --silent --show-error http://127.0.0.1:4776/health
printf '\nPrivate Conference backend commissioned. Return to Commander Codex for live UI deployment.\n'
