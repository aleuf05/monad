# Recon Report — Captain's Algorithm & Root Console

Read-only investigation, no edits made during recon. Repo: `~/dev/monad`, as of 2026-08-02.

## Current-state summary
There is no single "Captain's Algorithm" in doctrine or code — the literal phrase appears nowhere in the repo. What exists instead is two structurally different, independently-running loops (a fully closed FleetCore decision loop, and an event-driven conversational turn loop), plus one fully-built observe-only loop that no running service invokes. The root console question has one clean answer: `tools/root-console/server.py` (`root-console.service`) is the sole, doctrinally-confirmed command surface — everything else called "console" is either a toy instrument panel or a service piggybacking on root-console's name/auth pattern.

## 1. Captain's Algorithm — live implementation

**The one complete, closed, 7-step loop: `tools/living-fleet/captain_runtime.py`** (service `living-fleet.service`, `ExecStart=... captain_runtime.py --interval 5`)
1. Read world state: `captain_runtime.py:208-210` `get_snapshot()` → `urllib.request.urlopen(f"{fleetcore_url}/snapshot")`
2. Interpret: `captain_runtime.py:222-248` `observation_for()`
3. Choose action: `captain_runtime.py:299-306` → `provider.decide(...)`; default `DoctrineProvider` (`:56-133`, rule-based); pluggable `CommandProvider` (`:136-153`) pipes JSON to an external subprocess via `MONAD_CAPTAIN_PROVIDER_COMMAND`
4. Execute: `captain_runtime.py:309-321` builds `submit-escort-intent`, POSTs via `post_command()` (`:212-220`) to FleetCore `/command`
5. Verify: client-side `validate_decision()` (`:156-177`) + server-side `fleetcore/src/world.rs:824-965` (rejects e.g. nonexistent target contact, `:916-926,963`)
6. Durable record: FleetCore `record_agent_decision()` (`world.rs:288`) → `world.agent_decisions`; Python side `_save_memory()` (`:201-206`) writes `data/living-fleet/runtime.json`
7. Repeat: literal `while True:` at `captain_runtime.py:405-420`, `time.sleep(max(1.0, args.interval))` — verified directly.

