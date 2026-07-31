# Monad Root Console — Chat Captain

Persistent, Codex-backed Admiral–Captain conference. Ship state (SQLite) is
the sole continuity layer across restarts — see
`docs/doctrine/2026-07-27-continuity-truth-living-captain.md`, design
principle 5. Codex itself is used statelessly per turn (fresh ephemeral
thread each call); nothing about resuming this conversation depends on the
provider.

**Deliberately LAN-only.** Not exposed on the public
`https://cameronlampley.com/` domain — see `docs/deployment.md`'s
2026-07-31 exception entry for why and how this differs from the retired
`web-lan/` pattern. Live at `http://192.168.0.100:8080/` on the home LAN
only.

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
- `server.py` — authenticated loopback HTTP API (scrypt password + signed
  session cookie, same mechanism as `tools/living-captain/web_service.py`,
  minus the `Secure` cookie attribute since the LAN Caddy block is plain
  HTTP).
- `usage_budget.py` — daily turn-count ceiling (Codex has no metered
  per-token API key from this codebase's perspective, so this guards
  against runaway loops rather than approximating dollar cost).
- `configure_web_auth.py` — provisions `~/.config/monad/chat-captain-web.env`.

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
