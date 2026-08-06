#!/usr/bin/env bash
set -euo pipefail

repo="/home/cgl/dev/monad"

python3 -m unittest discover -s "${repo}/tools/mike-rocketry" -p 'test_*.py'
sudo caddy validate --config "${repo}/scripts/Caddyfile"
sudo install -m 644 "${repo}/scripts/mike-rocketry-glb-intake.service" /etc/systemd/system/mike-rocketry-glb-intake.service
sudo install -m 644 "${repo}/scripts/Caddyfile" /etc/caddy/Caddyfile
sudo systemctl daemon-reload
sudo systemctl enable --now mike-rocketry-glb-intake.service
sudo systemctl reload caddy
curl --fail --silent --show-error http://127.0.0.1:4789/health
curl --fail --silent --show-error https://cameronlampley.com/mike-rocketry-intake-api/health
printf '\nMike rocketry GLB intake commissioned.\n'
