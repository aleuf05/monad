# Monad Documentation

This is the enduring conceptual map of Monad's documentation. It organizes
existing material by what it explains rather than by when it was implemented.
Dated packets, reports, and logs retain their original paths and status.

## Mission

- [Project Mission](mission.md) — current purpose and supporting mechanisms.
- [Highest-Priority Charter](../000_HIGHEST_PRIORITY_MONAD_CHARTER_2026-07-14.md)
  — standing duty to protect the human and the hull.

## Architecture

- [`architecture/`](architecture/) — component and system designs.
- [Architecture map](reports/2026-07-15-architecture-map.md) — dated system map.
- [Artifact registry and projections](architecture/artifact-registry-projections-v0.1.md)
  — provenance-preserving audience views.

Architecture documents describe mechanisms supporting the mission. Their
status labels distinguish implemented reality from proposals and drafts.

## Command Structure

- [Command Structure](command-structure.md) — current authority model and role
  boundaries.
- [Command charter](../001_MONAD_COMMAND_CHARTER_2026-07-15.md) — provisional,
  historically important formulation.
- [Crew role assignment](architecture/model-agnostic-crew-role-assignment.md).
- [`doctrine/`](doctrine/) — standing and proposed operating rules.

## Cognitive Landscape

- [Living archive proposal](research/MONAD_ACTUAL_LIVING_ARCHIVE_V0.1_24H_PROPOSAL_2026-07-27.md).
- [Private conference knowledge loop](research/PRIVATE_CONFERENCE_KNOWLEDGE_LOOP_DRAFT_2026-07-27.md).
- [`context/`](context/) — generated continuity projections and checkpoints.

This section concerns how ideas, decisions, questions, evidence, and project
relationships become navigable without treating every thought as an order.

## Safety

- [Safety overview](safety/README.md) — project-wide operational synthesis.
- [Human state safety intent](research/HUMAN_SAFETY_INTENT_DRAFT_2026-07-27.md)
  — draft safety record with explicit human-state safeguards.
- [Human distress assistance doctrine](research/HUMAN_DISTRESS_ASSISTANCE_DOCTRINE_2026-07-14.md).
- [Archive stewardship](doctrine/005-captain-archive-stewardship.md) — authority
  retained by the human.

## Memory

- [Continuity, Truth, and the Living Captain](doctrine/2026-07-27-continuity-truth-living-captain.md).
- [Context Steward](../tools/context-steward/README.md).
- [Living Fleet memory](../tools/living-fleet/README.md).
- [Session packets](research/MONAD_SESSION_PACKETS_DRAFT_2026-07-31.md) — draft
  preservation record, not canon.

Memory is an inspectable aid to continuity, not an independent authority or a
substitute for source records.

## Semantic Artifact Engineering

- [Semantic Artifact Engineering](research/SEMANTIC_ARTIFACT_ENGINEERING.md) —
  current research methodology and review loop.
- [IntentForge core concept](research/INTENTFORGE_CORE_CONCEPT_PACKET_V1_2026-07-28.md).
- [Beast Structural Latent Space](research/BEAST_STRUCTURAL_LATENT_SPACE_DRAFT_2026-07-29.md).

## Engineering Methodology

- [`workflows/`](workflows/) — repeatable engineering practices.
- [`engineering-orders/`](engineering-orders/) — active work, briefs, and
  bounded execution packets.
- [`verification/`](verification/) and [`reports/`](reports/) — evidence and
  findings.
- [Logging doctrine](logging-doctrine.md).

## Research Programs

- [`research/`](research/) — proposals, field cards, research minutes, and
  evolving conceptual models.
- [Operational Topology — Packet 006](research/OPERATIONAL_TOPOLOGY_PACKET_006_2026-07-31.md)
  — candidate formalism for constrained human–AI operational flows.
- [Semantic Artifact Engineering](research/SEMANTIC_ARTIFACT_ENGINEERING.md) —
  intent, semantic refinement, projection, review, and knowledge capture.
- [Monad Reality Program](research/MONAD_REALITY_PROGRAM_DRAFT_2026-07-28.md).
- [Core Reality research proposal](research/MONAD_CORE_REALITY_RESEARCH_PROPOSAL_2026-07-14.md).

Research status must remain visible. A draft hypothesis does not become canon
or implementation truth by being linked here.

## Historical Archive

- [Historical Continuity](history/README.md) — evolution map and reading rules.
- [Chronicle of Vessel Monad](../002_CHRONICLE_OF_VESSEL_MONAD_2026-07-16.md).
- [`logs/`](logs/), [`handoff/`](handoff/), [`incidents/`](incidents/), and
  [`context/archive/`](context/archive/) — dated operational memory.
- **Anticipated, not yet built:** an Admiral-facing section of this archive —
  a curated, executive-level read surface over Captain records, distinct from
  the full operational log. Not scoped or scheduled; noted here so the
  archive's structure and any related tooling (e.g. the Root Console's
  [Captain's Brief](../tools/chat-captain/README.md)) aren't designed in a
  way that forecloses it.

## Reading status correctly

1. Read the document's status and date before its claims.
2. Prefer current mission and adopted doctrine for present framing.
3. Treat reports as dated evidence, not timeless architecture.
4. Treat drafts and proposals as preserved possibilities, not authorization.
5. Follow provenance links when formulations conflict; do not silently merge
   them into a false consensus.
