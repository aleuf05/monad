#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_DIR="/home/cgl/.config/monad"
ENV_FILE="$CONFIG_DIR/world-intake.env"
DB="$REPO_ROOT/data/world-intake.sqlite3"

(cd "$REPO_ROOT" && python3 -m unittest tools/world-intake/test_world_intake.py)
RUSTC_BOOTSTRAP=1 cargo -Znext-lockfile-bump build --release --manifest-path "$REPO_ROOT/fleetcore/Cargo.toml" --bins

mkdir -p "$CONFIG_DIR"
if [[ ! -e "$ENV_FILE" ]]; then
  umask 077
  python3 -c 'import secrets; print("WORLD_INTAKE_REVIEW_TOKEN=" + secrets.token_hex(32))' > "$ENV_FILE"
fi

source_id="$(python3 "$REPO_ROOT/tools/world-intake/world_intake.py" --db "$DB" ingest "$REPO_ROOT/tools/world-intake/first_wave_reactor_crew.txt" --author Monad --mission-context first-wave-reactor-crew)"
python3 "$REPO_ROOT/tools/world-intake/world_intake.py" --db "$DB" extract "$source_id" >/dev/null

sudo cp "$REPO_ROOT/scripts/world-intake.service" /etc/systemd/system/world-intake.service
sudo cp "$REPO_ROOT/scripts/Caddyfile" /etc/caddy/Caddyfile
sudo systemctl daemon-reload
sudo systemctl restart fleetcore-serve
sudo systemctl enable --now world-intake
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
sudo systemctl --no-pager --full status fleetcore-serve world-intake caddy

echo "Living World Intake installed: https://cameronlampley.com/toys/world-intake/"
echo "Captain token: $ENV_FILE"
