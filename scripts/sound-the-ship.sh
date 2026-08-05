#!/usr/bin/env bash
# Sound the ship — structural checks the running system does not do for itself.
#
# Written 2026-08-05 after a carpenter's pass found that the installed
# fleetcore-serve unit was an older copy than the one in the repo. Nothing
# was broken and nothing would have noticed: the service was active, enabled,
# and behaving. The host was simply carrying a stale account of itself.
#
# These checks are cheap, read-only, and none of them are performed by any
# test suite, because they are about the gap between the repository and the
# machine rather than about the code.
#
#   bash scripts/sound-the-ship.sh
#
# Exit 0 if sound, 1 if anything wants attention.

set -uo pipefail
cd "$(dirname "$0")/.." || exit 2

problems=0
note() { printf '  %s\n' "$*"; }
fault() { printf '  ⚠ %s\n' "$*"; problems=$((problems + 1)); }

echo "=== 1. python files parse ==="
while read -r f; do
  case "$f" in archive/*) continue ;; esac   # archive is retired on purpose
  python3 -c "import ast,sys; ast.parse(open('$f').read())" 2>/dev/null \
    || fault "syntax: $f"
done < <(git ls-files '*.py')
note "$(git ls-files '*.py' | grep -cv '^archive/') files checked (archive/ skipped)"

echo "=== 2. service units point at files that exist ==="
for unit in scripts/*.service; do
  grep -h "^ExecStart=" "$unit" 2>/dev/null | sed 's/ExecStart=//' | tr ' ' '\n' \
    | grep '^/' | while read -r path; do
      # Only absolute tokens are paths; flags like --port live in the same line.
      [ -e "$path" ] || fault "$(basename "$unit") -> missing $path"
    done
done
note "$(ls scripts/*.service 2>/dev/null | wc -l) units checked"

echo "=== 3. installed units match the repo ==="
for unit in scripts/*.service; do
  name=$(basename "$unit" .service)
  installed="/etc/systemd/system/$name.service"
  [ -f "$installed" ] || continue
  if ! diff -q "$unit" "$installed" >/dev/null 2>&1; then
    fault "drift: $name — installed copy differs from repo"
  fi
done
note "drift check complete"

echo "=== 4. units the repo defines but the host never installed ==="
for unit in scripts/*.service; do
  name=$(basename "$unit" .service)
  [ -f "/etc/systemd/system/$name.service" ] || note "not installed: $name"
done

echo "=== 5. plumbing: services listening with no public route ==="
# Deliberately narrow. An earlier version probed each Caddy handle_path and
# faulted on 404 — and reported ten faults that were almost all wrong, because
# a bare prefix returns 404 when the service simply has no handler at "/".
# /gasket-upload-api/ is 404 while /gasket-upload-api/api/status is 200: the
# route is fine. Status codes cannot distinguish "no route" from "no root
# handler", so this checks only the thing that IS unambiguous — a listening
# port with nothing pointing at it.
for port in $(ss -ltn 2>/dev/null | grep -oE ':(4[0-9]{3})' | tr -d ':' | sort -u); do
  grep -q "reverse_proxy 127.0.0.1:$port" scripts/Caddyfile 2>/dev/null \
    || note "port $port listening, no public route"
done
note "reachability of individual endpoints is not inferable from a prefix probe"

echo
if [ "$problems" -eq 0 ]; then
  echo "SHIP IS SOUND — no faults found."
else
  echo "$problems fault(s) want attention."
fi
exit $(( problems > 0 ))
