# Semantic Document Viewer — Requirements Baseline

Date: 2026-08-05  
Status: Superseded as product center by the accepted Captain's Concept Room
course; preserved as source-viewer requirements and design history  
Target: Existing authenticated `console/documents.html` and
`tools/root-console/docs_corpus.py`

## Mission

> **Course change, 2026-08-05:** The Admiral ruled that documentation
> ingestion is Captain-led concept and history explanation, not primarily
> direct reading. Requirements below remain relevant to the evidence
> microscope behind citations. The active implementation specification is
> `docs/architecture/captains-concept-room-v0.1.md`.

Make the existing Semantic Document Viewer support four connected jobs:

```text
deep reading → comprehension → comparison → governed engineering action
```

The viewer remains a reading and decision-support surface. It must not become
a second document store, silently mutate canon, or replace the established
packet lifecycle.

## Authority and requirement sources

- Admiral direction on 2026-08-05: pause the Intake chunk and collect Document
  Viewer requirements.
- The staged Captain Watch objective `ec08e2de5576`, currently
  `AWAITING_ADMIRAL`, names deep reading, comprehension, comparison, and
  movement into engineering action. Its dormant state is preserved; this
  requirements pass does not approve or execute it.
- Doctrine 012 requires read-before-filing and separation of submitted text
  from assessment.
- Doctrine 013 defines staged, filed, refused, and research-split lifecycle
  meaning; an original refusal is never rewritten.
- The existing viewer and corpus collector establish the working baseline.
- The Ultra-Rich Text conference brief supplies optional visual hypotheses,
  not mandatory product requirements.

Collection and change procedure:
`docs/workflows/document-viewer-requirements-intake.md`.

## Requirement register

| ID | Requirement | Source | Authority | Priority | State |
|---|---|---|---|---|---|
| DV-001 | Organize the document pool through Category, Newest, Priority, and Hierarchy lenses rather than one long list. | Admiral, direct conversation, 2026-08-05 | Explicit product direction | P0 product need | Accepted requirement |
| DV-002 | Support deep reading, comprehension, comparison, and movement into engineering action. | Staged Captain Watch objective `ec08e2de5576` | Proposed; awaiting Admiral approval for autonomous execution | Mission framing | Requirement source only |
| DV-003 | Preserve live-off-disk corpus behavior and the existing authenticated target. | Existing implementation + Monad target discipline | Operational constraint | P0 | Accepted constraint |
| DV-004 | Preserve staged/filed/refused lifecycle truth and read-before-filing. | Doctrine 012/013 | Active doctrine | P0 | Accepted constraint |
| DV-005 | Priority placement must be deterministic, explainable, and allow Unclassified. | Captain synthesis of DV-001 under narrative-follows-reality doctrine | Derived requirement | P0 safety | Proposed for Admiral review |
| DV-006 | First implementation chunk should establish organization and comprehension before rich visual experiments. | Captain recommendation from current corpus inspection | Recommendation | Course | Proposed for Admiral review |

New requirements are added here before they are dispersed into design or
implementation sections. A register entry can be accepted as a requirement
without authorizing its implementation.

## Verified current baseline

The live authenticated corpus currently contains 165 documents and about
699 KiB of Markdown:

| Category | Count |
|---|---:|
| Packets | 75 |
| Reports / chronicle | 42 |
| Doctrine | 29 |
| Engineering notes | 15 |
| Incoming | 2 |
| Open queries | 2 |

Working behavior already includes:

- live reads from disk with no manifest, sync job, or corpus cache;
- authenticated Root Console API and login recovery;
- category navigation, keyboard movement, search, URL deep links, and browser
  back/forward behavior;
- dark, light, and paper themes; font, size, measure, focus, and MSIR-gloss
  controls persisted locally;
- Markdown headings, lists, links, fenced code, tables, and normal browser
  selection/copy;
- deterministic document identicons;
- provenance-reactive status presentation;
- `[[wikilink]]` navigation, backlinks, related-document context, and MSIR
  vocabulary derived from the corpus itself.

## P0 — load-bearing requirements

### One real target

Extend the existing authenticated viewer and Root Console corpus endpoint.
Do not create a replacement application, shadow corpus, alternate manifest,
or second document service.

### Narrative follows document reality

The viewer must distinguish at minimum:

