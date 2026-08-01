# Fresh-thread continuation packet

Assume Captain role. Continue the Monad project in `/home/cgl/dev/monad`.
Read `AGENTS.md`, `CLAUDE.md`, and the cited sources before changing state.

Mission: Monad organizes Cameron's cognitive landscape so valuable engineering work is preserved, connected, refined, and recoverable instead of becoming fragmented or buried (docs/mission.md). Beastscape and sibling Live Captain instruments remain active parallel product threads within that mission.

Active goal: 2026-08-01: legacy Chat Captain (tools/chat-captain/, port 4778) is parked -- stopped, disabled, data preserved, routes return 410 legacy_chat_captain_parked. It is not the governing design for the integrated Captain; its legacy modes, harvest workflow, context-compiler, and JSON ceremony are not requirements of the new Captain. The active objective is one coherent, maximum-capability Live Captain: root-console.service is already commissioned and active; next action is the clean Captain bootstrap on top of it. Separately, Caddy was consolidated to one site block: console reachable only at cameronlampley.com/root, same existing password check; the bare-IP LAN-only 192.168.0.100:8080 block is gone.

Established truth:
- PARKED 2026-08-01: chat-captain-web.service stopped and disabled (confirmed inactive/disabled, no listener on port 4778, removed from multi-user.target.wants). data/chat-captain/ left byte-for-byte untouched (captain.sqlite3 sha256 e3ba0653...970aa, usage.json sha256 6a7858e8...476a6, full sizes/mtimes recorded before the change). scripts/Caddyfile's two /chat-captain-api/* handlers now `respond` 410 with body {"error":"legacy_chat_captain_parked"} instead of reverse_proxy-ing to 127.0.0.1:4778, validated and deployed live via caddy validate + systemctl reload caddy, prior Caddyfile preserved at /etc/caddy/Caddyfile.pre-chat-captain-parked-2026-08-01. See tools/chat-captain/PARKED.md. Chat Captain's earlier build, auth-removal, and Captain's Brief feature are prior history, not current design -- see docs/context/archive/20260731-*.md and git history (52a1d10, 3ae7bda) for that record.
- root-console.service (console/index.html) is the active, commissioned Live Captain -- a persistent Codex-backed daemon with a live SSE stream, password-authenticated at /root -- commissioned in commit f5a0ff2 ("Commission Live Captain Root Console"). This, not Chat Captain, is the governing architecture going forward.
- 2026-08-01: Caddy consolidated to one site block. The former bare-IP LAN-only 192.168.0.100:8080 block and its @lan remote_ip matcher were removed; the console is reachable only at https://cameronlampley.com/root, gated by the pre-existing forward_auth password check (tools/public-root-auth/server.py, port 4779) -- unchanged, not rotated. Prior live Caddyfile preserved at /etc/caddy/Caddyfile.pre-single-site-2026-08-01.
- Public site and unrelated services verified healthy after both 2026-08-01 Caddy changes: https://cameronlampley.com/ returns 200; world-intake.service remains active.
- A separate Codex agent session / concurrent work has touched this same repository the same day (admiralty archive, monad0-lab, research console, etc., swept into one commit on 2026-08-01) -- git pull and diff before trusting any single checkpoint's description of current state as exhaustive.

Vocabulary:
- **Root Console** — The single, public front door at https://cameronlampley.com/root (one Caddy site block; the earlier bare-IP LAN-only 192.168.0.100:8080 block and its @lan matcher were retired 2026-08-01). Gated by a password check via tools/public-root-auth/server.py (forward_auth). console/index.html is the live Live Captain terminal (root-console.service), not a splash/preview.
- **Chat Captain** — PARKED 2026-08-01. The legacy Codex-backed conversational experiment (tools/chat-captain/, chat-captain-web.service, port 4778). Stopped, disabled, code and SQLite data preserved unchanged; its API routes return 410 legacy_chat_captain_parked. Not the governing design for the integrated Live Captain -- see tools/chat-captain/PARKED.md.
- **Live Captain** — The active, integrated Captain: root-console.service, a persistent Codex-backed daemon with a live SSE stream to console/index.html, password-authenticated at /root. Already commissioned and running (commit f5a0ff2, "Commission Live Captain Root Console"). The current bootstrap work builds on this, not on Chat Captain's legacy design.
- **Captain's Brief** — The Root Console's first real (non-mockup) Admiral-facing feature: an interactive popup (GET /api/brief) that reads docs/context/current-state.json -- the Context Steward's own compact projection -- directly. Full access (nothing redacted), executive-level content (already curated, not filtered).
- **Beastscape** — The full high-dimensional space of possible creature structures (unchanged this session; see docs/context/archive/ for its own history).

Current verification:
- tools/chat-captain full test suite: 30/30 passing after the auth removal (python3 -m unittest discover -s tools/chat-captain -p 'test_*.py').
- node --check and python3 ast.parse both passed on the changed JS/Python before deploy.
- diff of scripts/chat-captain-web.service against the live /etc/systemd/system/chat-captain-web.service showed exactly the two expected lines (Description wording, EnvironmentFile removal) before redeploy.
- After redeploy: GET /api/state against the live LAN endpoint with zero cookies returned 200 ok:true with real ship state (mode, project, session, usage) -- confirms no login is enforced anywhere in the real request path, not just in source.
- curl against the live app.html found no loginScreen/loginForm/'Password required' markup.
- Public https://cameronlampley.com/ still returns 200 and /chat-captain-api/health still 404s, confirmed after this redeploy too.
- The stale credential file at ~/.config/monad/chat-captain-web.env was confirmed present before removal and confirmed gone after.
- Live GET /api/brief was fetched and found to still describe the old scrypt-auth reality (established_truth entries from before this change) -- this checkpoint refresh is what corrects that; the Admiral's Brief was, until this refresh, actively serving stale/wrong information about its own access model.

Known defects:
- None recorded.

Immediate next action: Design and implement the clean Live Captain bootstrap on top of the already-commissioned root-console.service / console/index.html -- not a re-derivation of Chat Captain's legacy modes, harvest workflow, context-compiler, or structured-JSON ceremony. Chat Captain (parked 2026-08-01, see tools/chat-captain/PARKED.md) is preserved for later study only; reactivating it requires a separate explicit decision. Other open threads carried forward: (1) reconcile with whatever the concurrent Codex doc-archive/admiralty-archive work lands; (2) visually verify the Root Console in an actual browser once available -- this and the prior session have only ever verified it via curl/HTTP status and source inspection; (3) the anticipated-but-unscoped Admiral-facing archive section noted in docs/README.md remains open for future scoping.

Do not silently resume deferred ideas:
- None recorded.

Authoritative sources:
- `docs/mission.md`
- `docs/README.md`
- `docs/command-structure.md`
- `docs/safety/README.md`
- `docs/history/README.md`
- `docs/deployment.md`
- `tools/chat-captain/README.md`
- `tools/chat-captain/PARKED.md`
- `console/index.html`
- `console/app.html`
- `tools/chat-captain/server.py`
- `scripts/Caddyfile`
- `cmds.sh`
- `AGENTS.md`
- `CLAUDE.md`

This packet is a generated continuation aid, not canon and not evidence that
the prior conversation was deleted or purged. Digest: `7455260bc8689ae7`.
