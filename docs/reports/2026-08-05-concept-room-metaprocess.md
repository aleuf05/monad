# Concept Room — Captain/Chief/Tech Lead Meta-process

**Date:** 2026-08-05  
**Status:** Live implementation trace; append consequential evidence only

## Captain Architect phase

The Admiral rejected the premise that the ideal Document Viewer is mainly a
reading surface. Research and repository inspection produced the inversion:
documents become evidence underneath a Captain-led concept, history, and
comparison conversation. The Admiral selected scoped rooms, live dialogue as
the hero, automatic memory, whole-corpus default scope, spoken briefs with
visible depth, and append-only revisions.

External patterns inspected included source-grounded cited dialogue,
multi-perspective concept maps, contextual hybrid retrieval, and local/global
query routing. The full GraphRAG path was rejected for the present roughly
699 KiB corpus because it adds cost and machinery before a measured need.

**Exit evidence:** decision-complete Concept Room course accepted by the
Admiral with an implementation order.

## Chief Engineer phase

Inspection confirmed:

- Root Console already owns the authenticated UI and exact source viewer;
- Live Captain already owns persistent conversation, context compilation,
  synchronous Codex turns, SSE, and the operational SQLite database;
- Python's SQLite build supports FTS5;
- the live corpus contains 165 Markdown documents read directly from disk;
- Git already provides the authoritative revision chronology;
- unrelated Master Page, voice, Fleetnet, and Intake work is present in the
  dirty tree and must be preserved.

The Chief selected one existing database, one Captain, and one live UI target.
The build is divided into grounded retrieval, room/memory contracts, Living
interface, and commissioning gates.

**Exit evidence:** `docs/architecture/captains-concept-room-v0.1.md` contains
the build specification; Doctrine 026 records the reusable phase discipline.

## Technical Lead phase

The implementation added a rebuildable FTS5 projection, scoped room and turn
persistence, append-only concept revisions with evidence, authenticated room
APIs, grounded Captain prompt compilation, and a full-width Concept Room in
the existing Research station. The interface provides intent controls,
conversation, evidence, Git history, memory cards, source opening, and spoken
briefs through the existing voice path.

### Discoveries and repairs

- The loopback Root Console server's `/` serves an older diagnostic static
  page, while Caddy's actual authenticated `/root/` route correctly serves
  `console/`. Verification was moved to the real public route rather than
  changing the correct target to satisfy a misleading loopback check.
- The first HTTPS loopback probe failed because the inspection client omitted
  TLS SNI. The service was healthy; verification changed to an SNI-correct
  `cameronlampley.com` request resolved to loopback.
- The prior requirements pass found incoming packets labelled `Staged, not
  filed` were classified neutral. The live parser now accepts that established
  wording as staged.
- A redundant UI expression in memory refresh was removed before live handoff.

### Verification evidence

- 74 Live Captain tests and 22 Root Console tests pass.
- Both browser scripts pass JavaScript syntax checks.
- Real corpus synchronization produced 168 documents and 1,075 chunks.
- Both coupled services restarted healthy.
- Authenticated room create/list/open passed against the live service.
- A real Concept Room inquiry completed in 29.7 seconds, retrieved eight
  passages, cited seven, produced a 507-character spoken brief and a
  4,398-character answer, and persisted revision 1.
- The actual Caddy/authenticated `/root/`, Concept Room asset, and room API all
  returned HTTP 200.

**Exit evidence:** the first grounded Captain-led documentary explanation is
live and recoverable. Further visual Atlas depth is enhancement, not a blocker
to the commissioned interaction loop.

## Captain Verification phase

The Captain reconciled source, tests, service state, public routing, and the
first persisted result. Doctrine 026 proved useful immediately: a premature
Tech Lead transition was corrected when the Admiral observed the Chief package
had not yet been made durable. The process now requires phase exit evidence,
not merely a declared role change.

## Major Campaign 2 — Concept Room Dynamics

The Captain selected the next pressure without returning sequencing upward:
room-scoped token streaming plus a provenance Atlas. They are one campaign
because streaming exposes semantic formation in time while the Atlas exposes
the durable structure left behind. The first implementation also closes a
discovered integration risk: raw Concept Room daemon events must not be
rendered as ordinary Bridge turns.

### Implementation and evidence

The daemon now tags every Codex event with the semantic source established at
turn start. Root Console diverts `concept-room:*` traffic away from Bridge and
into a room-scoped browser event. Research builds one provisional Captain row
from deltas and replaces it with the durable API result at completion.

The Atlas was built from existing concept revision and evidence tables rather
than adding graph storage. This was a Process–Container decision: the view is a
projection of the semantic record, not a second record trying to become the
environment.

Live commissioning captured 510 deltas and proved their concatenation exactly
equalled the 2,765-character persisted answer. Public Caddy checks returned
200 for the page and updated asset. The Atlas markup and renderer were present,
and both coupled services remained active.

**Campaign exit evidence:** semantic formation is visibly live, durable result
matches the stream, Bridge routing is source-aware, and current concept/source
relationships have a dynamic inspectable projection.
