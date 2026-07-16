# QUacken Mission Archive 1.0

1. **Originating intent** — The Lieutenant ordered the QUacken mission deactivated and archived on 2026-07-16.
2. **Verified starting state** — Both QUacken runs are `MISSION_COMPLETE`; no Mission Director process or service is running. The homepage and Command Deck still present run 002 as `ACTIVE MISSION` and poll its JSON.
3. **Objective / problem** — Remove QUacken from active presentation while preserving its reports, director state, and downstream evidence references.
4. **Scope and exclusions** — Move public reports to `web/archive/missions/`, director state to `tools/mission-director/archive/`, add a clearly classified plain-text legend, and update evidence consumers and front doors. Do not mutate FleetCore, Living Fleet memory, mission evidence, or privileged services.
5. **Constraints / authority** — Archived truth remains readable and hashable; no evidence is deleted; `web/index.html` and `web/command-deck.html` remain synchronized in mission presentation.
6. **Acceptance criteria** — No active QUacken widget or polling remains; both archived reports are reachable from the site root; original active paths are absent; Legend Pipeline and Living Fleet seed tests use the archive; mission tests pass.
7. **Tests / rollback** — Run relevant Python tests, link/path checks, and live HTTPS checks. Roll back by reverting the commit, which restores all paths.
8. **Assigned actor** — Codex.
9. **Evidence and completion state** — Verified complete and recorded. No Mission Director process/service was active. Legend Pipeline's 4 tests and Living Fleet seed import's 3 tests pass against the archived record. Live HTTPS shows `MISSION ARCHIVE` / `RETIRED FROM ACTIVE WATCH`; `/archive/missions/quacken-transit-002/` and its `LEGEND.txt` return 200; the former active path returns 404. Both completed reports and director-state files remain preserved.
