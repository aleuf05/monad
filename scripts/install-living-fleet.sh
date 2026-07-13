#!/usr/bin/env bash
# One-shot production rollout for the Living Fleet. This replaces the running
# FleetCore binary through its existing systemd unit and adds one shared captain
# runtime process (still opens no port; it uses FleetCore's loopback API), plus
# Effort B's memory/identity services: a loopback-only inspector API
# (living-fleet-memory.service, reached publicly only through Caddy's
# /captain-memory-api/* route -- see docs/deployment.md) and a scheduled
# reflection timer.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cargo build --release --manifest-path "$REPO_ROOT/fleetcore/Cargo.toml" --bins
python3 -m unittest discover -s "$REPO_ROOT/tools/living-fleet" -p 'test_*.py'
python3 "$REPO_ROOT/tools/living-fleet/memory/seed_import.py"

sudo cp "$REPO_ROOT/scripts/living-fleet.service" /etc/systemd/system/living-fleet.service
sudo cp "$REPO_ROOT/scripts/living-fleet-memory.service" /etc/systemd/system/living-fleet-memory.service
sudo cp "$REPO_ROOT/scripts/living-fleet-memory-reflect.service" /etc/systemd/system/living-fleet-memory-reflect.service
sudo cp "$REPO_ROOT/scripts/living-fleet-memory-reflect.timer" /etc/systemd/system/living-fleet-memory-reflect.timer
sudo systemctl daemon-reload
sudo systemctl restart fleetcore-serve
sudo systemctl enable --now living-fleet
sudo systemctl enable --now living-fleet-memory
sudo systemctl enable --now living-fleet-memory-reflect.timer

echo "Living Fleet installed. Agent Operations: https://cameronlampley.com/toys/agent-ops/"
echo "Remember to add the /captain-memory-api/* route to /etc/caddy/Caddyfile (see scripts/Caddyfile) if not already present, then: sudo caddy validate --config /etc/caddy/Caddyfile && sudo systemctl reload caddy"
sudo systemctl --no-pager --full status fleetcore-serve living-fleet living-fleet-memory living-fleet-memory-reflect.timer
