# Artifact Registry and Projections V0.1

Status: GLUE-06 design. The registry is a rebuildable index of artifact
references from the append-only Mission Record. It is not another source of
truth and does not relocate, mirror, or own artifact bytes.

## Registry entry

```json
{
  "schema_version": "monad.registry.v0.1",
  "artifact_id": "artifact.legend.quacken-transit-002.v1",
  "mission_id": "mission.quacken-transit-002",
  "artifact_type": "fleet-lore",
  "status": "accepted",
  "classification": "fleet-lore",
  "title": "The Legend of Operation QUACKEN",
  "locator": {"kind": "url", "value": "/archive/missions/quacken-transit-002/LEGEND.txt"},
  "content_sha256": "required-for-file-artifacts",
  "media_type": "text/plain",
  "component": "legend-pipeline",
  "created_at": "2026-07-16T17:40:00Z",
  "accepted_at": "2026-07-16T17:40:00Z",
  "evidence_refs": ["evidence.mission.quacken-transit-002"],
  "supersedes_artifact_id": null,
  "visibility": "public"
}
```

Required fields are all shown; `accepted_at` may be null. File/URL artifacts
require a content hash. API/record locators may use null only when the source
has a stable immutable native ID.

## Storage and rebuild

Canonical artifact facts remain `ArtifactResult` and review events in the
Mission Record. The registry is generated to:

```text
web/data/mission-artifacts.json
```

because all initial consumers are static public instruments. It contains only
entries whose `visibility` is `public`. An operator-only projection may later
be served from a loopback API; private records must never be copied into `web/`.

Rebuild folds Mission Record events, selects the newest unsuperseded artifact
revision, joins accepted review decisions, verifies each locator/hash, writes a
temporary file, then atomically renames it. Missing files remain listed with
`status: unavailable` and a build warning; they are not silently dropped.

The registry never scans directories to invent ownership. Files enter only
through recorded artifact events. Deleting the registry and rebuilding it must
produce byte-identical JSON for the same Mission Record and artifact bytes.

## Existing artifact mappings

| Existing output | Registry type / locator | Ownership remains |
|---|---|---|
| Mission report `index.html`, `mission.json`, `log.md` | `mission-report`, URL/file | Mission Director/archive |
| `LEGEND.txt` / narrative memory | `fleet-lore`, URL or record | Legend pipeline / Living Fleet memory |
| GLB and manifest entry | `model-3d`, `/assets/models/<name>.glb` | img2asset manifest |
| Source/generated image | `image`, URL/file | producing tool/repository path |
| Cognition node/verdict JSON | `model-output`, Mission Record locator | Cognition Graph artifact event |
| Screenshot/capture | `capture`, URL/file | Mission Director capture attachment |
| Chronicle proposal/entry | `chronicle-proposal` / `chronicle-entry`, file | Chronicle/report record |

## Audience projections

Projection builders filter registry + Mission Record; clients never implement
authority rules independently.

### Agent Ops

- Shows active/recent missions, lifecycle, latest accepted/review-required
  artifacts, evidence classifications, and direct provenance links.
- Fact and Fleet Lore render side by side only when both are explicitly linked.
- Provides review links/cards from GLUE-05; existing captain controls remain a
  separate FleetCore command surface.
- First pilot output: `web/data/mission-ops.json`.

### Bridge

- Shows current mission objective/status, last verified operational evidence,
  and count of human actions required.
- Links outward to Agent Ops/detail; does not render full model output or lore
  on the operational status rail.
- Never derives active mission from the newest directory or filename.

### Radio

- Receives only entries explicitly projected with `radio_eligible: true`.
- Eligible: accepted operational milestone, exceptional verified-state event,
  or operator-requested accepted briefing.
- Ineligible: pending/rejected/generated candidates, hypotheses, fleet lore,
  assets, and routine component activity.
- Projection supplies channel, priority, expiry, and dedupe key so Radio does
  not reinterpret registry entries or recreate scout spam.

### World Intake / Review Inbox

- Shows `review-required` artifacts with immutable evidence/artifact links and
  current revision.
- Does not consume public registry JSON for adjudication; server-side projection
  reads Mission Record directly to prevent stale public data authorizing work.

### Chronicle

- Accepts only reviewed `chronicle-proposal` artifacts.
- Export appends a cited entry; Chronicle remains a narrative view over reports
  and evidence, not a registry or Mission Record replica.
- Superseded proposals remain discoverable but are never re-exported.

### Reports

- Verification reports cite stable artifact/evidence IDs plus locators/hashes.
- Report generation may list unavailable/superseded artifacts but must label
  them; it never repairs or rewrites source material.

## Projection envelope

Every generated audience file contains:

```json
{
  "schema_version": "monad.projection.v0.1",
  "audience": "agent-ops",
  "generated_at": "2026-07-16T18:02:00Z",
  "source_record_cursor": 42,
  "missions": [],
  "artifacts": []
}
```

`source_record_cursor` permits visible staleness detection. A projection may be
behind the Mission Record; it must never claim freshness without exposing its
cursor/time.

## Failure and privacy rules

1. Hash mismatch marks `integrity-failed`; no consumer embeds/plays the artifact.
2. Missing locator marks `unavailable`; provenance remains visible.
3. Unknown classification/status fails the build closed.
4. `visibility != public` is never written under `web/`.
5. A review decision in a stale public projection cannot authorize anything.
6. Projection failure does not change mission/artifact state; UI shows degraded
   and last successful generation time.
7. A file moved intentionally requires a new artifact revision/locator; the
   registry does not search for a likely replacement.

## Pilot build boundary

GLUE-07 should implement only Mission Director archive import, Mission Record
append, registry build, and Agent Ops projection for one Kraken inquiry. Bridge,
Radio, generalized review UI, Chronicle export, and asset registration remain
design-complete but outside the first implementation packet.
