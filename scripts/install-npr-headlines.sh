#!/usr/bin/env bash
# Installs the NPR headlines fetch timer: a oneshot service run every 15
# minutes that writes web/data/npr-headlines.json from NPR's public RSS
# feed (see tools/npr-headlines/fetch.py for the terms-of-use notes).
# Privileged (sudo) -- see docs/commissioning-handoff.md. Until this is
# run, a user crontab entry (see docs/deployment.md) covers the same job
# non-privileged; this replaces that bridge with the proper systemd timer
# this repo otherwise uses everywhere else.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python3 "$REPO_ROOT/tools/npr-headlines/fetch.py"

sudo cp "$REPO_ROOT/scripts/npr-headlines-fetch.service" /etc/systemd/system/npr-headlines-fetch.service
sudo cp "$REPO_ROOT/scripts/npr-headlines-fetch.timer" /etc/systemd/system/npr-headlines-fetch.timer
sudo systemctl daemon-reload
sudo systemctl enable --now npr-headlines-fetch.timer

crontab -l 2>/dev/null | grep -v "npr-headlines/fetch.py" | crontab - || true

echo "NPR headlines timer installed."
sudo systemctl --no-pager --full status npr-headlines-fetch.timer
