#!/usr/bin/env bash
set -euo pipefail

log() {
  printf '[deploy-web] %s\n' "$*"
}

fail() {
  printf '[deploy-web] ERROR: %s\n' "$*" >&2
  exit 1
}

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
WEB_DIR="$REPO_ROOT/web"
DEST_DIR="/var/www/monad/"
CADDYFILE="/etc/caddy/Caddyfile"

if [[ ! -d "$WEB_DIR" ]]; then
  fail "web/ directory not found at $WEB_DIR"
fi

if [[ ! -f "$WEB_DIR/index.html" ]]; then
  fail "web/index.html not found at $WEB_DIR/index.html"
fi

if ! command -v rsync >/dev/null 2>&1; then
  fail "rsync is required"
fi

if ! command -v curl >/dev/null 2>&1; then
  fail "curl is required"
fi

if [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
  SUDO=()
else
  SUDO=(sudo)
fi

cd "$REPO_ROOT"

log "Repo root: $REPO_ROOT"
log "Deploying web/ to $DEST_DIR"
"${SUDO[@]}" rsync -av --delete "$WEB_DIR/" "$DEST_DIR"

log "Validating Caddy config: $CADDYFILE"
"${SUDO[@]}" caddy validate --config "$CADDYFILE"

log "Reloading Caddy"
"${SUDO[@]}" systemctl reload caddy

log "Checking local HTTP response"
curl -fsSI http://localhost/ >/dev/null

log "Deployment complete"
