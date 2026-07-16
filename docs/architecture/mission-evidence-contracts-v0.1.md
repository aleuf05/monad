# Shared Mission and Evidence Contracts V0.1

Status: reviewed design target for GLUE-01. This document defines interchange
shapes only; it does not create a runtime, database, authority, or second world
state.

## Purpose and boundary

Monad's components already exchange questions, snapshots, decisions, reports,
review records, and generated artifacts, but they do not share identifiers or
provenance vocabulary. These three envelopes provide that connective tissue:

- `MissionEnvelope` identifies the bounded inquiry or operation.
- `EvidenceRef` cites material used without copying or reclassifying it.
- `ArtifactResult` records one component output and whether review is required.

FleetCore remains the only owner of operational world truth. World Intake
remains the adjudication path for canon changes. These envelopes describe and
reference; possession of one never grants command authority.

## Common conventions

- JSON field names are `snake_case`; timestamps are UTC RFC 3339.
- IDs are opaque, stable strings: `<kind>.<namespace>.<local-id>`. Consumers
  compare IDs, never parse them for authority or behavior.
- Required fields must be present. Optional fields use `null`; absence must not
  silently imply a default classification, authority, or approval.
- `schema_version` is `monad.mission.v0.1`, `monad.evidence.v0.1`, or
  `monad.artifact.v0.1`. Additive fields are compatible within v0.1; removing a
  field or changing its meaning requires a new version.
- Payloads may contain component-specific data under `data`; shared fields must
  not be duplicated there with different meanings.

## MissionEnvelope

```json
{
  "schema_version": "monad.mission.v0.1",
  "mission_id": "mission.kraken-inquiry-001",
  "correlation_id": "run.kraken-inquiry-001.20260716T172300Z",
  "parent_mission_id": null,
  "kind": "inquiry",
  "objective": "Assess what the evidence justifies about contact K-1.",
  "requested_by": {"id": "lieutenant.cgl", "authority": "human-command"},
  "status": "created",
  "created_at": "2026-07-16T17:23:00Z",
  "updated_at": "2026-07-16T17:23:00Z",
  "input_refs": [],
  "constraints": ["Do not classify an unknown contact as hostile without evidence."],
  "data": {}
}
```

Required: every field shown except `parent_mission_id`, which may be `null`.

`kind` is one of `inquiry`, `operation`, `review`, `generation`, or
`verification`. It describes work shape, not authority.

`status` is one of:

```text
created -> running -> review-required -> running -> completed
                    \-> rejected
created/running/review-required -> cancelled
running -> blocked -> running
running -> failed
```

Only an explicit lifecycle event may change status. `blocked` means a named
external input is required; `failed` means the attempted execution terminated.
Neither means rejected. Terminal states are `completed`, `rejected`,
`cancelled`, and `failed`. Corrections never mutate a terminal envelope; they
create a child mission with `parent_mission_id` pointing to it.

`requested_by.authority` is one of `human-command`, `operator`, `component`, or
`unknown`. It records origin only. A coordinator must still use the target
component's existing authority checks.

## EvidenceRef

```json
{
  "schema_version": "monad.evidence.v0.1",
  "evidence_id": "evidence.fleetcore.vessel-event-728208",
  "source_system": "fleetcore",
  "source_id": "vessel-event.728208",
  "locator": {"kind": "api", "value": "/fleetcore-ws/snapshot#vessel_events[event_seq=728208]"},
  "content_sha256": null,
  "observed_at": "2026-07-16T17:20:00Z",
  "recorded_at": "2026-07-16T17:23:01Z",
  "classification": "verified-state",
  "claim": "Scout Charlie completed its route.",
  "producer": "fleetcore-reader",
  "supersedes_evidence_id": null
}
```

Required fields: all shown. `content_sha256` may be `null` only when the source
has its own stable event identity; immutable files and model outputs require a
SHA-256. `claim` states what the consumer says the reference supports. The
reference does not make that claim true merely by existing.

Classifications:

| Classification | Meaning |
|---|---|
| `verified-state` | Direct authoritative system state or event. |
| `observation` | Reproducible measurement or direct inspection. |
| `testimony` | Attributed statement or recollection. |
| `interpretation` | Explanation applied to evidence. |
| `hypothesis` | Provisional, challengeable account. |
| `generated-candidate` | Machine-produced proposal awaiting judgment. |
| `fleet-lore` | Cultural mythology explicitly not operational truth. |
| `command-finding` | Governing human determination, not empirical observation. |

`locator.kind` is `api`, `file`, `event`, `url`, or `record`. Locators point to
the source of truth; Mission Record implementations must not copy full
FleetCore snapshots merely to make evidence convenient.

Corrections append a new `EvidenceRef` with `supersedes_evidence_id`. The old
reference remains addressable. A correction may change a claim or
classification, never rewrite the cited source.

## ArtifactResult

```json
{
  "schema_version": "monad.artifact.v0.1",
  "artifact_id": "artifact.cognition.kraken-inquiry-001.verdict-01",
  "mission_id": "mission.kraken-inquiry-001",
  "correlation_id": "run.kraken-inquiry-001.20260716T172300Z",
  "component": "cognition-graph",
  "artifact_type": "recommendation-candidate",
  "status": "candidate-ready",
  "created_at": "2026-07-16T17:23:20Z",
  "input_refs": ["evidence.fleetcore.vessel-event-728208"],
  "evidence_refs": [],
  "requires_review": true,
  "review_authority": "human-command",
  "supersedes_artifact_id": null,
  "data": {"verdict": "INCONCLUSIVE", "recommendation": "Continue passive observation."}
}
```

