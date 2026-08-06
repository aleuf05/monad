#!/usr/bin/env bash
set -euo pipefail

# End-of-meeting bridge: publish the packet, then emit the small human-facing
# message that belongs in the Chat Client.
repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

ledger="${1:?usage: wardroom-chat-handoff.sh <ledger.jsonl> [packet.md] [title]}"
packet="${2:-${ledger%.jsonl}.packet.md}"
title="${3:-Publish Wardroom chat handoff}"
branch="$(git branch --show-current)"

scripts/wardroom-handoff.sh "$ledger" "$packet" "$title"
pr_url="$(gh pr list --repo aleuf05/monad --head "$branch" --state open --json url --jq '.[0].url' 2>/dev/null || true)"

printf '\n## Wardroom handoff\n\n'
printf '%s\n' "Packet: \`$packet\`"
printf '%s\n' "Events: $(python3 -c 'import json,sys; print(sum(1 for line in open(sys.argv[1]) if line.strip()))' "$ledger")"
if [[ -n "$pr_url" ]]; then printf '%s\n' "GitHub: $pr_url"; fi
printf '%s\n' "The Captain has published the durable artifact; this message is the human-facing readout."
