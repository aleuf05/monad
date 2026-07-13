#!/usr/bin/env bash
# One-shot production rollout for the Living Fleet. This replaces the running
# FleetCore binary through its existing systemd unit and adds one shared captain
# runtime process. The runtime opens no port; it uses FleetCore's loopback API.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cargo build --release --manifest-path "$REPO_ROOT/fleetcore/Cargo.toml" --bins
python3 -m unittest discover -s "$REPO_ROOT/tools/living-fleet" -p 'test_*.py'

sudo cp "$REPO_ROOT/scripts/living-fleet.service" /etc/systemd/system/living-fleet.service
sudo systemctl daemon-reload
sudo systemctl restart fleetcore-serve
sudo systemctl enable --now living-fleet

echo "Living Fleet installed. Agent Operations: https://cameronlampley.com/toys/agent-ops/"
sudo systemctl --no-pager --full status fleetcore-serve living-fleet
