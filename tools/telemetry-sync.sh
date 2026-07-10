#!/usr/bin/env sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT_DIR"

LOG_INDEX_STATUS="SKIP"
PYTHON_STATUS="SKIP"
FRONTEND_STATUS="SKIP"

fail() {
  printf '\nTelemetry sync failed: %s\n' "$1" >&2
  exit 1
}

run_step() {
  label=$1
  shift
  printf '%s...\n' "$label"
  "$@" || fail "$label"
}

run_step "Regenerating Watchbook log index" python tools/build-log-index.py
LOG_INDEX_STATUS="OK"

run_step "Validating Python syntax" python -m py_compile tools/build-log-index.py
PYTHON_STATUS="OK"

if command -v node >/dev/null 2>&1; then
  run_step "Validating Watchbook JavaScript syntax" node --check toys/watchbook/app.js
  FRONTEND_STATUS="OK"
else
  printf 'Validating Watchbook JavaScript syntax... SKIP (node not found)\n'
  FRONTEND_STATUS="SKIP (node not found)"
fi

GIT_STATUS=$(git status --short)

printf '\nTelemetry Summary\n'
printf '%s\n' '-----------------'
printf 'Log index .......... %s\n' "$LOG_INDEX_STATUS"
printf 'Frontend validation  %s\n' "$FRONTEND_STATUS"
printf 'Python validation... %s\n' "$PYTHON_STATUS"
printf '\nGit changes:\n'
if [ -n "$GIT_STATUS" ]; then
  printf '%s\n' "$GIT_STATUS"
else
  printf '  none\n'
fi
printf '\nRepository ready for review.\n'
