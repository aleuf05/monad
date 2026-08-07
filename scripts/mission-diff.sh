#!/usr/bin/env bash
# What has the mission actually changed?
#
# Written 2026-08-07 after `git diff pre-mission-2026-08-07` was handed to the
# Captain as his evidence baseline and turned out to lie in both directions:
#
#   - the baseline tag was built with `git add -A`, so it CONTAINS untracked
#     files. `git diff <tag>` ignores untracked files, so every one of them
#     read as a deletion — 4,664 spurious deleted lines across 68 files,
#     including tools/root-console/*.py that are sitting on disk right now.
#   - genuinely new work (docs/monad-core/, seven files) did not appear in
#     the diff at all, because it is untracked too.
#
# A discovery mission that must cite evidence cannot use an instrument that
# invents deletions and hides additions. This snapshots the current tree the
# same way the baseline was built — tracked and untracked, honouring
# .gitignore — and diffs like against like.
#
#   bash scripts/mission-diff.sh              # stat summary
#   bash scripts/mission-diff.sh --full       # full patch
#   bash scripts/mission-diff.sh --name-only  # paths only
#
# Compares against $MISSION_BASELINE (default: pre-mission-2026-08-07).
# Read-only: builds its snapshot through a temporary index and never touches
# the working tree, the real index, or HEAD.

set -uo pipefail
cd "$(dirname "$0")/.." || exit 2

baseline="${MISSION_BASELINE:-pre-mission-2026-08-07}"

if ! git rev-parse --verify --quiet "$baseline^{commit}" >/dev/null; then
  echo "mission-diff: baseline '$baseline' does not exist" >&2
  echo "set MISSION_BASELINE, or create the tag first" >&2
  exit 2
fi

tmp_index=$(mktemp -t mission-diff-index.XXXXXX)
trap 'rm -f "$tmp_index"' EXIT

# Snapshot the working tree exactly as the baseline tag was built.
if ! GIT_INDEX_FILE="$tmp_index" git read-tree HEAD 2>/dev/null; then
  echo "mission-diff: could not read HEAD into a temporary index" >&2
  exit 2
fi
GIT_INDEX_FILE="$tmp_index" git add -A 2>/dev/null
tree=$(GIT_INDEX_FILE="$tmp_index" git write-tree) || exit 2
now=$(git commit-tree "$tree" -p HEAD -m "mission-diff ephemeral snapshot") || exit 2

case "${1:-}" in
  --full)      git diff "$baseline" "$now" ;;
  --name-only) git diff --name-status "$baseline" "$now" ;;
  *)
    echo "Mission changes since $baseline ($(git rev-parse --short "$baseline")):"
    echo
    git diff --stat "$baseline" "$now"
    echo
    echo "Full patch: bash scripts/mission-diff.sh --full"
    ;;
esac
