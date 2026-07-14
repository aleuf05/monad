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

## After execution

Archive the executed script inside its evidence directory, record results and
any deviations, then flush `/home/cgl/cmd.sh` to a minimal “nothing queued”
script that exits zero. A spent command package must not remain presented as
current work.

Reusable unpinned templates belong under
`/home/cgl/commissioning/cmd-sh-templates/`; they are never installed directly
as the live handoff.
