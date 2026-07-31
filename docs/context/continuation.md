# Fresh-thread continuation packet

Assume Captain role. Continue the Monad project in `/home/cgl/dev/monad`.
Read `AGENTS.md`, `CLAUDE.md`, and the cited sources before changing state.

Mission: Monad organizes Cameron's cognitive landscape so valuable engineering work is preserved, connected, refined, and recoverable instead of becoming fragmented or buried (docs/mission.md). Beastscape and sibling Live Captain instruments remain active parallel product threads within that mission.

Active goal: A prior session crashed mid-redesign with uncommitted work; this session recovered state from disk and the host (not from chat memory), verified everything described was already fully built and live, then committed and pushed it as agent/living-world-intake-v0-1 commit 52a1d10. Nothing is currently blocked or in flight.

Established truth:
- Chat Captain (tools/chat-captain/: server.py, engine.py, database.py, codex_provider.py, context_compiler.py, harvest.py, usage_budget.py, configure_web_auth.py, plus unittest coverage) is built, authenticated (scrypt password + HMAC-signed session cookie), and installed as chat-captain-web.service -- confirmed active and healthy on the host (running clean 1h41m+ at last check, no crash-loop in the journal).
- The Root Console is deliberately LAN-only by explicit prior Admiral authorization (docs/deployment.md's 2026-07-31 entry): served at http://192.168.0.100:8080/ via a dedicated Caddy site block in scripts/Caddyfile, plain HTTP (no public cert obtainable for a bare LAN address). This is narrower than the retired web-lan/ pattern -- one console, not a mirrored site -- and required its own explicit conversation, not a default.
- A same-hostname LAN-detection approach (Caddy remote_ip matching on cameronlampley.com itself) was tried and disproved this cycle: the router's (Archer A7 / OpenWrt) NAT hairpin rewrites source IPs so LAN-originated traffic through the public hostname is indistinguishable from real internet traffic. Documented in docs/deployment.md so it isn't re-attempted without first re-verifying router behavior. Split-horizon DNS is the noted alternative if a same-hostname approach is wanted later.
- console/index.html (the splash) explicitly labels itself a non-functional visual preview and links to /app.html for the real app and to https://cameronlampley.com/ to exit; console/app.html is the actual login-gated, working conversation UI (console/assets/js/chat-captain.js).
- The public site is unaffected and was verified after the deploy: https://cameronlampley.com/ returns 200; https://cameronlampley.com/chat-captain-api/health returns 404 (no route exists there) -- confirmed both via cmds.sh's own verification block and independently this session.
- cmds.sh scripts/Caddyfile and scripts/chat-captain-web.service on disk in the repo were diffed byte-for-byte against the live /etc/caddy/Caddyfile and /etc/systemd/system/chat-captain-web.service on the host and found identical -- the redeploy in cmds.sh had already been executed before the crash, nothing was lost.
- This same session, README.md was substantially rewritten (dropping stale Bridge-Station-era content that no longer matched the site) and docs/ was restructured with new top-level entry points: docs/mission.md, docs/README.md (documentation map), docs/command-structure.md, docs/safety/README.md, docs/history/README.md. The older 001_MONAD_COMMAND_CHARTER_2026-07-15.md and docs/research/MONAD_SESSION_PACKETS_DRAFT_2026-07-31.md were preserved, not deleted, with notes marking them explicitly historical/draft and pointing forward to the current mission doc.
- docs/research/SEMANTIC_ARTIFACT_ENGINEERING.md and docs/research/OPERATIONAL_TOPOLOGY_PACKET_006_2026-07-31.md were added this session as new research material feeding the docs restructure.
- data/chat-captain/ (holding the runtime password salt/hash/session-secret env file) was added to .gitignore alongside the repo's existing data/ runtime-state pattern; no secrets were committed -- checked explicitly before commit.
- At commit time the working tree had 38 files changed (3648 insertions, 281 deletions) all landing in one commit (52a1d10) on agent/living-world-intake-v0-1, fast-forward pushed to origin with no conflicts.
- Before committing, the Admiral flagged that a separate Codex agent session is concurrently working on 'core doc archive' in the same repository. git fetch confirmed origin/agent/living-world-intake-v0-1 had not moved past this session's parent commit at push time, so no conflict occurred, but the next Captain should git pull and check docs/history/, docs/README.md, docs/mission.md, docs/command-structure.md, and docs/safety/ for Codex's changes before assuming this session's versions of those files are still current.

Vocabulary:
- **Root Console** — The new private, LAN-only front door at http://192.168.0.100:8080/ -- console/index.html is a visual splash/preview of its future UI; console/app.html is the real working Chat Captain app.
- **Chat Captain** — The authenticated, Codex-backed, persistent Admiral-Captain conversation service (tools/chat-captain/), served only on the LAN console, never on the public domain.
- **Beastscape** — The full high-dimensional space of possible creature structures (unchanged this session; see docs/context/archive/ for its own history).

Current verification:
- grep across tools/chat-captain/*.py, console/*.html, and the two new scripts/ files for credential-shaped strings found no hardcoded secrets; the one plaintext password is a test fixture in test_api.py, and the real runtime secret file lives in gitignored data/chat-captain/.
- http://192.168.0.100:8080/ fetched live this session: <title>Root Console — Monad</title>.
- http://192.168.0.100:8080/chat-captain-api/health fetched live this session: {"ok":true,"service":"chat-captain"}.
- https://cameronlampley.com/ returned 200 and https://cameronlampley.com/chat-captain-api/health returned 404, both fetched live this session.
- systemctl status/journalctl for chat-captain-web.service showed active (running), no restarts or errors since the last intentional redeploy 1h41m+ prior.
- diff of scripts/Caddyfile and scripts/chat-captain-web.service against the live /etc/caddy/Caddyfile and /etc/systemd/system/chat-captain-web.service returned no differences.
- git status --short was empty and git push was a clean fast-forward (ee32a7d..52a1d10) with no conflicting remote commits at push time.

Known defects:
- No graphical or headless browser is available anywhere in this environment (unchanged from prior sessions) -- the Root Console splash and app pages have been verified only via curl/HTTP status and source inspection, never an actual rendered screenshot or click-through.
- A concurrent Codex agent session was reported as working on 'core doc archive' in this same repository at the time of this session's commit; the next Captain should re-check docs/history/, docs/README.md, docs/mission.md, docs/command-structure.md, and docs/safety/ against origin before trusting this checkpoint's description of them as current.

Immediate next action: No committed next action from the Admiral yet. Open threads: (1) confirm with the Admiral whether the Root Console splash's proposed next features (Project Formation, Design, Review, Associative Lab, Record modes; the Harvest Tray Accept/Reject actions; the automatic containment/review queue) should move from mockup to real implementation, and in what order; (2) reconcile with whatever the concurrent Codex doc-archive session lands, since both sessions touched docs/history/ and related files independently; (3) visually verify the Root Console and Chat Captain UI in an actual browser on the LAN once available, since only HTTP/source-level verification has been possible here.

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
- `console/index.html`
- `console/app.html`
- `scripts/Caddyfile`
- `cmds.sh`
- `AGENTS.md`
- `CLAUDE.md`

This packet is a generated continuation aid, not canon and not evidence that
the prior conversation was deleted or purged. Digest: `58d3b814288f969e`.
