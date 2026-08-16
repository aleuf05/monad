#!/usr/bin/env bash
# scripts/git-auto-sync.sh — Shell entry point for Monad Autonomous Git Auto-Sync
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

export PYTHONPATH="${REPO_ROOT}:${PYTHONPATH:-}"
python3 "${REPO_ROOT}/tools/git-sync/auto_sync.py" "$@"
