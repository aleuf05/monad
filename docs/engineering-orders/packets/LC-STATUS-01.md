# Packet LC-STATUS-01 — Living Captain status API install

## Originating intent
The 2026-07-15 captain issue report noted Living Captain's static
frontend (`web/toys/living-captain/`, homepage card) was already live,
but its backend (`living-captain-status.service`) was not installed --
the page showed "Unreachable."

## Verified starting state
`tools/living-captain/status_server.py` and
`scripts/living-captain-status.service` existed in source, tested
(9/9, `test_sight.py`/`test_captain.py`/`test_captain_v02.py`), but no
systemd unit existed on the host (confirmed via
`systemctl list-unit-files` and `systemd/*.service` grep) and no
`/living-captain-api/*` Caddy route existed (confirmed via
`diff scripts/Caddyfile /etc/caddy/Caddyfile`).

## Objective / problem
Install the service and Caddy route so the already-live frontend's
status fetch stops returning "Unreachable."

## Scope
`living-captain-status.service` install (loopback-only, 127.0.0.1:4774,
read-only view over `data/living-captain/state.json` and
`actions.jsonl` -- never assembles a Captain instance, never calls
`observe()`), plus the matching `/living-captain-api/*` Caddy route.

## Exclusions
No change to `fleetcore-serve`, `world-intake`, or any other running
service. No canon-mutating write authority anywhere in this package.

## Constraints / authority
Requires `sudo` -- routed through `/home/cgl/cmd.sh` under
`docs/commissioning-handoff.md`'s protocol, not executed directly by
the agent. Gated: refuses on marker-already-completed, HEAD mismatch,
dirty tree, or `caddy` not active before rollout.

## Acceptance criteria
- `living-captain-status` service active
- Loopback (`127.0.0.1:4774/status`) returns correct `captain_id`
- Public (`https://cameronlampley.com/living-captain-api/status`)
  returns the same, through the new Caddy route

## Tests / rollback
Living Captain's own test suite run pre-install. Rollback procedure
written into the script's own `operator-notes.md` (stop/disable
service, remove unit file, restore prior Caddyfile, reload) --
documented, not exercised this session (see Doctrine 001, Target 8).

## Assigned actor
Lieutenant (sudo steps), script drafted by Claude.

## Evidence
- First attempt: died cleanly at the first `sudo` line, no side effects
  (`/etc/systemd/system/living-captain-status.service` absent, Caddyfile
  diff unchanged) -- re-pinned to current HEAD and re-run
- Second attempt: succeeded. `systemctl is-active living-captain-status`
  -> active. Both loopback and public endpoints returned matching,
  correct `captain_id: captain.monad`
- Evidence directory:
  `/home/cgl/commissioning/living-captain-status-api-20260715T131341Z/`

## Completion state
**verified complete -> recorded**
