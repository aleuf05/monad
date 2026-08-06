#!/usr/bin/env bash
set -euo pipefail

# Captain-managed publication seam. It never stages runtime state, incoming
# material, credentials, experiments, or source code.
repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

allowed=(docs/doctrine docs/wardroom docs/workflows admiralty/archive/canon)

for path in "${allowed[@]}"; do
  git add -- "$path"
done

outside="$(git diff --cached --name-only | awk '
  !($0 ~ /^docs\/doctrine\// || $0 ~ /^docs\/wardroom\// || $0 ~ /^docs\/workflows\// || $0 ~ /^admiralty\/archive\/canon\//) { print }
')"
if [[ -n "$outside" ]]; then
  echo "Captain publication refused: staged paths outside canonical documentation:" >&2
  printf '%s\n' "$outside" >&2
  exit 2
fi

if git diff --cached --quiet; then
  echo "Captain publication: no canonical documentation changes."
  exit 0
fi

if ! git diff --cached --check; then
  echo "Captain publication refused: whitespace error in canonical documentation." >&2
  exit 3
fi

message="${CAPTAIN_COMMIT_MESSAGE:-Captain: publish canonical process documentation}"
git commit -m "$message"
git push origin "$(git branch --show-current)"
echo "Captain publication complete: $(git rev-parse --short HEAD)"

