# Current context brief

> Compact projection, not project canon. Generated `2026-07-31T14:15:57+00:00` from cited
> repository sources. Input digest: `883f4932fd5e38f2`.

## Mission

Monad organizes Cameron's cognitive landscape so valuable engineering work is preserved, connected, refined, and recoverable instead of becoming fragmented or buried (docs/mission.md). Beastscape and sibling Live Captain instruments remain active parallel product threads within that mission.

## Active course

Continuing the Root Console redesign begun after a prior-session crash recovery: shipped Chat Captain's first real Admiral-facing feature (Captain's Brief), then removed the console's application-level password entirely at the Admiral's explicit direction, since the LAN-only Caddy site block it lives behind is deliberately the whole access-control boundary. Both changes are committed, deployed, and verified live. Nothing is currently blocked or in flight; the Admiral flagged this as careful foundational work, not a rush.

## Working vocabulary

- **Root Console** — The private, LAN-only front door at http://192.168.0.100:8080/ -- console/index.html is a visual splash/preview of its future UI; console/app.html is the real working Chat Captain app. No application-level login on either.
- **Chat Captain** — The Codex-backed, persistent Admiral-Captain conversation service (tools/chat-captain/), served only on the LAN console, never on the public domain. Access control is network isolation only, not a password.
- **Captain's Brief** — The Root Console's first real (non-mockup) Admiral-facing feature: an interactive popup (GET /api/brief) that reads docs/context/current-state.json -- the Context Steward's own compact projection -- directly. Full access (nothing redacted), executive-level content (already curated, not filtered).
- **Beastscape** — The full high-dimensional space of possible creature structures (unchanged this session; see docs/context/archive/ for its own history).

## Established truth

