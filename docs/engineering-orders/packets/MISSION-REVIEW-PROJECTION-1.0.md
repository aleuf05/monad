# Mission Review Projection 1.0

1. **Originating intent** — Lieutenant ordered continued execution of the doable glue backlog.
2. **Verified starting state** — Review decisions existed in Mission Record and the Kraken UI, but no generalized review-card projection existed.
3. **Objective / problem** — Derive reusable review cards by joining immutable candidate and decision artifacts, and make them visible in Agent Ops.
4. **Scope and exclusions** — Read-only static projection and UI. No decision POST API in this slice.
5. **Constraints / authority** — Candidate state is never rewritten; only `human-command` decisions resolve cards; the UI cannot authorize work.
6. **Acceptance criteria** — Pending before decision, accepted/rejected after joined decision, revision and authority visible, FleetCore consequence explicit, live click-reachable display.
7. **Tests / rollback** — Mission Bus tests and live HTTPS. Rollback removes the derived JSON/UI without changing Mission Record.
8. **Assigned actor** — Codex.
9. **Evidence and completion state** — Seven Mission Bus tests pass. Live projection reports zero pending and the immutable Kraken recommendation joined to its accepted decision at cursor 10; Agent Ops visibly renders the Review Inbox.
