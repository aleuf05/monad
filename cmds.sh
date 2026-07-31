#!/usr/bin/env bash
# Superuser commissioning commands, assembled for the record. Captain has
# passwordless sudo since the 2026-07-29 authority bootstrap
# (docs/commissioning-handoff.md), so these are run directly rather than
# parked for the Lt. -- this file exists as an audit trail of what was
# actually executed, not a pending queue.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "== 2026-07-31: commissioning Chat Captain as a LAN-only console =="
echo "   (public cameronlampley.com Caddy block has zero chat-captain routes;"
echo "   see docs/deployment.md for the narrow exception to the retired"
echo "   web-lan/ pattern this authorizes)"

sudo caddy validate --config "$REPO_ROOT/scripts/Caddyfile"
sudo cp /etc/caddy/Caddyfile "/etc/caddy/Caddyfile.pre-chat-captain-lan-$(date +%Y%m%d%H%M%S)"
sudo install -m 644 "$REPO_ROOT/scripts/Caddyfile" /etc/caddy/Caddyfile
sudo install -m 644 "$REPO_ROOT/scripts/chat-captain-web.service" /etc/systemd/system/chat-captain-web.service
sudo systemctl daemon-reload
sudo systemctl restart chat-captain-web.service
sudo systemctl reload caddy

echo "== verifying =="
curl --fail --silent --show-error http://127.0.0.1:4778/health && echo
curl --fail --silent --show-error http://192.168.0.100:8080/chat-captain-api/health && echo
curl --fail --silent --show-error -o /dev/null -w "console page: %{http_code}\n" http://192.168.0.100:8080/
curl --fail --silent --show-error -o /dev/null -w "public site unaffected: %{http_code}\n" https://cameronlampley.com/
curl --silent -o /dev/null -w "public chat-captain-api route gone (expect 404): %{http_code}\n" https://cameronlampley.com/chat-captain-api/health

echo "== done =="

echo "== 2026-07-31 (continued): revert failed single-hostname LAN-detection theory =="
echo "   Tested and disproved: this router's NAT hairpin rewrites the source IP so"
echo "   hairpinned LAN traffic through the public hostname is indistinguishable"
echo "   from real internet traffic to Caddy's remote_ip matcher. Removing the"
echo "   @lan block from the public cameronlampley.com Caddy block -- it never"
echo "   worked and left dead config claiming a capability that doesn't exist."
echo "   The dedicated LAN-IP block (http://192.168.0.100:8080/) is the only"
echo "   working path to the console and is untouched by this revert."

sudo caddy validate --config "$REPO_ROOT/scripts/Caddyfile"
sudo cp /etc/caddy/Caddyfile "/etc/caddy/Caddyfile.pre-lan-detection-revert-$(date +%Y%m%d%H%M%S)"
sudo install -m 644 "$REPO_ROOT/scripts/Caddyfile" /etc/caddy/Caddyfile
sudo install -m 644 "$REPO_ROOT/scripts/chat-captain-web.service" /etc/systemd/system/chat-captain-web.service
sudo systemctl daemon-reload
sudo systemctl restart chat-captain-web.service
sudo systemctl reload caddy
sleep 3

echo "== verifying both required behaviors =="
PUBIP=$(dig +short cameronlampley.com A | tail -1)
echo "-- LAN dedicated URL -> must be the Root Console --"
curl -s -m 6 http://192.168.0.100:8080/ | grep -o "<title>[^<]*</title>"
curl --fail --silent --show-error http://192.168.0.100:8080/chat-captain-api/health && echo

echo "-- public hostname, hairpinned from this LAN host -- must be the public playground --"
curl -s -m 6 --resolve "cameronlampley.com:443:${PUBIP}" "https://cameronlampley.com/" | grep -o "<title>[^<]*</title>"
curl -s -m 6 -o /dev/null -w "public chat-captain-api route absent (expect 404): %{http_code}\n" --resolve "cameronlampley.com:443:${PUBIP}" "https://cameronlampley.com/chat-captain-api/health"

echo "-- public playground itself still fully intact --"
curl -s -m 6 -o /dev/null -w "public site: %{http_code}\n" https://cameronlampley.com/

echo "== done =="
