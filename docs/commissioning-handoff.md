# Commissioning handoff protocol

Monad has no passwordless sudo for agent sessions. Any privileged Granite
action—service restart, systemd installation, or `/etc/caddy/Caddyfile`
deployment—is staged by engineering and run by the Lieutenant through
`/home/cgl/cmd.sh`, outside the repository.

## Current-batch rule

`cmd.sh` contains only the current actionable batch. It is never a template,
placeholder, or stale prior rollout. If nothing is queued, it says so and exits
successfully.

Every privileged handoff must:

1. Pin `EXPECTED_HEAD` to the exact commit it commissions.
2. Refuse a dirty working tree or a different HEAD.
3. Refuse when a service it will restart is unhealthy before rollout.
4. Create one timestamped evidence directory under
   `/home/cgl/commissioning/` containing git state, before/after service
   status and journals, and an explicit rollback procedure.
5. Back up FleetCore's `world.json`, `events.jsonl`, and newest checkpoint,
   with SHA-256 hashes, before restarting or replacing FleetCore.
6. Use a completion marker and refuse accidental reuse.
7. Keep imports and installation steps idempotent wherever possible.

An agent must never leave the Lieutenant with a script that contains fillable
placeholders, refuses because it was already spent, or requires prose
interpretation to determine whether it is safe. That reads as broken rather
than cautious. Templates live elsewhere; the live file is executable work.

## After execution

Archive the executed script inside its evidence directory, record results and
any deviations, then flush `/home/cgl/cmd.sh` to a minimal “nothing queued”
script that exits zero. A spent command package must not remain presented as
current work.

Reusable unpinned templates belong under
`/home/cgl/commissioning/cmd-sh-templates/`; they are never installed directly
as the live handoff.

## Precedent

- `/home/cgl/commissioning/living-fleet-v0.1-20260713T231102Z/` — original
  Living Fleet persistence/determinism restart package.
- `/home/cgl/commissioning/living-fleet-v0.1-effort-b-20260714T000001Z/` —
  consolidated Caddy, memory-service, timer, FleetCore, and Living Fleet
  rollout.
- `/home/cgl/commissioning/host-reboot-20260714T011327Z/` — marker-gated real
  reboot proof with before/after canonical-state evidence.
- `/home/cgl/commissioning/cmd-sh-templates/` — reusable unpinned starting
  points, never the live handoff itself.
