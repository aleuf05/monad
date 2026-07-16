# Radio Console Source Sync 1.0

1. **Originating intent** — Architecture Engine inventory and `tools/check-toy-drift.py` both identify the live Radio Console as containing logic absent from its source counterpart.
2. **Verified starting state** — A byte-level comparison reports only `toys/radio-console/app.js` versus `web/toys/radio-console/app.js` as unexpected public-toy drift. The live file is the deployed, working copy.
3. **Objective / problem** — Restore the live Radio Console application logic to the canonical `toys/` source tree.
4. **Scope and exclusions** — Replace only `toys/radio-console/app.js` with the live file and record the work. Do not change the live page, NPR data, scheduling, services, or unrelated dirty files.
5. **Constraints / authority** — Non-privileged repository work authorized by the Lieutenant's 2026-07-16 instruction to take available work. Preserve current production behavior exactly.
6. **Acceptance criteria** — Source and live Radio Console application files are byte-identical; JavaScript syntax passes; the repository drift checker exits zero.
7. **Tests / rollback** — Run `node --check toys/radio-console/app.js` and `python3 tools/check-toy-drift.py`. Roll back by reverting the implementation commit.
8. **Assigned actor** — Codex.
9. **Evidence and completion state** — Verified complete and recorded. `node --check toys/radio-console/app.js` passed; `python3 tools/check-toy-drift.py` reported that public toy source and live runtime files are in sync. The implementation commit contains only the restored source file and this packet.