- Chat Captain (tools/chat-captain/: server.py, engine.py, database.py, codex_provider.py, context_compiler.py, harvest.py, usage_budget.py, plus unittest coverage) is built and installed as chat-captain-web.service -- confirmed active and healthy on the host after the most recent redeploy, with no restarts or errors.
- The Root Console is deliberately LAN-only by explicit prior Admiral authorization (docs/deployment.md's 2026-07-31 entry): served at http://192.168.0.100:8080/ via a dedicated Caddy site block in scripts/Caddyfile, plain HTTP (no public cert obtainable for a bare LAN address). This is narrower than the retired web-lan/ pattern -- one console, not a mirrored site.
- As of 2026-07-31 (same day, later amendment), Chat Captain and the Root Console have NO application-level password. An earlier version carried a scrypt password + HMAC-signed session cookie (copied from tools/living-captain/web_service.py); the Admiral had it removed on the reasoning that the console's LAN-only Caddy site block already IS the access-control boundary -- only the Admiral has physical/network access to that LAN, so the boundary is already binary before any password is checked, and a password on top of it was a second access-control system solving a problem the first one already solved. configure_web_auth.py was deleted; the stale credential file at ~/.config/monad/chat-captain-web.env was removed from the host. The POST Origin allowlist check was kept -- that is ordinary CSRF hygiene, not an access-control gate, and costs the Admiral nothing.
- The Root Console's first real (non-mockup) feature is Captain's Brief: an authenticated-by-nothing (no login needed, same as everything else now) GET /api/brief endpoint that reads docs/context/current-state.json directly and an interactive popup in console/app.html (also linked from console/index.html's splash via /app.html?brief=1, auto-opening once the app has loaded). This reuses the Context Steward's own projection rather than building a second summarization path -- full access by construction (nothing redacted), executive-level by construction (already curated), matching the Admiral-level access model requested.
- console/index.html (the splash) explicitly labels itself a non-functional visual preview; two things on it are real: the Captain's Brief link and the Exit to Public Site link. console/app.html is the actual, working conversation UI (console/assets/js/chat-captain.js), now loading directly with no login screen.
- The public site is unaffected and was verified after both this session's deploys: https://cameronlampley.com/ returns 200; https://cameronlampley.com/chat-captain-api/health returns 404 (no route exists there).
- The full tools/chat-captain test suite (30 tests, including test_api.py rewritten to drop all login/session/password test scaffolding) passes after the auth removal.
- docs/deployment.md carries two dated entries on this: the original 2026-07-31 LAN-only exception (network isolation as the security boundary), and a same-day amendment entry documenting the password removal and the reasoning above -- both are the authoritative record; this checkpoint summarizes, doesn't replace them.
- Earlier the same day: this session recovered from a prior-session crash by reading disk/host state directly (not chat memory), found the LAN Root Console splash-plus-old-site-link redesign already fully built and deployed, committed it (52a1d10), then added Captain's Brief (3ae7bda) before this auth-removal change. README.md was substantially rewritten and docs/ restructured with new top-level entry points (docs/mission.md, docs/README.md, docs/command-structure.md, docs/safety/README.md, docs/history/README.md), preserving older material as marked historical/draft rather than deleting it.
- A separate Codex agent session was reported mid-session as concurrently working on 'core doc archive' in this same repository. git fetch checks before each push this session found origin/agent/living-world-intake-v0-1 had not moved past this session's parent commit, so no conflicts occurred -- but the next Captain should still git pull and diff docs/history/, docs/README.md, docs/mission.md, docs/command-structure.md, and docs/safety/ against origin before trusting this checkpoint's description of them as current.
- docs/README.md notes (added this session, still standing) that an Admiral-facing section of the historical archive is anticipated but not yet scoped, per the Admiral's own flag -- noted so neither the doc map nor related tooling like Captain's Brief forecloses it.

## Decisions

- Network isolation (the LAN-only Caddy site block) is the entire access-control boundary for the Root Console and Chat Captain -- not network isolation plus a password. The Admiral was explicit that reinventing a second access-control system on top of the first, when the first already does the whole job, was the exact mistake to avoid; don't reintroduce a login without a reason the network boundary doesn't already cover.
- The Root Console splash page is intentionally a non-functional preview shipped alongside the real, functional app rather than gating the real app behind an unfinished redesign; Captain's Brief is the first crack in that -- a real feature surfaced through the splash.
- Historical/superseded documentation is marked and cross-linked forward rather than deleted, per docs/history/README.md's reading rules.
- This is explicitly foundational, unhurried work in the Admiral's own words ('this isn't a sprint'), aimed at reshaping how the system gets used going forward -- weight correctness and care over speed on this thread specifically.

## Live and changed surfaces

- tools/chat-captain/server.py -- no login route, no session cookie, no password verification; GET /api/brief added and unaffected by the auth removal (it was never behind anything but the same non-existent gate).
- tools/chat-captain/configure_web_auth.py -- deleted (unused once the password was removed).
- tools/chat-captain/test_api.py -- rewritten without login/session scaffolding; 30/30 suite passes.
- console/app.html, console/assets/js/chat-captain.js -- login screen and all related markup/JS removed; app loads directly. Captain's Brief popup unaffected.
- console/index.html -- banner text updated to state plainly there is no password.
- scripts/chat-captain-web.service -- EnvironmentFile line (pointing at the now-deleted credential file) removed; installed live and restarted.
- scripts/install-chat-captain-web.sh -- auth-file provisioning step removed.

## Verification

- None recorded.

## Known defects

- None recorded.

## Next action

No committed next action from the Admiral yet beyond what's already landed. Open threads carried forward: (1) confirm with the Admiral whether the Root Console splash's remaining proposed panels (Project Formation/Design/Review/Associative Lab/Record mode chips, Harvest Tray Accept/Reject, the automatic containment/review queue) should move from mockup to real, and in what order -- Captain's Brief is a precedent for doing this incrementally; (2) reconcile with whatever the concurrent Codex doc-archive session lands; (3) visually verify the Root Console and Chat Captain UI (including the now-gateless load) in an actual browser on the LAN once available; (4) the anticipated-but-unscoped Admiral-facing archive section noted in docs/README.md remains open for future scoping.

## Deferred ideas

- None recorded.

## Source paths

- `docs/mission.md`
- `docs/README.md`
- `docs/command-structure.md`
- `docs/safety/README.md`
- `docs/history/README.md`
- `docs/deployment.md`
- `tools/chat-captain/README.md`
- `console/index.html`
- `console/app.html`
- `tools/chat-captain/server.py`
- `scripts/Caddyfile`
- `cmds.sh`
- `AGENTS.md`
- `CLAUDE.md`

## Omissions

- deferred_ideas
- defects
- verification
- changed_surfaces