- staged / unevaluated;
- refused;
- confirmed or filed evidence where explicitly supported;
- proposal or design;
- reconstruction or recollection;
- unclassified.

Status comes from repository conventions and filing provenance, not from a
document granting authority to itself. Unknown state must remain unknown.

### Preserve the packet lifecycle

- Arrival and staging are not filing.
- Reading precedes disposition.
- Submitted text and Captain assessment remain visibly separate.
- Refusal review appends evidence; it never rewrites the original refusal.
- Any action launched from the viewer must use the existing Packet Drop,
  review, query, M³, or engineering path and expose its consequence.

### Deep reading must remain ordinary and reliable

- Text remains selectable, copyable, searchable, linkable, printable, and
  legible without WebGL or GPU effects.
- Reading preferences persist without altering source documents.
- Long prose, code, tables, MSIR notation, and mathematical material degrade
  gracefully when specialized rendering is unavailable.
- Focus mode must not remove access to document identity or provenance.

### Trust boundary

- Private engineering documents remain behind existing Root authentication.
- Rendered Markdown must not gain script execution or unsafe URL behavior.
- Read operations do not write to source files.
- Consequential document actions retain their existing confirmation and
  authority boundaries.

## P1 — required next capability

### Document-pool organization — highest-level need

The corpus must stop reading as one long list with category dividers. The same
live document pool needs several switchable **navigation lenses**. A lens is a
projection, never a copied collection or new authority layer.

Required lenses:

1. **Category shelves** — Incoming, Queries, Packets, Reports, Notes, and
   Doctrine, each collapsible with counts and status composition. This evolves
   the current grouping without discarding it.
2. **Newest / timeline** — today, this week, older, with exact modification
   time available and clear separation between source date and filesystem
   modification date where both exist.
3. **Priority / attention deck** — a transparent operational ordering:
   - **Now:** staged material, open queries, explicit action-required items,
     and Admiral-pinned documents;
   - **Next:** unresolved review conditions and active-course material;
   - **Reference:** doctrine, verified reports, and completed records;
   - **Unclassified:** items lacking enough evidence for placement.
   Every placement must show its reason. The viewer must not invent urgency
   from dramatic wording inside a document.
4. **Hierarchy / library tree** — repository path hierarchy with folders,
   document children, backlinks, and `[[wikilink]]` branches. This answers
   “where does this belong?” rather than only “when did it change?”

Creative secondary views worth prototyping after the four foundations:

- **Captain's chart:** a two-dimensional map with lifecycle on one axis
  (staged → evaluated → disposition) and document role on the other
  (evidence → analysis → decision → doctrine). Empty or uncertain cells remain
  visible instead of being force-classified.
- **Constellation:** a graph of explicit links and backlinks, with isolated
  documents shown as islands. Graph distance never becomes authority or
  priority by itself.
- **Working table:** a dense, sortable inspector for path, status, category,
  dates, link count, and explicit priority reason.

Cross-lens behavior:

- switching lenses preserves selection, reading position, filters, and pinned
  comparison documents;
- search narrows the active lens rather than flattening back into a list;
- counts and empty states remain truthful when filters are active;
- the active lens and selection are deep-linkable or locally recoverable;
- operator pins are visibly manual and never rewrite document metadata;
- priority rules are inspectable and deterministic, with `Unclassified` as a
  valid outcome.

### Comprehension

- Search full document content, titles, paths, status, and category. The
  current search sees title plus only the first 240 excerpt characters.
- Provide a document outline with heading navigation and current-position
  awareness for long material.
- Make provenance, status basis, source path, modification time, outbound
  links, backlinks, and unresolved links inspectable.
- Distinguish verbatim source content, extracted facts, Captain assessment,
  open questions, and proposed action when those layers exist.
- Preserve a stable URL for both the document and, where practical, a heading
  or selected passage.

### Comparison

- Pin at least two documents without losing the current reading position.
- Support synchronized or independently scrolling side-by-side reading.
- Show status, provenance, timestamps, links, and headings for both documents.
- Offer exact textual difference where meaningful, while keeping semantic
  interpretation explicitly labelled as interpretation.
- Make comparison reversible and shareable through URL or recoverable local
  state; it must not create a new authoritative document.

### Movement into engineering action

- Show the next lawful action for the selected document based on its actual
  lifecycle state—for example evaluate staged material, inspect a query,
  review a refusal condition, open related evidence, or enter M³ review.
