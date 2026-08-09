# Document Viewer Requirements Intake

Date established: 2026-08-05  
Scope: Semantic Document Viewer requirements only  
Status: Working collection process; not product canon

## Purpose

Keep Document Viewer product direction in one inspectable baseline while the
Admiral and Captain develop it conversationally. Prevent three failures:

- good requirements stranded in chat history;
- speculative ideas silently promoted into commitments;
- implementation beginning before requirement meaning and acceptance are
  clear.

The assembled baseline is:
`docs/reports/2026-08-05-semantic-document-viewer-requirements-baseline.md`.

## Intake loop

```text
receive → restate → classify → trace → place inline → test for ambiguity
        → identify acceptance evidence → preserve → continue collecting
```

For each requirement, record:

1. **Meaning** — concise behavior or constraint, stated in product language.
2. **Source** — Admiral statement, doctrine, observed current behavior,
   research hypothesis, or Captain recommendation.
3. **Authority** — explicit direction, active doctrine, derived requirement,
   candidate experiment, or unresolved decision.
4. **Evidence** — current file, endpoint, corpus measurement, or observed
   defect that makes it relevant.
5. **Priority** — P0 load-bearing, P1 next capability, P2 experiment, or open.
6. **Acceptance** — what observable result would prove the requirement exists.

## Classification language

- **Accepted requirement:** directly ordered by the Admiral or required by
  active doctrine/current architecture.
- **Derived requirement:** necessary to satisfy an accepted requirement but
  still open to correction.
- **Candidate experiment:** an option to compare, not a promised feature.
- **Open decision:** materially different outcomes require Admiral direction.
- **Observed defect:** current behavior contradicts an accepted requirement or
  its own stated contract.

## Assembly rules

- Add the compact item to the baseline's Requirement Register first.
- Expand it in the relevant inline section; do not create one file per idea.
- Keep current capability, requirement, recommendation, and implementation
  state separate.
- Preserve rejected or superseded ideas with their reason when they affected
  course; do not silently delete history.
- Merge duplicates by reference, not by erasing their distinct provenance.
- Requirements never self-authorize code, service changes, publication, or
  canon status.

## Collection checkpoints

Pause for Admiral review when any of these occurs:

- two requirements imply incompatible navigation or authority models;
- a requirement would expose private documents publicly;
- a proposed action can mutate or canonize source material;
- the first implementation chunk has enough acceptance criteria to build;
- a visual experiment competes with reading reliability or accessibility.

Routine clarification, corpus inspection, and inline assembly continue without
requiring a new document or ceremony.
