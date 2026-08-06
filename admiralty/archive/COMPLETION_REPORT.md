# Admiralty Archive — Foundational Seed, Version 0.1

**Date:** 2026-07-31  
**Builder:** Codex under Admiral authority  
**Scope:** Archive foundation and seed only; no runtime or UI implementation

## Created

- `admiralty/archive/` executive archive subsystem;
- registry, schema, canon, executive, project, history, decision, brief, and
  source directories;
- deterministic inventory builder:
  [`tools/build-admiralty-archive.py`](../../tools/build-admiralty-archive.py);
- validation command:
  [`tools/check-admiralty-archive.py`](../../tools/check-admiralty-archive.py);
- UI data contract and machine-readable registries.

## Source regions inspected

Documentary Markdown/RST/text under `docs/`, `logs/`, `archive/`, `fleetcore/`,
`projects/`, `intentforge/`, `tools/`, and `toys/`, plus top-level Monad
charters and repository guidance. Binary assets, generated dependencies,
caches, build output, virtual environments, and routine source code were
excluded.

## Seed counts

- Documents registered: **332**
- Canonical-status records identified by explicit source metadata: **6**
- Proposed-status records: **8**
- Executive records: mission, project state, command state, risks, unresolved
  questions, and recent changes
- Project briefs: **9**
- Retrospective records: master timeline and foundational reconstruction, plus
  explicitly labeled candidate project reconstructions

Counts are generated inventory facts, not claims that every record is current
or complete.

## Uncertainty and missing records

The archive does not resolve competing mission formulations, active versus
retired project status, or the evidentiary status of Living Basin, Beastscape,
and Coalition Engine. Candidate recovery terms such as Minimal Activation
Doctrine, No Ghost Systems, Health outranks mission, and Bedroom Containment
Boundary are listed in [`sources/missing-records.md`](sources/missing-records.md)
without canon promotion.

## Checks run

```text
python3 tools/build-admiralty-archive.py --scan
python3 tools/build-admiralty-archive.py --check
python3 tools/check-admiralty-archive.py
git diff --check
```

Validation passed for registered paths, unique IDs, relationship targets,
allowed status values, retrospective/proposed boundaries, canonical source
support, hash freshness and mutation sensitivity, deterministic source records,
curated metadata preservation, excluded directories, and executive links.

## Claude UI handoff

Build the private Admiralty surface from
[`UI_DATA_CONTRACT.md`](UI_DATA_CONTRACT.md), beginning with the executive brief,
decision queue, active project cards, canonical-document statuses, recent
changes, provenance labels, and visible command boundaries. Keep it static or
lightly functional, private, calm, and legible within the thirty-second
acceptance test. Do not add autonomous command execution, public access, dense
telemetry, or automatic canon promotion.

## Repository facts limiting full population

The repository contains many dated drafts, proposals, reports, and operational
records without uniform metadata. Silence does not establish abandonment, and
the first pass cannot safely infer missing authority or chronology. The archive
is therefore a foundational seed, not a complete institutional history.

## Diff summary

Added the `admiralty/archive/` subsystem, 332-record source registry, five JSON
schemas, four curated registries, nine project briefs, executive/history/source
records, UI contract, deterministic builder, validator, and documentation-map
links. Existing source documents and unrelated pre-existing working-tree
changes were left in place.
