# Kraken Inquiry Pilot 1.0

1. **Originating intent** — Implement the first complete Mission Bus vertical slice from GLUE-01 through GLUE-06: one evidence-bounded inquiry, durable record, explicit human judgment, and visible projection.

2. **Verified starting state** — FleetCore live snapshot exposes the active K-1/KRAKEN watch context and stable event sequences. Shared mission/evidence/artifact contracts, append-only Mission Record design, component adapter inventory, coordinator lifecycle, review inbox, and registry/projection designs exist under `docs/architecture/`. Agent Ops is already public and reads FleetCore plus captain memory. Live model-provider credentials remain blocked (`HEART-01`), while Track B explicitly permits a stub graph.

3. **Objective / problem** — A Lieutenant must be able to open one live page and see how a question about K-1 moved from verified FleetCore evidence through competing interpretations to an explicit human decision, with every boundary visible and no interpretation written back as FleetCore truth.

4. **Scope and exclusions**

   Scope:
   - Add `tools/mission-bus/`, a standard-library Python CLI/package.
   - Implement the SQLite Mission Record at `data/mission-record/mission-record.sqlite3` per GLUE-02.
   - Implement coordinator commands `create`, `execute`, `inspect`, `review`, `cancel`, and `resume` for this fixed pilot plan.
   - Implement a read-only FleetCore adapter and deterministic, visibly labeled stub cognition adapter.
   - Implement review decision persistence; V0.1 may use CLI review, but the public page must show the exact decision and authority.
   - Build `web/data/mission-artifacts.json` and `web/data/mission-ops.json` atomically.
   - Extend source and live Agent Ops with an obvious `NEW · Mission Inquiry` panel linking evidence, competing findings, review state, and result.

   Exclusions:
   - No FleetCore commands or schema changes.
   - No daemon, message broker, second database, replication, or service restart.
   - No live-model requirement; no hidden claim that stub output is live.
   - No generalized World Intake UI rewrite, Bridge/Radio projection, Chronicle export, legend generation, or asset generation.
   - No use of QUacken as an active mission; it remains archived evidence.

5. **Constraints / authority**

   - FleetCore is read-only for this packet. Tests must fail if the tool attempts `POST /command`.
   - Stub cognition artifacts are `generated-candidate`, `data.mode: stub`, never `verified-state`.
   - Only a supplied `human-command` review decision may complete the inquiry.
   - The recommendation may say evidence is insufficient; it may not infer hostility from unknown identity/approach alone.
   - Mission Record rows are append-only and corrections/revisions supersede rather than overwrite.
   - Existing Radio/NPR dirty or generated files are outside this packet and must not be committed with it.

6. **Acceptance criteria**

   1. `create` records `mission.kraken-inquiry-001` with objective: “What does the verified evidence justify about contact K-1?”
   2. `execute` reads the real live FleetCore snapshot and records at least one `verified-state` `EvidenceRef` with a stable FleetCore locator/cursor plus observed time.
   3. Stub cognition records at least three competing artifacts: non-hostile/unknown, surveillance-risk, and potential-threat hypotheses; each cites the same evidence and states counterevidence/unknowns.
   4. A verifier artifact recommends a proportionate posture (continue passive observation / maintain separation / escalate only on new evidence) and is `review-required`.
   5. Before review, `inspect` returns `review-required`; repeated execution cannot auto-complete it.
   6. CLI review supports accept, reject, and edit-as-new-revision with reviewer ID, `human-command` authority, reason, revision check, and idempotent decision ID.
   7. Accepted review completes the inquiry but emits zero FleetCore command receipts and changes no FleetCore snapshot fields.
   8. SQLite triggers reject update/delete of Mission Record events; restart/reopen folds to the same state.
   9. Duplicate identical event/artifact/decision IDs are idempotent; unequal content under the same ID fails.
   10. Registry/projection rebuild is deterministic, exposes source cursor/time, excludes non-public artifacts, and marks missing/hash-mismatched files unavailable/integrity-failed.
   11. Agent Ops visibly shows `NEW · Mission Inquiry`, the original question, current lifecycle state, Verified Evidence, Competing Findings, Human Decision, and “No FleetCore mutation” statement.
   12. The panel is reachable by clicking from `https://cameronlampley.com/` through the existing Agent Operations card and verified at `https://cameronlampley.com/toys/agent-ops/`.

7. **Tests / rollback**

   Tests:
   - Unit tests for all shared schema/state validations used by the implementation.
   - Mission Record immutability, ordering, restart, correction, idempotency, and terminal-state tests.
   - Coordinator pause/cancel/resume, expired attempt/receipt, and review-required gate tests.
   - FleetCore adapter fixture plus live read-only test; snapshot hash/selected fields equal before and after pilot.
   - Projection determinism/privacy/integrity tests.
   - `node --check` for Agent Ops; source/live drift check.
   - Live HTTPS checks for page marker and projection JSON; visual browser check that all six named sections are visible without devtools.

   Rollback:
   - Revert implementation commit to remove tool/UI/projection.
   - Preserve the pilot SQLite file under `archive/missions/kraken-inquiry-001/` as execution evidence; do not delete recorded history.
   - No FleetCore rollback is required because the packet must not mutate FleetCore.

8. **Assigned actor** — Codex, authorized by the Lieutenant on 2026-07-16. One actor owns the packet; other sessions must not edit its files without handoff. No privileged actor is required.

9. **Evidence and completion state** — Verified complete and recorded. The live read-only inquiry recorded one FleetCore evidence reference, three stub-labeled competing findings, a review-required recommendation, and the Lieutenant-authorized human-command acceptance; the Mission Record reached `completed` at sequence 10 with no command receipt. Two lifecycle/immutability tests pass; Agent Ops JavaScript syntax and source/live drift checks pass. Live HTTPS exposes all six required markers and `/data/mission-ops.json` reports `completed`, three findings, and `accept`. Required design evidence:
   - `docs/architecture/mission-evidence-contracts-v0.1.md`
   - `docs/architecture/mission-record-v0.1.md`
   - `docs/reports/2026-07-16-component-adapter-inventory.md`
   - `docs/architecture/mission-coordinator-lifecycle-v0.1.md`
   - `docs/architecture/human-review-inbox-v0.1.md`
   - `docs/architecture/artifact-registry-projections-v0.1.md`