Required fields: all shown. Artifact status is one of `candidate-ready`,
`validated`, `review-required`, `accepted`, `rejected`, `superseded`, or
`failed`. `validated` means structural/domain checks passed, not human
acceptance. Only a review result may set `accepted` or `rejected` when
`requires_review` is true.

An artifact may cite evidence and may itself later be cited by an EvidenceRef
classified as `generated-candidate`, `interpretation`, or `fleet-lore`. It may
not cite itself. Revisions create a new artifact whose
`supersedes_artifact_id` names the prior version.

## Component mappings

| Component | Existing shape | Contract mapping | Authority preserved |
|---|---|---|---|
| Mission Director | `mission_id`, phase, evidence array, outcome, captures | Its mission becomes an `operation` envelope; each phase transition/capture is an `EvidenceRef`; published report is an artifact. | Director still issues only its two bounded FleetCore commands. |
| World Intake | source/assertion/adjudication/command/canon-event IDs | Source and assertion become evidence; review/compiled command become artifacts; accepted FleetCore event is a new verified-state reference. | Approval still does not mutate canon; FleetCore decides. |
| Living Fleet | snapshot input, provider decision, intent, durable `agent_decisions` | Decision cycle is an artifact citing snapshot/event evidence; accepted/rejected FleetCore result is separate evidence. | Captain assignment and FleetCore validation remain governing. |
| Cognition Graph | question, framing, role results, verifier verdict | Question is an `inquiry` envelope; node outputs and verdict are generated-candidate artifacts with provider/mode in `data`. | Simulated/live mode remains explicit; verdict has no command authority. |
| Legend Pipeline | request ID, source hash, verified facts, candidate, validation | Existing bundle maps directly to evidence refs; fact rendering and lore candidate are separate artifacts. | `fleet-lore` never becomes verified-state; validation is not approval. |

## Complete mapping examples

### Operation QUacken legend preparation

```json
{
  "mission": {
    "schema_version": "monad.mission.v0.1",
    "mission_id": "mission.quacken-transit-002",
    "correlation_id": "run.quacken-legend.001",
    "parent_mission_id": null,
    "kind": "generation",
    "objective": "Prepare a fleet-lore candidate from the completed mission.",
    "requested_by": {"id": "lieutenant.cgl", "authority": "human-command"},
    "status": "running",
    "created_at": "2026-07-16T17:23:00Z",
    "updated_at": "2026-07-16T17:23:00Z",
    "input_refs": ["evidence.mission.quacken-transit-002"],
    "constraints": ["Fact and mythology remain separate."],
    "data": {}
  },
  "evidence": {
    "schema_version": "monad.evidence.v0.1",
    "evidence_id": "evidence.mission.quacken-transit-002",
    "source_system": "mission-director",
    "source_id": "mission.quacken-transit-002",
    "locator": {"kind": "file", "value": "web/missions/quacken-transit-002/mission.json"},
    "content_sha256": "1f6332e95c5b0b2eb957a3a8bf35691d616b23666e43d218faa6b4e1a78ce871",
    "observed_at": "2026-07-11T07:11:28Z",
    "recorded_at": "2026-07-16T17:23:01Z",
    "classification": "verified-state",
    "claim": "The rendezvous hold completed after 31 continuous seconds; outcome success.",
    "producer": "legend-pipeline",
    "supersedes_evidence_id": null
  }
}
```

The generated mythology is a separate `ArtifactResult` with
`artifact_type: fleet-lore-candidate`, `status: validated`,
`requires_review: true`, and the mission evidence ID in `input_refs`.

### Cognition Graph inquiry

The input question creates an `inquiry` mission. Framer output and each of four
formulations are separate `generated-candidate` artifacts. The verifier result
is a `recommendation-candidate`, not verified evidence. `data.mode` must be
`simulated` or `live`, and live output records provider/model identifiers. A
human decision becomes another artifact rather than overwriting the verdict.

## Validation rules for later implementation

1. Reject unknown schema versions, classifications, lifecycle states, and
   artifact statuses.
2. Reject missing required fields, naive timestamps, blank IDs, and duplicate
   IDs with unequal content.
3. Reject an ArtifactResult whose mission/correlation IDs do not match its
   envelope.
4. Reject `accepted`/`rejected` artifacts without a review artifact when review
   is required.
5. Reject `verified-state` evidence sourced only from a generated artifact.
6. Reject `fleet-lore` or `interpretation` as a FleetCore command premise unless
   separately supported by verified-state evidence and explicitly adjudicated.
7. Preserve unknown additive `data` fields during read/write round trips.

## Decisions deferred to dependent tasks

- GLUE-02 chooses Mission Record storage and append-event format.
- GLUE-03 defines each adapter's executable boundary.
- GLUE-04 defines who may emit lifecycle transitions.
- GLUE-05 defines review artifact details and human identity proof.
- GLUE-06 defines artifact locators and projections.

Those tasks may add fields under new schema versions; they must not weaken the
truth/interpretation/lore separation or grant authority through an envelope.
