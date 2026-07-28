# Captain/Commander Briefing — Live Captain Version 1

Date: 2026-07-28

Audience: incoming Captain / Commander

Classification: Technical finding and operational handoff

## Executive state

Live Captain Version 1 is operational on Granite in two forms:

1. a local terminal conversation client; and
2. an authenticated Private Conference panel on the live Monad site.

The web service is active and enabled, binds only to `127.0.0.1:4776`, and is
reachable publicly only through Caddy at `/live-captain-chat-api/*`. The
existing public read-only Living Captain status service on port 4774 remains
independent.

Live page:

`https://cameronlampley.com/toys/living-captain/`

The human-selected conference password, its verifier, the Gemini API key, and
session-signing secret are not recorded here or in Git.

## Verified evidence

- `live-captain-web.service`: active and enabled.
- Listener: `127.0.0.1:4776`, not a public bind.
- Public health endpoint: HTTP 200.
- Unauthenticated transcript request: HTTP 401.
- Authenticated status request through the real domain: HTTP 200.
- Authenticated Gemini message through the real domain: HTTP 200.
- Provider: `gemini-3.5-flash-lite`.
- Offline suite: 25 tests passing.
- Runtime credential file: mode 0600, owner `cgl:cgl`.
- Service log showed no error or restart loop after acceptance.
- Live UI visibly contains `Private Conference — NEW`.

At final acceptance the persistent usage ledger contained six total attempts
and a deliberately conservative reserved estimate of `$0.019164`. This is a
local upper-bound estimate, not a provider billing statement.

## Architecture

```text
Admiral
  -> terminal client OR authenticated browser
  -> single-owner CaptainEngine
  -> append-only transcript + durable usage ledger
  -> provider-neutral ModelProvider
  -> Gemini adapter
  -> Gemini API
```

The terminal and web service cannot own conversation state simultaneously.
An exclusive `owner.lock` makes the second interface fail closed instead of
racing transcript sequences or usage writes.

The running web service currently owns the conversation. Starting
`/home/cgl/captain.sh` while the service is active should therefore report an
ownership conflict. This is expected continuity behavior, not a defect.

## Security and authority boundary

The conversational Captain has:

- no shell;
- no tools;
- no uploads;
- no arbitrary file path;
- no autonomous work;
- no background inference;
- no canon mutation;
- no public listening socket.

Browser transcript access and message submission require authentication.
The session cookie is signed, expires after 12 hours, and is marked
`HttpOnly`, `Secure`, and `SameSite=Strict`.

The service rejects:

- cross-origin writes;
- missing authentication;
- oversized bodies and messages;
- concurrent inference;
- repeated login attempts above the bounded window;
- suspected API keys in messages;
- requests beyond the persistent usage boundary.

Gemini failure preserves the user message, returns a clear unavailable state,
and records no invented Captain reply.

## Continuity behavior

The old public status instrument and the new Private Conference are separate.
If Gemini or the conference service fails:

- the static live page still loads;
- the public read-only status instrument remains useful;
- the UI reports conference unavailability;
- conversation history remains on disk;
- no simulated reply replaces the failed inference.

This implements Doctrine 007: the system remains useful while partially
broken.

## Principal files

Implementation:

- `tools/living-captain/live_captain_engine.py`
- `tools/living-captain/live_captain_cli.py`
- `tools/living-captain/web_service.py`
- `tools/living-captain/gemini_provider.py`
- `tools/living-captain/conversation.py`
- `tools/living-captain/usage_budget.py`
- `tools/living-captain/prompts/captain-system.md`

Authentication and commissioning:

- `tools/living-captain/configure_web_auth.py`
- `scripts/live-captain-web.service`
- `scripts/install-live-captain-web.sh`
- `scripts/Caddyfile`

Live UI:

- `toys/living-captain/`
- `web/toys/living-captain/`

Records:

- `docs/engineering-orders/packets/LIVE-CAPTAIN-VERSION-1.md`
- `docs/engineering-orders/packets/LIVE-CAPTAIN-SITE-INTEGRATION-VERSION-1.md`
- `docs/workflows/LIVE-CAPTAIN-HUMAN-ACCEPTANCE-TEST-VERSION-1.md`
- `docs/doctrine/007-continuity-under-failure.md`
- `docs/doctrine/2026-07-27-continuity-truth-living-captain.md`

Private runtime state:

- `data/living-captain/conversation.jsonl`
- `data/living-captain/conversation-state.json`
- `data/living-captain/usage.json`
- `data/living-captain/live-captain.log`
- `data/living-captain/owner.lock`

Do not print, publish, or delete these runtime files casually.

## Relevant commits

- `b1ba1ca` — Build Live Captain Version 1 terminal chat
- `959a4ed` — Document Live Captain human acceptance test
- `f08da50` — Record continuity under failure doctrine
- `872f405` — Build authenticated Live Captain site conference
- `5ab0239` — Mark commissioning scripts executable
- `705bbbf` — Deploy Live Captain Private Conference

The current branch was six commits ahead of its upstream at handoff. These
commits were local and had not been pushed during this operation.

The worktree also contains unrelated pre-existing modifications and untracked
files. Do not sweep, reset, stage, or commit them as part of Live Captain
maintenance.

## Operator actions

Normal web use:

1. Open the live Living Captain page.
2. Find `Private Conference — NEW`.
3. Enter the human-selected conference password.
4. Converse normally.
5. Use `Leave` to clear the browser session cookie.

Read-only health checks:

```text
systemctl status live-captain-web.service --no-pager
curl https://cameronlampley.com/live-captain-chat-api/health
ss -ltnp | grep 4776
```

Run tests:

```text
python3 -m unittest discover -s tools/living-captain -p 'test_*.py' -v
```

## Recovery

If the conversation service fails:

1. Preserve logs and runtime state.
2. Confirm the exact service failure.
3. Confirm no terminal Captain owns the conversation.
4. Validate the repository Caddyfile and service source.
5. Restart only the failed service after identifying the cause.

The commissioning installer preserved the prior Caddy configuration at:

`/etc/caddy/Caddyfile.pre-live-captain-v1`

Do not restore it blindly: validate the current and prior configurations and
confirm what later routes may have changed.

`/home/cgl/cmd.sh` was a one-time, commit-pinned commissioning handoff. Its
pin predates the final UI deployment commit, so rerunning it should fail
closed. Prepare a new reviewed handoff for any future privileged change.

## Known limitations and next watch

1. The `$2` application boundary is a conservative local approximation.
   Provider-side spend controls remain the billing backstop.
2. Conversation is grounded in its transcript and local Captain prompt, not
   yet in a fresh, source-labeled FleetCore snapshot for every answer.
3. Authentication supports one human-operated password, not multiple users or
   roles.
4. No adoption/outcome analytics exist beyond usage accounting.
5. The terminal and web service are intentionally mutually exclusive. A
   future terminal client could talk to the running local service instead of
   competing for ownership.

Recommended next bounded feature:

Add a deterministic, source-labeled live-state summary to the Captain context
so the human can ask, “What is happening right now?” and receive an answer
explicitly separating observed, derived, simulated, narrative, and unknown
claims. Preserve the current read-only authority and cost boundary.

## Command recommendation

Maintain station. Do not expand tool or command authority yet.

Observe real human use of the Private Conference, record friction and useful
outcomes, and let evidence determine the next whole-number version.
