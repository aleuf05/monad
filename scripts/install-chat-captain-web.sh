#!/usr/bin/env bash
set -euo pipefail

repo="/home/cgl/dev/monad"
auth_file="/home/cgl/.config/monad/chat-captain-web.env"

if [[ ! -s "${auth_file}" ]]; then
  python3 "${repo}/tools/chat-captain/configure_web_auth.py"
fi

python3 -m unittest discover -s "${repo}/tools/chat-captain" -p 'test_*.py'
install -d -m 700 "${repo}/data/chat-captain"
sudo caddy validate --config "${repo}/scripts/Caddyfile"

if [[ -f /etc/caddy/Caddyfile ]]; then
  sudo cp /etc/caddy/Caddyfile /etc/caddy/Caddyfile.pre-chat-captain
fi
sudo install -m 644 "${repo}/scripts/Caddyfile" /etc/caddy/Caddyfile
sudo install -m 644 "${repo}/scripts/chat-captain-web.service" /etc/systemd/system/chat-captain-web.service
sudo systemctl daemon-reload
sudo systemctl enable --now chat-captain-web.service
sudo systemctl reload caddy

sudo systemctl --no-pager --full status chat-captain-web.service
curl --fail --silent --show-error http://127.0.0.1:4778/health
curl --fail --silent --show-error http://192.168.0.100:8080/chat-captain-api/health
printf '\nChat Captain commissioned. LAN-only console: http://192.168.0.100:8080/\n'
