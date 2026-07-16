# Mission Artifact Registry 1.0

1. **Originating intent** — Lieutenant ordered an iterative attack on all doable glue work.
2. **Verified starting state** — Mission Bus supports multiple mission IDs and records artifacts, but `web/data/mission-artifacts.json` does not exist.
3. **Objective / problem** — Produce the designed deterministic public artifact index directly from the append-only Mission Record.
4. **Scope and exclusions** — Add a Mission Bus registry builder, CLI, tests, and current live JSON. No review API, Radio consumer, or artifact-file relocation.
5. **Constraints / authority** — Mission Record remains authoritative; the builder never scans directories or authorizes actions; unknown types fail closed.
6. **Acceptance criteria** — Atomic output; stable record locators; superseded revisions excluded; byte-identical rebuild; source cursor exposed; live URL returns the index.
7. **Tests / rollback** — Mission Bus unit tests plus live HTTPS fetch. Rollback removes the builder command and derived JSON without touching Mission Record.
8. **Assigned actor** — Codex.
9. **Evidence and completion state** — Verified complete. Six Mission Bus tests pass, including byte-identical rebuilding and superseded-revision exclusion. Live HTTPS returns `monad.registry-index.v0.1`, source cursor 10, and five current Kraken artifacts. The output is atomically derived at `web/data/mission-artifacts.json`.
