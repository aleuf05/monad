# Mission Record V0.1

Status: reviewed design target for GLUE-02. This document specifies storage,
event schema, restart behavior, correction handling, indexing, and boundaries
against FleetCore. It does not implement a database or service — per GLUE-02's
own exclusion, and per the Architecture Engine's own gates, prototype code may
follow to test disputed assumptions, but it is not architecture of record
until it passes through this design.

## Purpose and boundary

The Mission Record is the single durable, append-only log of everything that
happens to a `MissionEnvelope` (`docs/architecture/mission-evidence-contracts-v0.1.md`,
GLUE-01) over its life: lifecycle transitions, evidence citations, artifact
results, and corrections. It is a citation ledger, not a data warehouse:

- It is authoritative for *what the Mission Bus recorded happening to a
  mission* — not for FleetCore world state, not for any component's own
  data. FleetCore remains the only owner of operational world truth
  (unchanged from GLUE-01).
- Every `EvidenceRef` it stores is a locator back to its source system
  (`fleetcore`, `world-intake`, `mission-director`, etc.), never a copied
  snapshot. GLUE-01's rule stands: "Mission Record implementations must not
  copy full FleetCore snapshots merely to make evidence convenient."
- One instance, one file, per this project's standing "one source of truth
  per concern" invariant (`LS-01`, `docs/reports/2026-07-15-inadequate-specs.md`).
  No replica, no standby, no second copy — same posture as every other store
  in this repo.

## Storage choice

**SQLite, WAL mode, one file: `data/mission-record/mission-record.sqlite3`.**

