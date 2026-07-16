# Engineering Order: Human Review Inbox V0.1

Priority: Medium

Scope: Read-side unification only. The shared feed and its public viewer —
not a new decision-write path.

Doctrine: `docs/architecture/human-review-inbox-v0.1.md` (GLUE-05) designed
this generalization explicitly *without* generalizing canon-writing
authority: "Current endpoints can remain... World Intake cards may be
projected into that feed, but canon adjudication POSTs continue to go to
World Intake so its compiler, validation, and FleetCore receipt chain remain
intact." This order builds exactly that projection, and stops there.

Source: `docs/architecture/component-consolidation-master-plan-v0.1.md`'s
Phase 3 ("World Intake's adjudication flow + Mission Bus's `review()` are
the same conceptual pattern implemented twice... worth its own decision
rather than folding into either phase above"). GLUE-05 already did the
design work; nobody had built any of it yet.

## What already existed

Investigating before building turned up more than expected: Mission Bus's
`tools/mission-bus/mission_bus.py build_reviews()` already writes
`web/data/mission-reviews.json` in almost exactly GLUE-05's `ReviewCard`
shape (`schema_version: "monad.review.v0.1"`, `review_id`, `artifact_id`,
`status`, `requested_action`, `required_authority`, `evidence_refs`,
`conflicts`, `summary`, `proposed_data`, `created_at`,
`supersedes_review_id`, `revision`) — real field-for-field compliance, not
approximate. That side of GLUE-05 was effectively already done. World Intake
never emitted this shape at all; its `/proposals` endpoint returns its own
native assertion-card format, which is what actually needed normalizing.

## V0.1 decomposition

### 1. `tools/review-inbox/review_inbox.py`

Read-only, no write path anywhere in this file. On each run:

- Fetches World Intake's `GET /proposals?status=pending` (no auth required —
  only `POST /adjudications` needs the Captain bearer token, and this tool
  never calls that) and normalizes each native assertion card into a
  `ReviewCard`, per GLUE-05's own "Mapping onto World Intake" table:
  `assertion_id` -> native ID retained inside `proposed_data`; `artifact_type`
  set to `"fleetcore-command-proposal"` (World Intake's proposals all carry a
  `proposed_fleetcore_command`, matching that row in GLUE-05's authority
  table); `required_authority` `"human-command"` (the existing Captain-token
  gate); `evidence_refs` from `provenance.source_id`; `created_at` from
  `provenance.source_timestamp`.
- Reads Mission Bus's existing `web/data/mission-reviews.json` cards
  directly — already conformant, no transform needed beyond tagging
  `source_system`.
- Merges both into one array, sorted newest-first, tags each card with
  `source_system` (`"world-intake"` or `"mission-bus"`) so the viewer can
  show provenance and link back to the actual decision surface.
- Writes `web/data/review-inbox.json`: `{schema_version, generated_at,
  pending_count, cards: [...]}`.

### 2. `toys/review-inbox/` — the public viewer

Static page, no build step, no backend of its own (same shape as
`toys/watch-officer/`). Renders every card with the provenance GLUE-05
requires being visible without devtools: artifact type, status, source
system, evidence refs, conflicts, summary, required authority, and — this is
the part that keeps this V0.1 honest about what it is — a **"Decide at
source"** link per card pointing at whichever system actually owns that
card's write path (`toys/world-intake/` for World Intake cards; Mission
Bus cards note that no public decision UI exists yet and point at
`toys/agent-ops/`, the closest existing surface that projects Mission
Record state). This page cannot itself accept/reject/defer anything — doing
so would mean reimplementing each system's compile/commit/authority chain
a second time, exactly what GLUE-05 says not to do.

### 3. Refresh cadence

Same non-privileged pattern as Watch Officer and NPR: a user crontab entry
(no `sudo`) regenerates `review-inbox.json` periodically. No systemd unit —
privileged, the Lieutenant's step if ever wanted.

## Deferred (explicitly not in V0.1, per GLUE-05's own text)

- `POST /mission-review-api/decisions` — the actual unified decision
  endpoint. Building this means reconciling World Intake's compile/commit
  chain with Mission Bus's `review()` in one authority path — a real
  backend project, not a read-side aggregation script.
- `accept`/`reject`/`defer`/`edit`/`regenerate` actions from the shared
  viewer. "No bulk acceptance in V0.1" is explicit in GLUE-05 itself for
  the *real* shared inbox; this V0.1 has no acceptance action at all yet.
- Optimistic-concurrency revision checking (409 on stale revision) — moot
  until there's a write path to be stale against.
- Reviewer authentication in the shared viewer — it's read-only, so there's
  nothing to authenticate a decision against yet.

## Done evidence

`review_inbox.py --once` run against the real live `world-intake.service`
and the real `web/data/mission-reviews.json` on this host, not fixtures.
Verified the merge is genuinely correct, not just non-crashing: card counts
from each source sum to the combined total, every World Intake card's
`proposed_data.assertion_id` round-trips, and Mission Bus's one existing
card (`review.cognition.kraken.verdict-01`, status `accepted`) appears
unchanged alongside the 39 pending World Intake cards. Public page verified
live at `https://cameronlampley.com/toys/review-inbox/`.
