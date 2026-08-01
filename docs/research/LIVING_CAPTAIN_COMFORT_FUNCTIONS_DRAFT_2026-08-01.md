# Living Captain Comfort Functions — Draft

- **Recorded:** 2026-08-01
- **Status:** Non-canonical design speculation
- **Provenance:** Admiral observation that the current live interface is not
  polished, functional, or comfortable; Captain inspection of the deployed
  `web/toys/living-captain/` source and existing Living Captain doctrine.
- **Authorship:** Human problem statement; AI diagnosis and proposed ordering.

## Core diagnosis

**Technical finding:** The current page is organized primarily around proving
the Captain runtime exists and is bounded: identity, restarts, status, budget,
custody manifest, and append-only actions dominate the surface.

**Inference:** Those controls are useful as an inspector or engineering panel,
but they do not yet form a comfortable conversation environment. The primary
surface should serve the Admiral's conversation; runtime proof should remain
available in a secondary inspector.

## Proposed functional hierarchy

### 1. Immediate orientation

On entry, show a compact Captain briefing:

- what is happening now;
- what changed since the Admiral's last visit;
- what needs judgment or attention;
- what the Captain is uncertain about;
- whether any service or evidence source is stale.

**Inference:** This is more useful than leading with Captain ID and restart
count. Those facts remain inspectable but are not the principal human task.

### 2. Conversation continuity

The conference should support named, durable sessions with visible time,
restoration after refresh, a clear current-course marker, and an explicit
boundary between full transcript, Captain summary, and canonical record.

Desired conveniences include:

- resume where the conversation stopped;
- search within the conference;
- jump to decisions, unresolved questions, and cited artifacts;
- mark a message or exchange for later judgment;
- show what was captured as a draft without implying canon promotion.

### 3. Evidence attached to answers

Captain answers should expose compact source chips or an evidence drawer with
source time, freshness, and epistemic status. The default answer stays natural;
provenance is one gesture away.

### 4. Safe action handoff

Conversation should be able to form a proposed action or work request without
silently executing it. The interface should display:

- the Captain's understanding of intent;
- exact scope and expected result;
- authority/cost/side-effect boundary;
- required human approval;
- execution state and returned evidence.

### 5. Human comfort and control

Recommended interaction details:

- a larger, persistent composer anchored to the viewport;
- clear sending, thinking, waiting, failed, and reconnected states;
- stop/cancel generation;
- edit-and-resend and retry;
- keyboard shortcuts and good mobile behavior;
- restrained voice controls hidden until requested;
- readable message width, timestamps on demand, and reduced visual density;
- a conspicuous privacy/read-only/authority indicator stated once, not repeated
  throughout the page.

### 6. Progressive disclosure

Recommended surface order:

1. briefing and active conversation;
2. current decisions, questions, and suggested next actions;
3. evidence and relevant live state;
4. runtime identity, budget, custody, and action log in an inspector drawer.

## Proposed first product slice

**Conjecture:** The smallest change with the greatest comfort gain is a
conversation-first layout containing:

1. a returning-user briefing;
2. durable transcript restoration;
3. a fixed composer with trustworthy activity/error states;
4. source/freshness affordances on each Captain response;
5. a collapsible runtime inspector containing the existing diagnostic panels.

This slice adds no autonomous command authority. Action proposals and workbench
integration should follow only after conversation and evidence handling are
comfortable and dependable.

## Unknowns requiring observation

- Which discomfort dominates in actual use: layout density, latency, loss of
  continuity, weak Captain answers, or missing action capability?
- Does the Admiral want one continuous private conference or multiple named
  threads/courses?
- Which live instruments should be reachable from cited Captain answers?
- Which proposed actions are common enough to deserve direct interface
  affordances rather than conversation-only handling?

## Live activity density observation

- **Provenance:** Admiral direction, 2026-08-01; implementation inspected in
  `tools/root-console/static/app.js` and `console/assets/js/root-console.js`.
- **Human design ruling:** The interface should reassure the Admiral that the
  Captain is alive without displaying every possible status transition.
- **Technical finding:** The animated thinking indicator, streamed response,
  completed reasoning/tool items, telemetry, and errors provide sufficient
  live insight. Item-start, turn lifecycle, thread-status, MCP-startup, and
  unknown protocol notifications add scrollback density without comparable
  executive value.
- **Draft principle:** Prefer a small transient pulse of liveness and durable
  records of meaningful completed work; suppress routine control-plane churn.
