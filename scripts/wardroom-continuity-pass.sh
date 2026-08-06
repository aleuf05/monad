#!/usr/bin/env bash
set -euo pipefail

# One bounded continuity pass: validate the Clerk, then regenerate the
# human-readable packet from the authoritative append-only ledger.
repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

ledger="${1:?usage: wardroom-continuity-pass.sh <ledger.jsonl> [packet.md]}"
packet="${2:-${ledger%.jsonl}.packet.md}"

python3 -m unittest discover -s tools/wardroom -p 'test_*.py'
python3 tools/wardroom/wardroom.py --ledger "$ledger" export --output "$packet"
printf 'Continuity pass complete: %s → %s\n' "$ledger" "$packet"

