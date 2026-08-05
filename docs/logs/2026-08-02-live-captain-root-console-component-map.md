# Live Captain / Root Console — component map

**Live at:** `cameronlampley.com/root`

**Frontend** (edit directly, IS the live page):
- `console/index.html`
- `console/assets/js/root-console.js`

**Backend Captain daemon** — `root-console.service` (loopback `4792`):
- `tools/root-console/server.py` (entry)
- `tools/root-console/codex_daemon.py` (Captain logic)
- `tools/root-console/auth.py`

**Auth gate** — `public-root-auth.service` (`4779`):
- `tools/public-root-auth/server.py`

**Wiring:** `scripts/Caddyfile` — `/root` → auth gate → `console/`; `/root-console-api/*` → auth gate → `4792`

Verify anytime: `systemctl list-units | grep -i -E "root-console|captain"` + read Caddyfile directly.
