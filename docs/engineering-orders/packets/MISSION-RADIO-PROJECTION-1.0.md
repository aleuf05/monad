# Mission Radio Projection 1.0

1. **Originating intent** — Lieutenant ordered continued execution of the mission glue backlog and less noisy, more radio-like traffic.
2. **Verified starting state** — Radio assembled direct sources and had no shared mission classification gate.
3. **Objective / problem** — Derive a bounded Radio feed from Mission Record authority rather than letting the client reinterpret candidates.
4. **Scope and exclusions** — Static feed generation for accepted recommendation briefings. Radio client consumption follows separately.
5. **Constraints / authority** — Hypotheses, pending/rejected candidates, lore, assets, and routine events are excluded. A distinct human-command acceptance is required.
6. **Acceptance criteria** — Empty before review; one accepted briefing after review; channel, priority, expiry, classification, decision provenance, and dedupe key supplied.
7. **Tests / rollback** — Mission Bus unit tests and live JSON. Rollback deletes the derived feed without touching Mission Record.
8. **Assigned actor** — Codex.
9. **Evidence and completion state** — Verified complete. Eight Mission Bus tests pass, including empty-before-review and one-item-after-acceptance behavior. Live HTTPS exposes one `accepted-briefing` item at Mission Record cursor 10 with decision provenance and `radio_eligible: true`.
