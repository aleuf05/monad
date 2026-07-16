# Living Captain Radio Channel 1.0

1. **Originating intent** — Lieutenant ordered Living Captain its own Radio Console channel.
2. **Verified starting state** — Read-only live status API exposes sequenced Captain actions; Radio has no Captain channel.
3. **Objective / problem** — Make new Captain records audible on a distinct independently toggleable channel.
4. **Scope and exclusions** — Add Captain channel and read-only polling. No Captain mutation, FleetCore command, old-action replay, or Bridge attribution.
5. **Constraints / authority** — Seed cursor on first read; only higher sequences queue; speaker is `Living Captain`; normal power/channel discipline applies.
6. **Acceptance criteria** — Captain chip visible/active; first poll silent; each new action queues once; API failure is silent/retryable.
7. **Tests / rollback** — JS syntax, drift, live page/API markers. Revert commit.
8. **Assigned actor** — Codex.
9. **Evidence and completion state** — Verified complete and recorded. Source/live syntax and drift checks pass. Live HTTPS shows the active Captain channel and versioned client; live source contains the read-only status endpoint, first-poll cursor seed, sequenced-only filter, `Living Captain` speaker, and power-scoped timer. Status API returned `captain.monad`, 13 records, latest sequence 13.
