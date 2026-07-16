# NPR Headline Reader 1.0

1. **Originating intent** — The Lieutenant directed Engineering to choose and start a Radio Console task based on project principles, following the NPR-feature focus and voice-quality review.
2. **Verified starting state** — The console selects a real NPR lead topic but deliberately keeps news outside FleetCore speech. Browser speech synthesis is already available for fictional fleet traffic.
3. **Objective / problem** — Let the operator deliberately hear the selected NPR headline without making it sound like fleet radio traffic.
4. **Scope and exclusions** — Add an opt-in headline reader and visible voice status. Do not autoplay, read article text absent from the feed, enqueue news as fleet traffic, or apply radio static/squelch effects.
5. **Constraints / authority** — NPR attribution remains visible; speech identifies NPR as the source; unsupported browsers fail visibly; source and live copies ship together.
6. **Acceptance criteria** — Selected headline can be read/stopped; spoken text begins with NPR attribution; changing topic stops old speech; fleet transcript and radio speaking state remain untouched.
7. **Tests / rollback** — JavaScript syntax check, source/live drift check, and live HTTPS marker checks. Roll back by reverting the implementation commit.
8. **Assigned actor** — Codex.
9. **Evidence and completion state** — Verified complete and recorded. Source and live JavaScript passed `node --check`; `tools/check-toy-drift.py` reports synchronization; live HTTPS checks confirmed the read/stop control, explicit fleet-radio separation label, versioned script, NPR attribution phrase, and reader handler at `https://cameronlampley.com/toys/radio-console/`.
