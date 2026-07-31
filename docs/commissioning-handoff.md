# Captain execution authority and exceptional handoff protocol

**Authority:** Lieutenant cgl, 2026-07-29.

After the one-time authority bootstrap, `cgl` has passwordless administrative
execution authority. Captain performs routine privileged Granite work
directly, including service, Caddy, unit, package, filesystem, and host
configuration changes within the active project course.

Human interruption is reserved for:

1. testing that genuinely requires human perception, judgment, credentials,
   hardware interaction, or acceptance; or
2. an inadequate, ambiguous, or conflicting course that cannot be resolved by
   inspection and engineering judgment.

Sudo is no longer itself a human handoff boundary.

## Caddy exception — Captain-controlled subsystem

**Authority:** Lieutenant cgl, 2026-07-29.

Caddy configuration and service lifecycle are explicitly delegated to Captain
control. The repository file `scripts/Caddyfile` is the intended live source
of truth, and `cgl` may receive narrowly scoped passwordless authority to
start, stop, restart, reload, and recover `caddy.service`.

Caddy work does not require a human approval handoff. Captain must still
validate configuration before reload,
verify the public site afterward, preserve the Portainer route, and report any
failed recovery plainly.

The later full-authority ruling supersedes Caddy-only delegation.

## Exceptional human-handoff rule

`cmd.sh` remains available for the one-time authority bootstrap and for rare
actions that technically require a human context despite Captain authority.
It contains only the current actionable batch. If nothing is queued, it says
so and exits successfully.

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
8. Link the current Captain issue report, and repin the live script after any
   report update that changes the repository HEAD.

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
