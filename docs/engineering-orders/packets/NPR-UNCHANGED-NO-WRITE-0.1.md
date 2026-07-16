# NPR Unchanged Snapshot No-Write 0.1

1. **Originating intent** — Rich Voice commissioning repeatedly refused because the 15-minute NPR cron dirtied a tracked snapshot even when only `fetched_at` changed.
2. **Verified starting state** — `fetch_headlines()` unconditionally rewrote `web/data/npr-headlines.json`; two consecutive scheduled runs with identical items advanced only the timestamp and invalidated clean commit pins.
3. **Objective / problem** — Preserve the tracked snapshot byte-for-byte when fetched headline items are unchanged.
4. **Scope and exclusions** — Compare parsed headline items to the existing file before constructing/writing a new payload; add a regression test. Do not alter feed URL, cadence, item count or podcast behavior.
5. **Constraints / authority** — A changed item set must still update immediately; corrupt/missing existing JSON must be replaced normally; fetch failures retain prior data.
6. **Acceptance criteria** — Identical items retain original timestamp and modification time; changed items follow the existing write path; cron exits successfully.
7. **Tests / rollback** — Network-free unit test plus direct fetch smoke test. Revert this packet and fetch/test changes.
8. **Assigned actor** — Codex, as a workflow repair discovered during authorized Voice commissioning.
9. **Evidence and completion state** — Verified complete and recorded. Two network-free tests prove unchanged items preserve bytes/timestamp while changed items replace the snapshot. A direct live-feed smoke run reported `headlines unchanged` and left Git clean apart from this implementation.