Trigger: always-on daemon, no cron for the main cycle. (One adjacent timer, `living-fleet-memory-reflect.timer`, fires every 30 min but its target `run_scheduled_reflection.py:31-33` currently no-ops without an `--enable-living-fleet` flag the unit doesn't pass.)

FleetCore transport: plain HTTP/JSON (`GET /snapshot`, `POST /command`, `fleetcore/src/bin/serve.rs:143-146`) — a `/ws` WebSocket also exists but no Captain-side Python code uses it.

Tests: `tools/living-fleet/test_captain_runtime.py`, `test_captain_runtime_memory.py`, `fleetcore/tests/living_fleet.rs:1-162`.

**Second loop — event-driven conversational Captain: `tools/live-captain/server.py` + `context_compiler.py`** (service `live-captain-bootstrap.service`)
- Context assembly is real code, not just templates: `context_compiler.py:51-75` `compile_live_captain_context()` concatenates kernel + bearing + ledger + conversation, with required-field validation (`:20-31`) and sha256 provenance digests.
- Full turn: read (`server.py:56-77,205`) → assemble (`:206-214`) → persist admiral msg (`:224-231`) → dispatch to Codex/Claude subprocess (`:238`) → verify (`:236-297`) → persist reply + diagnostics (`:260-316`).
- Trigger: one cycle per incoming `POST /api/turn` (`:173-317`); the backing daemon process is always-running independent of requests.
- Tests: `tools/live-captain/test_live_captain.py`.

**Unwired but real: `tools/living-captain/captain.py` (`LivingCaptain.observe()`)** — reads FleetCore + World Intake via a hardcoded read-only allow-list (`tools/living-captain/sight.py:7-10,25-34`), persists state + durable JSONL action log (`captain.py:99-134`). Explicitly no write/execute step by design (`captain.py:136-151` comment). Confirmed never called by any running service — only by demo/test scripts (`demo_boundary.py`, `demo_restart.py`, `test_captain.py`, `test_captain_v02.py`). The actually-running `status_server.py:1-9` says so itself: "This process never assembles a LivingCaptain instance, never calls observe()... it is a window onto the record left by whatever operator-invoked run wrote it last."

**Doctrine with no code correlate:** `docs/doctrine/2026-07-28-truth-engine.md:18-26` (observe→disconfirm→update loop; its cited implementation, `web/toys/truth-engine/index.html`, is a static mock-mode-only HTML file). `docs/doctrine/009-live-captain-authority-contract.md` — a contract text meant to be injected into every dispatched task (`:20-21`), but no dispatch code referencing or injecting it was found anywhere. `docs/doctrine/007-true-captain-operational-posture-draft.md` — explicitly an unpromoted draft, no code.

**Staleness flag:** `docs/reports/2026-07-15-architecture-map.md` predates `tools/live-captain`, `tools/living-captain-workbench`, and doctrine 007/009 (all created 2026-07-27 through 2026-08-01) — don't treat it as current.

## 2. Root console

- **Definitive answer: `tools/root-console/server.py`** (port 4792, `root-console.service`), fronted by `console/index.html` + `console/assets/js/root-console.js`, gated by `tools/public-root-auth/server.py` (port 4779) via Caddy `forward_auth` on `/root/*` and `/root-console-api/*` (`scripts/Caddyfile:61-77`, verified directly). Doctrinally confirmed as the command surface in `docs/command-structure.md:33-39` and `README.md:34-40`.
- **Player-facing instruments** (`toys/fleet-motion`, `bridge-station-3.0`, `agent-ops`) send real commands, but only into FleetCore's public simulated world over an unauthenticated WebSocket — verified directly: `fleetcore/src/bin/serve.rs:59-61` `fn authorized(&self, _presented: Option<&str>) -> bool { true }`, with an explicit comment at `:11` that this is deliberate, not an oversight. Separate authority domain from root-console by design.
- **Auth (verified):** single-user, no username, no roles, at both stacked gates. Layer 1 (`public-root-auth`, scrypt + HMAC, 1-year cookie `monad_root_session`). Layer 2 (`root-console/auth.py`, same scrypt pattern, 12-hour cookie `root_console_session`, rate-limited login).
- **Endpoints exposed (`server.py` `do_GET`/`do_POST`, verified directly at lines 177/279/288/316/328):** fully implemented — `/api/turn`, `/api/stream`, `/api/status`, `/api/handoffs*`, `/api/ship-log`, `/api/generated-image/*`, `/api/login`, `/api/logout`. Partially stubbed — `/api/research/command`: real research packets (`CAP-ARI-00x`) always return `AUTHORIZED_NOT_STARTED` per `research.py:138-143`; only a synthetic `CAP-ARI-003-DEMO` arc actually executes, tagged `dataMode: "MOCK"`.
- **Orphaned surface worth flagging:** `tools/root-console/static/index.html` + `static/app.js` is a second, older, smaller UI still served by `do_GET` at path `/` inside the same daemon — distinct from the real live `console/index.html`.

## 3. Gap list

| Item | Status |
|---|---|
| "Captain's Algorithm" as a named 7-step doctrine | Ghost — no doc, no code, uses that name. The loop shape exists (living-fleet), just unnamed. |
| `docs/doctrine/009-live-captain-authority-contract.md` dispatch injection | Ghost — doctrine only, no consuming code found |
| `docs/doctrine/2026-07-28-truth-engine.md` loop | Ghost for the Captain proper — only implementation is a static mock toy |
| `docs/doctrine/007-...-draft.md` | Explicitly an unpromoted draft, no code |
| `tools/living-captain/captain.py` (`LivingCaptain`) | Implemented, tested, not wired — no running service calls it |
| `living-fleet-memory-reflect.timer` | Fires on schedule but target currently no-ops (missing enable flag) |
| `tools/root-console/research.py` real packets | Implemented but not wired to any execution backend (mock arc only) |
| `toys/asset-viewer` "generate" action, `toys/character-voice-studio` "generate" action | Backend code exists (`img2asset` :8501, `voice-engine` :4775) but neither port is routed in the Caddyfile — inert on the live site |
| `tools/root-console/static/*` | Orphaned duplicate UI still reachable through the live daemon's `/` path |
| `docs/reports/2026-07-15-architecture-map.md` | Stale, predates several now-live services |

No recommendations included, per task instructions.
