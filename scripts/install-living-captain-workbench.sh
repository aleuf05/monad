#!/usr/bin/env bash
set -euo pipefail

repo="/home/cgl/dev/monad"

python3 -m unittest discover -s "${repo}/tools/living-captain-workbench" -p 'test_*.py'
install -d -m 700 "${repo}/data/living-captain-workbench"
sudo caddy validate --config "${repo}/scripts/Caddyfile"
sudo install -m 644 "${repo}/scripts/living-captain-workbench.service" /etc/systemd/system/living-captain-workbench.service
sudo install -m 644 "${repo}/scripts/Caddyfile" /etc/caddy/Caddyfile
sudo systemctl daemon-reload
sudo systemctl enable --now living-captain-workbench.service
sudo systemctl reload caddy
curl --fail --silent --show-error http://127.0.0.1:4791/health
curl --fail --silent --show-error https://cameronlampley.com/captain-workbench-api/health
printf '\nLiving Captain Workbench commissioned.\n'
