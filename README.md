# HIGHEST PRIORITY

Read [`000_HIGHEST_PRIORITY_MONAD_CHARTER_2026-07-14.md`](000_HIGHEST_PRIORITY_MONAD_CHARTER_2026-07-14.md) before any other repository document.

# Monad

Monad organizes Cameron's cognitive landscape so valuable engineering work is
preserved, connected, refined, and recoverable instead of becoming fragmented
or buried.

The persistent workspace, command interfaces, memory systems, maritime world,
and browser instruments are mechanisms supporting that mission. They are not,
individually, the mission itself.

## Start here

- [Project mission](docs/mission.md) — purpose, scope, and the relationship
  between the mission and its mechanisms.
- [Documentation map](docs/README.md) — the durable conceptual entry point for
  architecture, command, safety, memory, research, and history.
- [Safety](docs/safety/README.md) — human authority, bounded AI roles, approval
  gates, least privilege, and the boundary between thought and action.
- [Semantic Artifact Engineering](docs/research/SEMANTIC_ARTIFACT_ENGINEERING.md)
  — the current intent-to-artifact research methodology.
- [Historical archive](docs/history/README.md) — earlier formulations and the
  path by which the current architecture emerged.
- [Admiralty Archive](admiralty/archive/README.md) — executive reading layer
  over the repository record.

## Current system

Monad's implemented systems include:

- a private Root Console and Captain collaboration environment;
- public experiments and browser instruments;
- FleetCore, a deterministic maritime world-model prototype;
- memory, archive, context-restoration, and provenance systems;
- engineering workflows, mission records, review surfaces, and research tools.

The private cognitive and command environment is intentionally distinct from
public experimentation. Public artifacts may project selected work outward;
they do not inherit private memory or Root Console authority. Some historical
public demos intentionally permit control of their shared simulated world;
[`docs/deployment.md`](docs/deployment.md) records that narrower implementation
choice and its limitations.

For implementation details, begin with [Architecture](docs/README.md#architecture),
then follow the component-level README files. The live public front door is
`https://cameronlampley.com/`; repository deployment rules are documented in
[`docs/deployment.md`](docs/deployment.md).

## Repository guide

| Path | Purpose |
|---|---|
| `docs/` | Mission, doctrine, architecture, research, reports, and history |
| `fleetcore/` | Deterministic maritime state and command model |
| `tools/` | Cognitive, memory, artifact, and engineering utilities |
| `toys/` | Experimental browser instruments and research projections |
| `web/` | Public-site material and deployed projections |
| `logs/` | Operational records |
| `intentforge/` | Intent-to-geometry translation experiments |

## Engineering entry points

- [`AGENTS.md`](AGENTS.md) and [`CLAUDE.md`](CLAUDE.md): repository operating
  instructions.
- [`docs/engineering-orders/queue.md`](docs/engineering-orders/queue.md): active
  non-privileged work.
- [`docs/engineering-orders/packets/README.md`](docs/engineering-orders/packets/README.md):
  bounded engineering packet format.
- [`docs/reports/2026-07-15-system-reality-report.md`](docs/reports/2026-07-15-system-reality-report.md):
  dated implementation evidence; verify current state before relying on it.

Monad is under active development. Dated records preserve what was believed or
implemented at a particular time; status labels and current entry points govern
how those records should be interpreted today.

## License

License information has not been finalized.