- Carry document identity and source path into the existing target workflow so
  the operator does not re-find the same item manually.
- Display whether the transition merely opened a workspace, staged a change,
  committed a result, or failed. Opening a workflow is not completion.
- Keep human-only decisions visibly distinct from continuing Captain duties.

### Responsive operation

- Desktop supports three-pane reading and comparison.
- Phone and narrow-window layouts preserve document selection, readable body,
  context access, and action access without horizontal page overflow.
- Keyboard use remains first class; touch targets and focus order must be
  usable without a mouse.

## P2 — candidate enrichments, not settled requirements

The following should be tested as competing hypotheses rather than shipped as
a bundle:

- a live related-document node graph versus the current flat related list;
- a small custom Monad glyph vocabulary or variable-font status treatment;
- accessible KaTeX or MathJax rendering for real mathematical notation;
- reactive/explorable blocks for documents that explicitly declare a bounded
  executable model;
- passage highlighting and private working notes;
- ambient semantic fields or SDF/3D hero glyphs.

Every enrichment must prove that it improves comprehension, comparison speed,
or action accuracy. Visual dynamism that slows scanning or obscures provenance
fails the viewer's job. Body text never requires a GPU path.

## Observed defects and gaps to carry into implementation

1. **Staged status drift:** both current `docs/incoming/` packets render as
   `neutral`. The parser expects `Status: staged, awaiting evaluation`; actual
   packet headers say `Status: Staged, not filed.`
2. **Search depth:** only title and the first 240 characters are searched.
3. **Pool organization:** category headings still resolve to one tall list;
   there is no newest, priority, hierarchy, lifecycle, or dense-table lens.
4. **No comparison workspace:** related documents replace the active document.
5. **No outline or passage address:** long-document movement resets to the top.
6. **No action seam:** the viewer explains status but does not carry a selected
   document into its existing evaluation/review/engineering workflow.
7. **No explicit narrow-screen layout:** the three fixed columns have no
   viewer-specific responsive rule.
8. **Status coverage is weak:** 143 of 165 current documents are unclassified.
   This may reflect honest absence of metadata, parser drift, or both; it must
   be measured before adding broader inference.
9. **Markdown coverage is intentionally minimal:** blockquotes, ordered and
   nested lists, task lists, heading anchors, and rich math are not represented
   faithfully.

## Acceptance criteria for the first implementation chunk

The first build should be an organization and comprehension foundation, not the fanciest visual
experiment. It passes when:

1. staged packets are classified correctly with regression tests;
2. Category, Newest, Priority, and Hierarchy lenses operate over the same live
   corpus and preserve selection when switched;
3. every Priority placement exposes a deterministic reason and uncertain
   documents remain Unclassified;
4. full-content search returns a term occurring beyond the excerpt boundary
   without discarding the active lens;
5. a long document exposes a usable heading outline and stable heading link;
6. the authenticated live viewer works at desktop and phone widths;
7. existing selection/copy, themes, focus, links, tables, MSIR glossing, and
   URL document navigation do not regress;
8. no new service, corpus store, manifest, or public document exposure is
   introduced;
9. current corpus and browser behavior are inspected after deployment.

Comparison and action seams should follow as the second large chunk once this
foundation is proven.

## Decisions still requiring Admiral direction

1. Should private working annotations exist, and if so are they ephemeral,
   browser-local, or durable with provenance?
2. Should refusal review be initiated directly from the viewer or only linked
   to a dedicated review surface?
3. Is the first visual experiment a related-document graph, a custom glyph
   language, variable typography, or none until comparison is complete?
4. Should mathematical rendering favor KaTeX speed or MathJax accessibility
   and coverage?
5. Is any subset of the corpus intended for public reading? Current scope is
   the authenticated Root viewer; this baseline grants no public exposure.

## Recommended course

Build in three verified chunks:

```text
1. organization and comprehension foundation
   four pool lenses + status truth + full search + outline + responsive reading

2. comparison and continuity
   pinned documents + diff + preserved positions + shareable workspace

3. governed action and visual experiments
   lifecycle transitions + one discriminating rich-language prototype
```

The staged Captain Watch objective remains dormant until explicitly approved.
This report supplies requirements and a course; it does not consume an
autonomous move or declare the viewer work complete.
