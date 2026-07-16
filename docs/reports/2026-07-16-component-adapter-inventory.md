# Component Adapter Inventory — GLUE-03

Date: 2026-07-16

This report maps the real component boundaries onto
`docs/architecture/mission-evidence-contracts-v0.1.md`. It proposes thin
adapters, not rewrites. An adapter translates identifiers and records
provenance; it never inherits the wrapped component's authority.

## Adapter rule

Every adapter accepts a `MissionEnvelope` plus referenced inputs and returns
zero or more `EvidenceRef` / `ArtifactResult` objects. It must preserve the
component's native receipt or cursor in `data`, never infer approval, and never
copy FleetCore world state into a second authoritative store.

## Inventory

| Component | Real input boundary | Real output boundary | Authority today | Role | Thinnest adapter | Missing shared fields |
|---|---|---|---|---|---|---|
| FleetCore | `GET /snapshot`, `GET /ws`; typed JSON commands at `POST /command` or WebSocket | `WorldSnapshot`, command HTTP response, WS broadcasts, durable `events.jsonl` | Sole operational world/canon owner; validates commands | Evidence producer and command target | Read-only `fleetcore-reader` selects stable event IDs/cursors and emits `verified-state` refs. A separate command-receipt adapter records proposed command, response, and resulting event; coordinator never posts directly. | Mission/correlation ID is absent from most commands/events; evidence observation timestamp and locator must be added externally. |
| Cognition Graph | Browser textarea; optional Anthropic key in browser `localStorage`; direct Anthropic `/v1/messages` calls | Framer JSON, four role JSON results, verifier JSON, visible verdict; no durable output | No operational authority; simulated/live mode is UI state | Artifact producer | Browser export function wraps the original question as an inquiry mission and each node/verdict as `generated-candidate` artifacts. Include mode, provider, model, role, and prompt version in `data`. | No stable run/artifact IDs, timestamps, evidence refs, persistence, model ID receipt, or export API. |
| Living Fleet | Polls FleetCore `/snapshot`; optional provider command over stdin/stdout | `submit-escort-intent` via FleetCore `/command`; local runtime state; FleetCore `agent_decisions` receipts | May propose only bounded posture for assigned captain; FleetCore decides | Evidence consumer, artifact producer, command proposer | Cycle wrapper records snapshot evidence cursor, provider/fallback identity, proposed intent artifact, and accepted/rejected FleetCore receipt. | No shared mission/correlation ID or explicit evidence-ref list; provider metadata is component-specific. |
| Mission Director | FleetCore snapshot/events and operator CLI actions | State JSON, evidence array, capture requests, `log.md`, `index.html`; two bounded FleetCore commands | Observes progress; may spawn its mission contact and append watch milestones only | Mission-envelope producer, evidence/artifact producer | Import existing mission JSON directly: mission ID/phase/outcome to envelope, each evidence row to a ref, each capture/report to artifact. Preserve `event_seq`, tick, and native phase. | No schema version, correlation/parent ID, evidence classification/hash, artifact IDs, or correction links. Documentation still contains retired URL history and hard-coded mission assumptions. |
| World Intake | Immutable source bytes; `GET /proposals`; authenticated `POST /adjudications` | Assertions, conflicts, adjudications, compiled command, FleetCore canon receipt, corrections in SQLite | Human review authorizes submission; FleetCore alone mutates canon | Evidence producer, review system, command proposer | Map source/assertion/conflict to evidence; adjudication and compiled command to review artifacts; FleetCore receipt to verified-state evidence. Native IDs are retained as `data.native_ids`. | No mission/correlation ID, shared classifications, artifact wrapper, or generalized review type outside canon intake. |
| Legend Pipeline | Completed mission JSON path; candidate JSON from an external provider | Hashed evidence bundle, deterministic fact, generation request, validated candidate JSON | Validation only; cannot approve or publish lore | Evidence and artifact producer | Mostly direct mapping: source hash/facts to evidence refs; fact rendering and lore candidate to separate artifacts. CLI wrapper supplies mission envelope and stable artifact IDs. | Current `request_id` is not the shared mission ID; no timestamps, provider receipt, human review result, or durable output path. |
| img2asset | CLI image/GLB path or `POST /generate` multipart upload | GLB under `web/assets/models/`; entry in `manifest.json`; HTTP entry response | Writes public assets/manifest, but no world/canon authority | Artifact producer | Wrap one generation/catalog operation; hash source and GLB; emit asset artifact referencing existing manifest entry/path and backend. | No mission/correlation ID, source hash, artifact ID, review status, provider/model version, or failure receipt in manifest. |
| Agent Ops | FleetCore WebSocket; `GET /captain-memory-api/captains/summary`; operator captain controls | Visible captain state, decisions, memory, Fact/Fleet Lore; sends bounded control commands | Projection plus explicit operator controls | Evidence/artifact projection and review surface candidate | Add read-only Mission Record projection endpoint/client. Render shared classifications and review-needed artifacts; keep existing FleetCore control path separate. | No Mission Record input, mission selection, artifact links/status, provenance drill-down, or shared review actions. |
| Bridge | Browser `localStorage[monad.fleetMotion.state]`; embedded instruments; some instruments independently connect to FleetCore | Composite UI and selection state; no shared backend output | Projection; selection-only browser state in classic Bridge | Projection | Read-only mission-summary card consuming a projection JSON. It links to evidence/artifacts but never becomes their store. | No mission envelope/status source, evidence classification UI, artifact/review indicators, or durable output. |
| Radio Console | FleetCore WebSocket; `/data/npr-headlines.json`; browser speech synthesis | Audible/visible narration and transcript in page memory | Projection only; no FleetCore mutation | Projection | Consume a small `radio-eligible` projection of accepted mission artifacts/events. Map only exceptional, already-classified items to speech; never speak generated candidates or lore as Fleet traffic. | No mission/correlation ID, durable transcript, artifact link, classification gate, or common rate/eligibility contract. |