Not a new technology introduced for this component — it is what World Intake
(`tools/world-intake/world_intake.py`) and Living Fleet's memory subsystem
(`tools/living-fleet/memory/store.py`) already use for exactly this shape of
problem: an ordered, append-mostly log with cheap point lookups, running
locally, no separate server process to operate. Matches this repo's
demonstrated preference (Architecture Engine invariant: "simplicity shall be
treated as an engineering asset") over introducing a message broker or a
second database technology for one more append log.

Immutability is enforced the same way World Intake enforces it on its
`sources` table — triggers, not application discipline alone:

```sql
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE mission_events (
  event_id      TEXT PRIMARY KEY,   -- "missionevent.<mission_id>.<seq>"
  mission_id    TEXT NOT NULL,
  correlation_id TEXT NOT NULL,
  seq           INTEGER NOT NULL,   -- assigned by the record, monotonic per mission_id, gapless
  event_type    TEXT NOT NULL,      -- see Event types below
  schema_version TEXT NOT NULL,     -- the GLUE-01 schema_version of payload_json's envelope/evidence/artifact
  payload_json  TEXT NOT NULL,      -- the full MissionEnvelope / EvidenceRef / ArtifactResult, verbatim
  recorded_at   TEXT NOT NULL,      -- UTC RFC3339, server-assigned -- never trusts a caller-supplied timestamp for ordering
  UNIQUE(mission_id, seq)
);

CREATE INDEX idx_mission_events_mission ON mission_events(mission_id, seq);
CREATE INDEX idx_mission_events_correlation ON mission_events(correlation_id);
CREATE INDEX idx_mission_events_type_time ON mission_events(event_type, recorded_at);

CREATE TRIGGER mission_events_immutable_update BEFORE UPDATE ON mission_events
BEGIN SELECT RAISE(ABORT, 'mission_events are immutable'); END;
CREATE TRIGGER mission_events_immutable_delete BEFORE DELETE ON mission_events
BEGIN SELECT RAISE(ABORT, 'mission_events are immutable'); END;
```

`seq` is assigned by the Mission Record itself, not supplied by the caller —
same reasoning as FleetCore's `next_vessel_event_seq` (`fleetcore/src/world.rs`):
letting the record be the sole authority for ordering avoids races between
concurrent writers guessing at the next number.

## Event types

`event_type` is one of:

| Type | Payload | Meaning |
|---|---|---|
| `mission_created` | `MissionEnvelope` | First event for a `mission_id`. Establishes `kind`, `objective`, `requested_by`. |
| `status_changed` | `MissionEnvelope` | A lifecycle transition per GLUE-01's state diagram. `payload_json.status` is the new status. |
| `evidence_cited` | `EvidenceRef` | A reference was attached to this mission's evidence trail. |
| `artifact_recorded` | `ArtifactResult` | A component produced or updated an artifact under this mission. |
| `corrected` | `EvidenceRef` or `ArtifactResult` | A correction — see below. Always carries a non-null `supersedes_evidence_id` or `supersedes_artifact_id` in its payload. |

This list is closed for V0.1. A new event type is a new schema version, same
rule GLUE-01 sets for its own three schemas.

## Restart behavior

The Mission Record has no separate "current state" table that could drift
from the log — the exact bug class GitHub issue #6 fixed for FleetCore's
`vessel_events` (`docs/architecture/vessel-events-retention-investigation.md`).
Instead:

- **Current mission status** is always the payload of the highest-`seq`
  `status_changed` (or `mission_created`, if none) event for that
  `mission_id`. A reader computes this with one indexed query
  (`ORDER BY seq DESC LIMIT 1`); nothing is precomputed or cached
  server-side that could fall out of sync with the log.
- **Restart requires no replay step at all.** Unlike FleetCore (which
  rebuilds in-memory `World` state from a checkpoint + event tail because
  its simulation runs continuously in memory), the Mission Record's only
  "state" is the SQLite file itself — a process restart just reopens the
  same file. There is nothing to reconstruct.
- A **read-side projection** (e.g. Agent Ops' "recent missions" view, GLUE-06)
  may still maintain its own derived cache for display performance. That
  cache is explicitly not the Mission Record — same "derived,
  replay-reconstructible convenience view, not an independent source of
  history" language `vessel_events` itself already uses for its own relationship
  to `events.jsonl`.

## Correction handling

Per GLUE-01: *"Corrections never mutate a terminal envelope; they create a
child mission... A correction may change a claim or classification, never
rewrite the cited source."* The Mission Record enforces this structurally,
not just by convention:

- The `mission_events_immutable_*` triggers make rewriting any row a hard
  SQLite error, not a discipline someone could forget.
- A correction to an `EvidenceRef` or `ArtifactResult` is a new
  `corrected` event whose payload's `supersedes_evidence_id` /
  `supersedes_artifact_id` names the row being superseded. The old row is
  untouched and remains addressable — a reader who already cited it keeps
  a valid reference; a reader querying fresh sees the correction on top.
- A correction to a mission's *outcome* after it reached a terminal status
  is not a `status_changed` event on the terminal mission (the triggers
  would still permit appending one, since terminal-ness is an application
  rule not a schema rule — see Validation rules below) — it is a new
  `mission_created` event for a **child mission**, `parent_mission_id`
  pointing at the original, matching GLUE-01's rule exactly. Application-layer
  validation, not the schema, is what rejects a `status_changed` event that
  would try to move a terminal mission back to `running`.

## Indexing needs

Three access patterns drove the indexes above, each mapped to a concrete
consumer:

1. **"Show me everything that happened to mission X, in order"** —
   `idx_mission_events_mission (mission_id, seq)`. The primary read path:
   Agent Ops mission detail view, Cognition Graph replaying its own inquiry.
2. **"Show me everything under this run"** —
   `idx_mission_events_correlation (correlation_id)`. Cross-component tracing
   when one mission spans multiple component calls in one execution
   (GLUE-01's `correlation_id` field exists specifically for this).
3. **"Show me recent artifacts needing review"** /
   **"show me missions with no activity in N minutes"** —
   `idx_mission_events_type_time (event_type, recorded_at)`. Feeds GLUE-05's
   review inbox and staleness detection (see Failure modes below).

No full-text or vector index in V0.1 — nothing in GLUE-01's schemas requires
one, and adding one before a real consumer needs it would be exactly the kind
of premature infrastructure the Architecture Engine's invariants warn against.

## Boundaries against FleetCore

- The Mission Record never becomes a second source of truth for FleetCore
  world state. Every `EvidenceRef.locator` pointing at FleetCore is a
  pointer (`{"kind": "api", "value": "/fleetcore-ws/snapshot#vessel_events[event_seq=728208]"}`,
  per GLUE-01's own example) — never a copied field value.
- The Mission Record has **no write path into FleetCore, ever.** It is
  purely descriptive. Nothing in this design grants it command authority;
  GLUE-04's Coordinator (not this record) is the only thing that may ever
  issue a FleetCore command, and even then only through FleetCore's own
  existing authority checks — unchanged from GLUE-01's boundary statement.
- If FleetCore's cited event is later trimmed from `vessel_events`'
  bounded retention window (`fleetcore/src/world.rs`,
  `default_vessel_event_retention`), the `EvidenceRef` does not become
  invalid — `event_sequence`/`event_seq`-based locators remain meaningful
  citations of what was true even after the live retained window moves on,
  because the full history remains durable in FleetCore's own
  `events.jsonl`, never in a Mission Record copy.

## Failure modes

| Failure | Handling |
|---|---|
| Process crash mid-write | A single `INSERT` is one SQLite transaction; a crash before commit means the event simply never happened. No partial row is possible. Caller retries with the same `event_id`. |
| Duplicate submission (retry after a timeout, not knowing if the first attempt landed) | `event_id` is deterministic (`missionevent.<mission_id>.<seq>`), and inserts use `INSERT OR IGNORE` — same idempotency pattern World Intake's `sources`/`assertions`/`adjudications` tables already use. A retried duplicate is a silent no-op, not a duplicate row. |
| Concurrent writers race for the next `seq` | The insert that assigns `seq` computes `MAX(seq)+1` for that `mission_id` and inserts inside one transaction; a losing concurrent writer hits the `UNIQUE(mission_id, seq)` constraint and must recompute and retry — same shape as any optimistic-append pattern, no distributed lock needed for a single-file SQLite store. |
| A mission goes stale (`running`/`blocked` with no new event for a long time) | Not silently hidden. `idx_mission_events_type_time` makes "missions with no `status_changed`/`evidence_cited`/`artifact_recorded` event in N minutes" a cheap query. Whether and how to *act* on staleness (timeout, escalation) is explicitly GLUE-04's Coordinator lifecycle design, not this record's job — the record only makes the staleness visible on request. |
| Two components both believe they can emit the mission's next lifecycle event | Out of scope for the record itself (which will happily append whatever a caller legitimately submits); GLUE-04 defines who may emit which transitions. The record's only enforcement is structural (append-only, correct `seq`), not authorization. |
| Store file corruption / disk failure | Out of scope for V0.1, matching this project's `LS-01` ruling: no replication or backup daemon as default hygiene. If a stated recovery requirement appears later, it is evaluated then, same as every other store in this repo. |

## Complete example: one Cognition Graph inquiry, replayed

```json
[
  {"seq": 1, "event_type": "mission_created", "payload_json": {"mission_id": "mission.kraken-inquiry-001", "kind": "inquiry", "status": "created", "objective": "Assess what the evidence justifies about contact K-1.", "...": "..."}},
  {"seq": 2, "event_type": "status_changed", "payload_json": {"mission_id": "mission.kraken-inquiry-001", "status": "running", "...": "..."}},
  {"seq": 3, "event_type": "evidence_cited", "payload_json": {"evidence_id": "evidence.fleetcore.vessel-event-728208", "classification": "verified-state", "claim": "Contact K-1 last observed at bearing 214, range 6nm.", "...": "..."}},
  {"seq": 4, "event_type": "artifact_recorded", "payload_json": {"artifact_id": "artifact.cognition.kraken-inquiry-001.formulation-01", "artifact_type": "generated-candidate", "status": "candidate-ready", "...": "..."}},
  {"seq": 5, "event_type": "artifact_recorded", "payload_json": {"artifact_id": "artifact.cognition.kraken-inquiry-001.verdict-01", "artifact_type": "recommendation-candidate", "status": "review-required", "requires_review": true, "...": "..."}},
  {"seq": 6, "event_type": "status_changed", "payload_json": {"mission_id": "mission.kraken-inquiry-001", "status": "review-required", "...": "..."}},
  {"seq": 7, "event_type": "artifact_recorded", "payload_json": {"artifact_id": "artifact.review.kraken-inquiry-001.decision-01", "artifact_type": "review-decision", "status": "accepted", "input_refs": ["artifact.cognition.kraken-inquiry-001.verdict-01"], "...": "..."}},
  {"seq": 8, "event_type": "status_changed", "payload_json": {"mission_id": "mission.kraken-inquiry-001", "status": "completed", "...": "..."}}
]
```

Current status after replay: `completed` (seq 8, the highest `status_changed`).
Full provenance chain: two artifacts, one evidence citation, one human
review decision — every one independently addressable and citable by ID,
none of it copied out of FleetCore.

## Validation rules for later implementation

1. Reject any event whose `payload_json` does not itself pass GLUE-01's
   validation rules for its own schema.
2. Reject a `status_changed` event that would move a mission from a
   terminal status (`completed`/`rejected`/`cancelled`/`failed`) to any
   other status — corrections create a child mission instead (see above).
3. Reject an event whose `seq` does not equal `MAX(seq)+1` for that
   `mission_id` at insert time (enforced by the transaction pattern above,
   not merely checked after the fact).
4. Reject `corrected` events with a null `supersedes_evidence_id` and
   `supersedes_artifact_id` (exactly one must be set).
5. Reject a `mission_created` event for a `mission_id` that already has
   events (a mission is created exactly once).
6. Preserve `payload_json` byte-for-byte on read — the Mission Record is a
   citation ledger; it must never normalize, reformat, or reinterpret a
   payload it stores.

## Decisions deferred to dependent tasks

- GLUE-03 defines each component adapter's exact call shape into this
  record (direct library call vs. an API boundary; this document assumes
  either is possible against the same schema).
- GLUE-04 defines who may emit which lifecycle transitions and how
  staleness/timeout is acted on.
- GLUE-05 defines the review artifact's exact shape and human-identity
  proof for `artifact_recorded` events of type `review-decision`.
- GLUE-06 defines how artifact locators surface into projections (Agent
  Ops, Bridge, Radio) without the record itself becoming a rendering layer.

Those tasks may add fields under new schema versions; they must not weaken
append-only immutability, the no-FleetCore-copy boundary, or the
evidence/artifact correction discipline this document enforces structurally
via the SQLite triggers above.
