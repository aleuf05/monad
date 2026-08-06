# Admiralty UI Data Contract

The first UI can consume static generated/curated data without parsing all
Markdown at render time.

## Current files

| File | Purpose | Required fields |
|---|---|---|
| `registry/documents.json` | Source inventory and provenance links | `id`, `title`, `source_path`, `document_type`, `domain`, `authority_status`, `lifecycle_status`, `content_sha256` |
| `registry/projects.json` | Executive project cards | `id`, `name`, `status`, `executive_summary`, `evidence_quality`, `last_reviewed` |
| `registry/decisions.json` | Decisions and pending judgment | `id`, `title`, `status`, `decision`, `authority`, `source_documents` |
| `registry/claims.json` | Normalized, sourced assertions | `id`, `claim`, `source_documents`, `confidence`, `authority_status`, `support` |
| `registry/relationships.json` | Cross-document/project links | `source`, `relationship`, `target`, `evidence` |
| `EXECUTIVE_BRIEF.md` | Human-readable first brief | — |
| `DECISION_QUEUE.md` | Human-readable pending queue | — |

## Envelope convention

Generated JSON includes `schema_version`, `generated_at`, and a top-level array
named after the resource. Source paths are repository-relative and should be
rendered as links only in the private UI. Status and confidence labels must be
visible; absent values remain `null` rather than invented.

## Example project object

```json
{
  "id": "project-fleetcore",
  "name": "FleetCore",
  "status": "implemented-prototype",
  "executive_summary": "Deterministic maritime world-model prototype.",
  "evidence_quality": "high",
  "last_reviewed": "2026-07-31"
}
```