## Required adapter interfaces

These are conceptual callable boundaries; GLUE-04 chooses process topology.

```text
FleetCoreReader.observe(envelope, cursor) -> EvidenceRef[] + next_cursor
CognitionExport.export(envelope, browser_run) -> ArtifactResult[]
LivingFleetCycle.wrap(envelope, cycle_receipt) -> ArtifactResult + EvidenceRef[]
MissionDirectorImport.import(mission_json) -> MissionEnvelope + EvidenceRef[] + ArtifactResult[]
WorldIntakeBridge.wrap(envelope, native_ids) -> EvidenceRef[] + ArtifactResult[]
LegendWrap.prepare/validate(envelope, files) -> EvidenceRef[] + ArtifactResult[]
AssetWrap.catalog(envelope, manifest_entry) -> ArtifactResult
Projection.read(mission_id, audience) -> non-authoritative view JSON
```

All write-capable native calls remain behind their existing boundaries. There
is deliberately no generic `adapter.execute_command()`.

## Identifier mapping

| Native identifier | Shared mapping |
|---|---|
| FleetCore `event_seq` / canon event sequence | `EvidenceRef.source_id`; never replace it with array index or tick. |
| Mission Director `mission_id` | `MissionEnvelope.mission_id` with `mission.` prefix normalized once by importer. |
| World Intake source/assertion/adjudication/command IDs | Preserve each as native source IDs; artifact IDs identify the wrapper record, not the native row. |
| Living Fleet `decision_id` | Native receipt under artifact `data`; resulting FleetCore decision event is separate evidence. |
| Legend `request_id` | Correlation ID; mission ID comes from the source mission/envelope. |
| Asset manifest `name` | Native source ID; artifact ID is stable and revision-aware. |
| Cognition Graph browser run | New correlation ID required at run start; node IDs combine run ID and role. |

## Authority hazards adapters must block

1. A Cognition verdict, captain provider output, or legend candidate cannot be
   reclassified as `verified-state`.
2. A World Intake approval is not evidence that FleetCore accepted a command;
   only the FleetCore receipt/event supplies that evidence.
3. Mission Director derived states must cite the underlying positions/events
   and remain `observation` unless directly sourced from FleetCore.
4. Agent Ops, Bridge, and Radio are projections. UI state or speech never
   becomes a Mission Record event by implication.
5. Asset existence proves a file was produced, not that it was reviewed,
   correctly scaled, or accepted for a mission.
6. Retained FleetCore arrays require stable sequence cursors; adapters must not
   use length as durable progress.

## Recommended implementation slices

1. Implement `MissionDirectorImport` first: its JSON is durable, bounded, and
   already contains a complete mission/evidence/report path.
2. Implement `FleetCoreReader` next with read-only snapshot/event selection.
3. Wrap Legend Pipeline, which already hashes evidence and separates fact/lore.
4. Add World Intake bridge after GLUE-05 fixes the generalized review shape.
5. Add Cognition export and Living Fleet cycle receipts once Mission Record can
   persist generated/provider metadata.
6. Add Agent Ops as the first projection; Bridge and Radio consume smaller
   audience projections later.
7. Wrap img2asset only when a pilot mission actually requests an asset.

## Finding

The components do not need a universal transport. They need stable envelope,
evidence, and artifact records around their existing transports. The first
healthy vertical slice is therefore Mission Director import → Mission Record →
Agent Ops projection, with FleetCore references left authoritative in place.
