#!/usr/bin/env bash
set -euo pipefail

# Captain's end-of-meeting handoff: continuity first, then scoped publication.
repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

ledger="${1:?usage: wardroom-handoff.sh <ledger.jsonl> [packet.md] [title]}"
packet="${2:-${ledger%.jsonl}.packet.md}"
title="${3:-Publish Wardroom meeting packet}"
branch="$(git branch --show-current)"

scripts/wardroom-continuity-pass.sh "$ledger" "$packet"
CAPTAIN_PUBLISH_PATHS="$packet scripts/wardroom-handoff.sh scripts/captain-publish-canon.sh scripts/wardroom-continuity-pass.sh" \
  CAPTAIN_COMMIT_MESSAGE="Captain: ${title}" scripts/captain-publish-canon.sh

if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
  existing_pr="$(gh pr list --repo aleuf05/monad --head "$branch" --state open --json url --jq '.[0].url' 2>/dev/null || true)"
  if [[ -z "$existing_pr" ]]; then
    gh pr create --repo aleuf05/monad --draft --base main --head "$branch" \
      --title "$title" \
      --body "Automated Wardroom handoff. Continuity packet: ${packet}. Tests and export run by wardroom-continuity-pass.sh."
  else
    printf '%s\n' "$existing_pr"
  fi
else
  printf 'Published branch %s; GitHub draft creation unavailable.\n' "$branch"
fi
