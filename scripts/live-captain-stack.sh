#!/usr/bin/env bash
set -euo pipefail

action="${1:-status}"
units=(public-root-auth.service root-console.service live-captain-bootstrap.service)

case "${action}" in
  start)
    sudo systemctl start public-root-auth.service
    sudo systemctl start live-captain-stack.target
    ;;
  restart)
    # Stop through the target so both coupled application services leave the
    # watch together. Auth remains available while the Captain reconstitutes.
    sudo systemctl restart public-root-auth.service
    sudo systemctl restart root-console.service live-captain-bootstrap.service
    sudo systemctl start live-captain-stack.target
    ;;
  status)
    ;;
  *)
    printf 'usage: %s {start|restart|status}\n' "$0" >&2
    exit 2
    ;;
esac

systemctl is-active --quiet "${units[@]}"
root_status="000"
captain_status="000"
for _attempt in $(seq 1 40); do
  root_status="$(curl --silent --output /dev/null --write-out '%{http_code}' http://127.0.0.1:4792/ || true)"
  captain_status="$(curl --silent --output /dev/null --write-out '%{http_code}' http://127.0.0.1:4778/api/status || true)"
  [[ "${root_status}" == "200" && ( "${captain_status}" == "200" || "${captain_status}" == "401" ) ]] && break
  sleep 0.25
done
[[ "${root_status}" == "200" ]] || { printf 'Root Console readiness failed: HTTP %s\n' "${root_status}" >&2; exit 1; }
case "${captain_status}" in
  200|401) ;;
  *) printf 'Live Captain status probe failed: HTTP %s\n' "${captain_status}" >&2; exit 1 ;;
esac
printf 'LIVE CO-CAPTAIN STACK: READY\n'
systemctl show --property=ActiveState,SubState --value "${units[@]}"
