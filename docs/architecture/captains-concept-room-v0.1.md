# Captain's Concept Room — Chief Build Specification v0.1

**Authority:** Admiral direction, 2026-08-05  
**Status:** Implemented and commissioned first vertical slice  
**Target:** Existing authenticated Living Captain Research station

## Product ruling

The documentation interface is not primarily a place for the Admiral to read
files. The Admiral navigates meaning through the Living Captain; the Captain
navigates documents, history, disagreement, and provenance. Source documents
remain authoritative evidence and the existing Document Viewer remains the
exact-source microscope behind citations.

```text
Admiral question or speech
  -> scoped Concept Room
  -> live corpus and Git retrieval
  -> evidence pack
  -> Captain explanation
  -> spoken brief + visible depth
  -> automatic append-only concept memory
```

## Chief decisions

- One Captain identity with scoped research rooms; room transcripts do not
  pollute the main Bridge conversation.
- New rooms search the whole documentation corpus by default, with visible
  pins and exclusions available later without changing the retrieval seam.
- Root Console remains the presentation and source-serving body. The Live
  Captain service owns room turns, grounding, and durable room memory.
- Use the existing Live Captain SQLite database. Documents and Git remain
  authoritative; FTS and concept maps are rebuildable projections.
- Use SQLite FTS5 plus headings, status, links, recency, and Git history for
  the first commissioned retrieval path. Do not introduce GraphRAG, a vector
  database, another daemon, or an external embedding dependency.
- Automatic memory is durable working interpretation, not automatic canon.
  New evidence appends a revision and preserves the superseded view.
- Speak a concise brief by default and retain the full cited answer onscreen.

## Build chunks and gates

### A. Grounded corpus engine

Build heading-aware chunks with path, title, heading, status, category,
content hash, and source excerpt. Incrementally synchronize a rebuildable FTS5
projection. Return ranked evidence labels and relevant Git events.

**Gate:** deterministic retrieval tests prove current source content is found,
changed content refreshes, removed content disappears, and history is labelled
as commit evidence rather than semantic fact.

### B. Room and memory contracts

Add rooms, room turns, concepts, append-only revisions, and evidence references
to the existing database. Add authenticated room list/create/read, turn, and
concept endpoints. A turn compiles Captain identity, current bearing, room
history, and the evidence pack.

**Gate:** HTTP tests prove authentication, room isolation, grounded prompt
assembly, persistence across store restart, and revision preservation.

### C. Living interface

Make Concept Room the primary Research station: room rail, central dialogue,
intent controls, source scope, evidence, history, and memory. Citations open
the existing source viewer. Reuse the live voice and interruption controls;
use dynamic motion only to communicate real retrieval/synthesis state.

**Gate:** desktop and narrow-screen inspection prove the dialogue remains
primary, sources are reachable, failures stay visible, and ordinary Bridge
conversation still works.

### D. Commissioning

Run explanation, history, comparison, conflict, and daily-brief scenarios.
Restart both coupled services, inspect authenticated live behavior, repair
failures, and reconcile status documentation.

**Gate:** the Admiral-facing live surface answers from real documents with
inspectable evidence and preserves a concept revision.

## Failure and recovery

- Retrieval failure returns an explicit ungounded fault; the Captain does not
  fabricate citations.
- Model failure retains the Admiral turn and evidence state as failed, never a
  successful Captain answer.
- Memory extraction failure cannot invalidate an otherwise successful answer.
- The FTS projection can be rebuilt from disk; concept revisions can be
  reconstructed and inspected from the existing database.
- The existing Document Viewer and Bridge remain available throughout rollout.

## Public contracts

Authenticated Live Captain routes use `/api/concept/rooms`, room-specific
turn/history routes, and `/api/concepts/{id}`. Responses carry room identity,
turn state, Captain text, spoken brief, evidence references, history events,
and memory revision identifiers. Existing `/api/turn` and `/api/stream`
contracts remain compatible.

## Commissioning result — 2026-08-05

The first vertical slice is live in the authenticated Root Research station.
It provides scoped rooms, whole-corpus FTS5 grounding, query routing, Git
history events, cited Captain answers, concise spoken briefs, evidence links,
and automatic append-only concept revisions. The existing Document Viewer
remains the citation microscope.

Commissioning measured 168 live documents and 1,075 heading-aware chunks. The
first real inquiry retrieved eight source passages, cited seven of them in a
4,398-character Captain explanation, produced a 507-character spoken brief,
and persisted concept revision 1. This establishes the integrated loop, not
the final richness of future Atlas or History projections.

## Major Campaign 2 — Concept Room Dynamics

**Objective:** Make grounded inquiry visibly live rather than presenting only
its completed result.

### Streaming contract

Every Codex event emitted during a Concept Room turn carries its room source.
The Research surface renders agent-message deltas into one provisional Captain
turn, then replaces it with the durable completed turn returned by the API.
Concept traffic never appears as injected Bridge conversation. Failure removes
the provisional state without inventing a completed answer.

### Atlas contract

The Atlas is a projection of durable concept revisions and their exact source
references. Concept nodes occupy the semantic center; evidence nodes orbit
them and retain path, heading, status, and revision identity. Selecting a node
opens its inspectable record. Motion communicates new evidence or revision,
respects reduced-motion preference, and never implies authority or certainty.

### Acceptance gate

- a live room turn visibly streams before completion;
- the same completed text remains durable after reload;
- Bridge receives no Concept Room prompt or answer rows;
- the current concept revision renders with its evidence relationships;
- source nodes still open the exact Document Viewer record.

### Commissioning result

Campaign 2 passed its acceptance gate on the live service. One real room turn
emitted `retrieving`, `synthesizing`, and `completed` phases followed by 510
room-tagged agent-message deltas. The accumulated stream was 2,765 characters
and matched the durable Captain turn byte for byte. The actual authenticated
public page and JavaScript asset expose the Living Provenance Atlas, and both
coupled services remained active.

The Atlas now renders a durable concept revision as the center node and its
cited source revisions as inspectable orbital nodes. The geometry communicates
provenance only; the interface explicitly states it is not authority.
