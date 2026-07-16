# Shared engineering task queue

Protocol: see [`AGENTS.md`](../../AGENTS.md) at the repo root. Non-privileged,
git-only tasks only — nothing requiring `sudo` (that stays in `cmd.sh` /
`commissioning-handoff.md`).

## HUMAN-03 — Restore access to scout-screen-mode worktree

- Status: blocked-on-human
- Source: `GA-01` finding
- What's needed: someone with host permissions to resolve the "dubious
  ownership" git error on `.claude/worktrees/scout-screen-mode`, or
  confirm whether the locked worktree (`worktree-scout-screen-mode`) is
  still active work or safe to release. No agent this session could
  inspect it.
- Claimed by: — (needs host-level access)
- Evidence: —

## HEART-01 — Provision live model-provider credentials for Track A

- Status: blocked-on-human
- Source: Heart of Monad Implementation Packet (2026-07-16), Track A
  acceptance criteria -- "Pilot only needs two adapters wired live."
- What's needed: real API credentials for at least two of
  OpenAI/Anthropic/Google (a local provider needs none) so Track A's
  model provider adapters (`providers/openai.rs` etc.) can make real
  calls, not stubs, for the pilot mission. Admiral noted the Lieutenant
  may need to help obtain these.
- Claimed by: — (needs Lieutenant/Admiral to provision)
- Evidence: —
- Note: does not block Track B (Command Console / Command Architecture
  / FleetCore reader / Mission Record) or Phase 0 (shared types) --
  Track B's own acceptance criteria explicitly allows a stub graph in
  place of a finished Track A.

## GLUE-03 — Inventory and map component adapters

- Status: queued
- Source: missing-glue architecture review
- Depends on: GLUE-01
- Objective: map each existing component's real inputs/outputs onto the shared
  contract and identify the thinnest adapter required for each.
- Components: FleetCore, Cognition Graph, Living Fleet, Mission Director,
  World Intake, Legend Pipeline, img2asset, Agent Ops, Bridge, and Radio.
- Done evidence: report matrix naming endpoint/file, authority, adapter shape,
  missing fields, and whether the component is producer, consumer, or projection.

## GLUE-04 — Design Mission Coordinator lifecycle

- Status: queued
- Source: missing-glue architecture review
- Depends on: GLUE-01, GLUE-02, GLUE-03
- Objective: specify create, inspect, execute, pause/cancel, resume, timeout,
  human-review, and completion behavior for a lightweight coordinator.
- Constraint: orchestration never grants authority or applies FleetCore commands
  on its own.
- Done evidence: state machine, sequence diagram for one Kraken inquiry, failure
  recovery rules, and a bounded implementation packet.

## GLUE-05 — Generalize the human-review inbox

- Status: queued
- Source: missing-glue architecture review
- Depends on: GLUE-01, GLUE-02
- Objective: design a common review-card contract based on World Intake for
  cognition recommendations, command proposals, legend candidates, Chronicle
  proposals, and generated assets.
- Done evidence: review states, edit/regenerate/accept/reject semantics,
  authority rules, provenance display requirements, and mapping to current
  World Intake UI/API.

## GLUE-06 — Define artifact registry and projections

- Status: queued
- Source: missing-glue architecture review
- Depends on: GLUE-01, GLUE-02
- Objective: specify a registry that references existing mission reports,
  legends, images, GLBs, model outputs, screenshots, and Chronicle proposals
  without relocating or duplicating them.
- Done evidence: manifest schema plus projection rules for Agent Ops, Bridge,
  Radio, World Intake, Chronicle, and reports.

## GLUE-07 — Produce one end-to-end pilot execution packet

- Status: queued
- Source: missing-glue architecture review
- Depends on: GLUE-01 through GLUE-06
- Objective: convert the approved glue designs into one bounded implementation
  packet for a Kraken inquiry pilot using a stub cognition graph if live model
  credentials remain unavailable.
- Acceptance target: request → verified FleetCore evidence → competing findings
  → human decision → Mission Record → visible Agent Ops projection, with no
  mythology or interpretation written as FleetCore truth.
- Done evidence: authorized-ready Master Packet §13 implementation packet with
  acceptance tests, rollback, actor boundaries, and live visibility location.
