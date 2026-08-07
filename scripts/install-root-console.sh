#!/usr/bin/env bash
set -euo pipefail

repo="/home/cgl/dev/monad"

install -d -m 700 "${repo}/data/root-console"
sudo install -m 644 "${repo}/scripts/root-console.service" /etc/systemd/system/root-console.service
sudo install -m 644 "${repo}/scripts/live-captain-bootstrap.service" /etc/systemd/system/live-captain-bootstrap.service
sudo install -m 644 "${repo}/scripts/live-captain-stack.target" /etc/systemd/system/live-captain-stack.target
sudo install -m 755 "${repo}/scripts/live-captain-stack.sh" /usr/local/bin/live-captain-stack
sudo systemctl daemon-reload
sudo systemctl enable --now live-captain-stack.target

sudo systemctl --no-pager --full status root-console.service
# `/api/status` is intentionally authenticated. Using it here without a
# session cookie made a healthy install exit non-zero with HTTP 401. Verify
# the unauthenticated console shell, then ask systemd for process health.
curl --fail --silent --show-error --output /dev/null http://127.0.0.1:4792/
sudo systemctl is-active --quiet root-console.service
sudo systemctl is-active --quiet live-captain-bootstrap.service
live-captain-stack status
printf '\nRoot Console commissioned (loopback only): http://127.0.0.1:4792/\n'
