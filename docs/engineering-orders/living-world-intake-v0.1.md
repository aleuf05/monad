# Engineering Order: Living World Intake V0.1

Priority: High

Scope: Thin vertical slice

Doctrine: Narrative proposes. FleetCore decides. The record persists.

## Mission

Build a safe, inspectable pipeline that converts pasted engineering reports
into proposed FleetCore changes. Raw prose never directly mutates canonical
state.

The pipeline must preserve source bytes and provenance, extract and classify
candidate assertions, resolve identities, surface conflicts, support
Captain-controlled adjudication, compile approved proposals into normal
FleetCore commands, remain idempotent across retries/restarts, and correct
canon only through compensating events.

## Required layers

1. Source: immutable content, author, timestamp, attachments, mission context,
   and content hash.
2. Interpretation: machine-generated candidate assertions; never facts merely
   because they were extracted.
3. Adjudication: Captain actions: approve, approve with edit, reject, defer,
   flavor only, mark unverified, or link to an existing entity.
4. Canon: FleetCore-owned state changed only through its authenticated,
   authorized, schema-validated, domain-validated command path and persisted
   event log.

## V0.1 boundaries

Supported input: pasted engineering report.

Supported entities: crew, agent, station, department, vessel, contact.

Supported proposals: create entity, add alias, assign role/station, set
onboarding status, attach unverified capability, create reporting
relationship, record authorization request, and record approval/denial.

Assertion classes: identity, assignment, capability, permission, location,
relationship, event, request, claim, flavor.

Rules:

- Capabilities default to unverified.
- Permissions and command authority are never inferred.
- Requests are not completed events.
- Confidence is not authorization.
- Flavor and jokes remain non-operational.
- Alias ambiguity causes review; there is no silent merge or duplication.
- Material conflicts may be suggested but never automatically resolved.
- Permissions, command authority, reactor state, vessel movement, injury,
  death, and safety status require individual approval.
- The LLM is an interpreter, not a sovereign.

## Required components

- `world_intake`
- `assertion_extractor`
- `entity_resolver`
- `canon_validator`
- `adjudication_queue`
- `command_compiler`
- `provenance_index`
- Minimal intake API or CLI
- Minimal Captain review interface

Use existing SQLite conventions and FleetCore command/persistence paths unless
a demonstrated blocker requires a narrow extension.

## Acceptance fixture

Use the First-Wave Reactor Crew report. Extract nine recruits, their proposed
assignments, claimed capabilities, Deck 7 references, and the startup
authorization request.

Required behavior:

- Assignments may be approved.
- Capabilities remain unverified by default.
- Vance's scram assignment does not grant scram authority.
- Startup authorization remains pending; no reactor-start event is created.
- Flavor remains non-operational.
- Approved canon changes retain complete provenance.
- "Chief Claude" is treated as a possible alias, not silently created.
- Exclusive-role conflicts are surfaced.
- Repeated commits create no duplicates.
- Sources, reviews, canon events, and provenance survive restart.

## Codex delegation

This order uses the reusable split described in
`docs/workflows/split-delegated-engineering.md`: parallel hands own bounded
architectural layers, while the integration commander retains contract
reconciliation, combined verification, publication, and readiness judgment.

### FleetCore canon hand

Own `fleetcore/**`. Implement validated, persisted, replayable canonical-change
commands and state; expose canon in snapshots; enforce idempotency and domain
validation; support compensating/superseding records; add Rust tests. Preserve
backward compatibility using serde defaults.

### Intake core hand

Own `tools/world-intake/**`. Implement SQLite migrations, byte-preserving
source ingestion, extraction, resolution, conflict validation, adjudication,
command compilation, provenance queries, idempotency, restart persistence,
the reactor fixture, and the minimum acceptance suite.

### Review and operations hand

Own `toys/world-intake/**` and
`docs/architecture/world-intake-v0.1.md`. Implement the minimal Captain review
surface and operating notes. The interface must display subject, proposed
change, assertion class, source excerpt, confidence, current canon, conflicts,
compiled command, provenance, and every required review action.

### Integration commander

Own cross-layer integration, schema alignment, end-to-end tests, live safety
checks, commits, PR publication, and the completion recommendation.

## Scope freeze

Do not add autonomous storytelling, voices/images, procedural missions,
generalized ontology work, a new agent framework, broad UI redesign, a new
database without necessity, automatic approvals, model-authored permissions,
model-controlled movement/reactor state, source rewriting, automatic deletion,
or an unrestricted natural-language command endpoint.

## Completion recommendation

Return exactly one of:

- READY FOR LIVE INTAKE
- READY WITH LIMITATIONS
- HOLD FOR CORRECTION
