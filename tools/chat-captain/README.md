# Monad Root Console — Chat Captain

Persistent, Codex-backed Admiral–Captain conference. Ship state (SQLite) is
the sole continuity layer across restarts — see
`docs/doctrine/2026-07-27-continuity-truth-living-captain.md`, design
principle 5. Codex itself is used statelessly per turn (fresh ephemeral
thread each call); nothing about resuming this conversation depends on the
provider.

**Deliberately LAN-only, and that LAN-only-ness *is* the access control.**
Not exposed on the public `https://cameronlampley.com/` domain — see
`docs/deployment.md`'s 2026-07-31 exception entry for why and how this
differs from the retired `web-lan/` pattern. Live at
`http://192.168.0.100:8080/` on the home LAN only. **There is no
application-level password.** An earlier version had one (scrypt +
session cookie); it was removed 2026-07-31 as redundant once it was
confirmed the console is its own isolated network-layer boundary, not a
path carved out of the public site — only the Admiral has physical/network
access to this LAN, so a second gate on top of that binary boundary added
friction without adding security. Do not reintroduce a login without a
reason the network boundary itself doesn't already cover.

## Layout

- `database.py` — SQLite schema: `captain_state`, `projects`, `sessions`,
  `messages`, `harvest_items`, `mode_events`.
- `codex_provider.py` — `ModelProvider` implementation backed by a
  persistent `codex app-server` subprocess; each turn starts a fresh
  ephemeral thread (see the docstring for why).
- `context_compiler.py` — builds the per-turn context envelope (identity,
  current situation, bounded recent window, output contract) and parses
  the ` ```captain-json ` structured reply block, with a safe fallback if
  the model omits or malforms it.
- `harvest.py` — validates harvest proposals before they are ever stored;
  malformed proposals are dropped, never stored as garbage.
- `engine.py` — `CaptainEngine`: owns the exclusive lock on ship state
  (`fcntl.flock`, mirrors `tools/living-captain/live_captain_engine.py`)
  and drives one full turn end-to-end.
- `server.py` — loopback HTTP API. No login: the LAN-only Caddy site block
  is the access boundary (see above). POST requests still check `Origin`
  against `CHAT_CAPTAIN_ALLOWED_ORIGINS` as ordinary CSRF hygiene, not as
  an access-control gate. Includes `GET /api/brief` — the Root Console's
  "Captain's Brief" popup: a thin read of `docs/context/current-state.json`
  (the Context Steward's own compact projection), not a second
  summarization path. Full access, executive-level content by
  construction, not by redaction.
- `usage_budget.py` — daily turn-count ceiling (Codex has no metered
  per-token API key from this codebase's perspective, so this guards
  against runaway loops rather than approximating dollar cost).

Static frontend lives in `console/` at the repo root (its own deploy
target, parallel to `web/`), not under `tools/chat-captain/` — see
`docs/deployment.md`.

## Commissioning

```sh
scripts/install-chat-captain-web.sh
```

Provisions the auth secrets file (if missing), runs the test suite,
installs the systemd unit and Caddy site block, and verifies both the
loopback health endpoint and the public-facing-but-LAN-only route.

## Tests

```sh
python3 -m unittest discover -s tools/chat-captain -p 'test_*.py'
```
