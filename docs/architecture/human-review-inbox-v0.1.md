# Human Review Inbox V0.1

Status: GLUE-05 design. This generalizes World Intake's proven review-card
pattern without generalizing its canon-writing authority.

## ReviewCard

```json
{
  "schema_version": "monad.review.v0.1",
  "review_id": "review.kraken-inquiry-001.recommendation-01",
  "mission_id": "mission.kraken-inquiry-001",
  "artifact_id": "artifact.cognition.kraken-inquiry-001.verdict-01",
  "artifact_type": "recommendation-candidate",
  "revision": 1,
  "status": "pending",
  "requested_action": "accept-recommendation",
  "required_authority": "human-command",
  "evidence_refs": ["evidence.fleetcore.contact-k1.001"],
  "conflicts": [],
  "summary": "Continue passive tracking; evidence does not justify hostility.",
  "proposed_data": {},
  "created_at": "2026-07-16T17:56:00Z",
  "supersedes_review_id": null
}
```

Required fields are all shown. A card references an immutable artifact and
evidence; it does not duplicate them. `revision` protects against stale browser
decisions.

## States and actions

```text
pending -> accepted | rejected | deferred | superseded
pending --edit--> superseded + new pending card/artifact revision
pending --regenerate--> superseded + new pending generated candidate
deferred --reopen--> new pending card (old card remains deferred)
```

Actions:

- `accept`: records that the named authority accepts this artifact for its
  stated purpose. It does not imply downstream execution succeeded.
- `reject`: records a terminal negative judgment with reason.
- `defer`: records missing timing/context, not rejection.
- `edit`: creates a new artifact revision and review card; never changes the
  reviewed artifact in place.
- `regenerate`: requests a new generated artifact with a new correlation ID;
  the prior candidate remains visible.

No bulk acceptance in V0.1. No timeout action. Review age never changes status.

## Authority by artifact class

| Artifact | Accept means | Required authority | Downstream effect |
|---|---|---|---|
| Cognition recommendation | Approved as an inquiry conclusion/recommendation | `human-command` | Mission may complete; no FleetCore command. |
| FleetCore command proposal | Approved for submission through its named bounded adapter | `human-command` or component-specific operator | Adapter submits; FleetCore receipt separately records accept/reject. |
| Legend candidate | Accepted as `fleet-lore`, never verified state | `human-command` | May enter narrative memory/public lore projection. |
| Chronicle proposal | Accepted for append to the witnessed Chronicle | `human-command` | Exporter appends/cites; reports remain governing truth. |
| Generated asset | Accepted for the named mission/use, not proof of scale/fitness | `operator` | Registry marks accepted; existing file remains where generated. |

The inbox authenticates reviewer identity but does not manufacture authority.
The action is rejected when the presented identity lacks the card's
`required_authority`.

## ReviewDecision

Every action appends an artifact and Mission Record event:

```json
{
  "decision_id": "decision.review.kraken-inquiry-001.01",
  "review_id": "review.kraken-inquiry-001.recommendation-01",
  "review_revision": 1,
  "action": "accept",
  "decided_by": {"id": "lieutenant.cgl", "authority": "human-command"},
  "reason": "Proportionate to the observed evidence.",
  "amended_data": null,
  "decided_at": "2026-07-16T18:00:00Z"
}
```

Server-side optimistic concurrency requires the submitted revision to equal the
current pending card. Replaying the same decision ID and content is idempotent;
different content under the same ID is rejected.

## Provenance visible on every card

The UI must show, without expanding developer tools:

- artifact type, component, status, and live/simulated/generated mode;
- source/evidence classification and direct locator;
- original question/request and component/provider/model identity;
- conflicts, unknowns, validation results, and prior revisions;
- exact downstream consequence of Accept;
- explicit warning when acceptance does not mutate FleetCore;
- reviewer authority required and current authentication state.

Fact, interpretation, generated candidate, and fleet lore use distinct labels
and styling. A card cannot render all sources as generic “evidence.”

## Mapping onto World Intake

World Intake remains the canon-specialized implementation:

| Current World Intake | Shared inbox |
|---|---|
| assertion/proposal card | `ReviewCard` |
| assertion ID | artifact/native source ID retained in `proposed_data` |
| approve | `accept` followed by existing compile/commit path |
| approve with edit | `edit`; new artifact/card revision before compilation |
| reject | `reject` |
| defer | `defer` |
| flavor only / mark unverified | domain-specific edit/classification actions |
| link existing | domain-specific edit resolving identity |
| Captain bearer token | reviewer authentication mechanism; shared service may reuse the pattern but not the token or canon scope |

Current endpoints can remain. A later shared inbox adds:

```text
GET  /mission-review-api/cards?status=pending&type=...
POST /mission-review-api/decisions
```

World Intake cards may be projected into that feed, but canon adjudication POSTs
continue to go to World Intake so its compiler, validation, and FleetCore receipt
chain remain intact.

## Failure rules

- Stale revision: HTTP 409, card remains pending.
- Missing/invalid reviewer authority: 401/403, no decision event.
- Missing evidence locator or artifact: card is invalid and not reviewable.
- Downstream submission rejection: accepted review remains accepted-for-submit;
  separate execution artifact records rejection.
- Regenerator/provider failure: prior card becomes superseded only after the new
  candidate is durably recorded; otherwise it stays pending.
- Correction: append a new card/decision chain; never delete prior judgment.
