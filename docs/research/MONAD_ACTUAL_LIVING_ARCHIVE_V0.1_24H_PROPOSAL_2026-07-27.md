# Monad Actual — Living Archive v0.1

**Recorded:** 2026-07-27  
**Source:** Admiral/Captain private conference  
**Status:** Draft proposal; not authorized for implementation or deployment  
**Timebox:** 24 elapsed hours, with bounded work periods and a full sleep cycle  

## Mission

**Project doctrine, proposed:** Reshape the existing Monad documentation into a
coherent living archive that can receive insights from natural conversation,
classify them, preserve provenance, expose contradictions, and restore context
for future Captain/Admiral conferences.

The first release is an archive and review system, not an autonomous agent and
not a production deployment.

## Visible result

At the end of the timebox, the repository should contain:

1. a single archive entry point;
2. a document-status and epistemic-label schema;
3. a generated inventory of relevant project records;
4. decision, terminology, open-question, and contradiction ledgers;
5. a rolling conference synthesis;
6. a context-restoration packet;
7. validation that catches missing metadata and broken archive links.

## Information architecture

### Human-facing entry point

`docs/archive/README.md` should explain, in one screen:

- what Monad Actual is;
- where canon, drafts, evidence, incidents, and narrative live;
- what changed recently;
- which questions require the Admiral;
- how to resume the latest conference.

### Machine-readable catalog

A generated catalog should record:

- path;
- title;
- date;
- status;
- authorship;
- epistemic classifications;
- related records;
- verification state;
- sensitivity marker.

The catalog is a projection of documents, not an independent source of truth.

### Core ledgers

- `decisions.md`: explicit human rulings and their scope.
- `terminology.md`: definitions and collisions.
- `open-questions.md`: unresolved questions without inferred answers.
- `contradictions.md`: conflicting claims with provenance.
- `conference-synthesis.md`: current rolling summary.

## Natural-conversation loop

**Proposed design:**

1. Admiral and Captain converse normally.
2. Captain extracts durable material.
3. Captain labels claims and writes draft records.
4. A local indexer updates the catalog and archive entry point.
5. Validation reports structural gaps without modifying canon.
6. Captain gives brief periodic summaries at natural boundaries.

## Twenty-four-hour course

### Hours 0–2: preserve and map

- Capture Git status and relevant document inventory.
- Identify nested repository instructions.
- Record pre-existing uncommitted work.
- Define canonical-versus-draft boundaries from evidence.

### Hours 2–5: establish the schema

- Write the minimal metadata convention.
- Define status and epistemic labels.
- Define sensitivity and provenance fields.
- Create the archive entry point and empty ledgers.

### Hours 5–9: build the indexer

- Implement a small local script that scans documentation metadata.
- Generate the catalog deterministically.
- Report missing or invalid fields without rewriting source documents.
- Add focused tests.

### Hours 9–12: curate the first corpus

- Index governing doctrine and Monad Actual records.
- Populate decisions, terminology, open questions, and contradictions from
  evidence.
- Link research proposals without promoting them to canon.

### Hours 12–14: build continuity

- Create the rolling conference synthesis.
- Produce a context-restoration packet.
- Document the capture and resumption workflow.

### Hours 14–16: verify and close

- Run link, metadata, and deterministic-generation checks.
- Review Git diff for accidental changes or sensitive content.
- Produce a concise findings report and proposed next increment.

### Remaining elapsed time

Reserved for meals, movement, decompression, and a full sleep cycle. Work does
not continue merely to fill the clock.

## Acceptance criteria

- No production, network, service, credential, container, or deployment change.
- No deletion or silent reclassification of existing material.
- No secret contents displayed or committed.
- Every indexed claim preserves its source and status.
- Generated output is reproducible.
- The Admiral can enter through one document and understand the project state.
- The next session can resume from written records rather than model memory.
- The operator completes a normal sleep cycle during the 24-hour window.

## Explicit non-goals

- autonomous canon promotion;
- diagnosis or storage of sensitive medical details;
- broad repository cleanup;
- replacement of Git history;
- deployment to the public site;
- restoration of SSH, Portainer, or Granite services;
- claims that Monad is conscious or cosmically authoritative.

## Principal risk

**Inference:** The greatest risk is scope inflation: attempting to redesign the
entire software platform instead of completing a narrow, trustworthy knowledge
spine.

## Recommendation

**Captain recommendation:** Approve only the archive spine for this increment.
Once it is coherent and verified, later work can attach interfaces, search,
semantic retrieval, and conversational automation without sacrificing
provenance.
