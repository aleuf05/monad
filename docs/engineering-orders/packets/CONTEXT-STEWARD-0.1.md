# CONTEXT-STEWARD-0.1

1. **Originating intent** — During the Beastscape research voyage, the Admiral
   identified that long-running Captain sessions accumulate enough historical
   context to dilute the current course. The Admiral ordered a lightweight
   automated context-management capability before the next sprint.
2. **Verified starting state** — Durable project truth already lives across
   doctrine, research drafts, architecture notes, engineering packets, and
   source control. There is no dedicated current-context briefing, structured
   continuation state, archive of milestone handoffs, or one-command process
   for producing a fresh-thread launch packet. A repository-local tool cannot
   directly purge or replace the active product conversation unless the host
   exposes that control.
3. **Objective / problem** — Implement Context Steward v0: a small,
   repository-local checkpoint tool that compresses current working state into
   a concise human briefing and machine-readable continuation packet, making a
   fresh Captain thread cheap and reliable before context becomes unwieldy.
4. **Scope and exclusions** — Add a one-command, on-demand checkpoint workflow;
   `docs/context/current-brief.md`; `docs/context/current-state.json`; archived
   milestone briefs; a ready-to-paste continuation packet; size budgets and
   deterministic validation. Capture mission, active goal, vocabulary,
   architecture/live state, decisions, changed surfaces, verification,
   defects, next action, and deferred ideas. Exclude daemons, automatic thread
   deletion, ChatGPT/Codex UI automation, transcript scraping, token-accounting
   claims, autonomous canon promotion, and a second project truth store.
5. **Constraints / authority** — Existing repository documents remain
   authoritative; Context Steward is a compact projection and explicitly
   labels its source paths and generation time. It must distinguish established
   truth, active course, historical wake, and disposable repetition. It must
   never infer credentials, copy secrets, rewrite source documents, or claim
   that an active context was purged. No sudo, service, API spend, or human
   handoff is required for implementation.
6. **Acceptance criteria** — One documented command produces or refreshes:
   (a) a concise current brief readable in under five minutes,
   (b) valid structured JSON with schema/version and source references,
   (c) a self-contained fresh-thread continuation packet, and
   (d) an immutable timestamped milestone archive when explicitly requested.
   Re-running without source changes is semantically stable. Outputs enforce
   configured size ceilings and visibly report omissions rather than silently
   truncating required sections. A fixture test proves that secrets and
   superseded/completed chatter are excluded.
7. **Tests / rollback** — Unit-test schema validation, deterministic refresh,
   size-budget enforcement, archive creation, source citation, secret
   exclusion, and missing-section failure. Perform one real checkpoint against
   the current Beastscape course and manually verify that its continuation
   packet is sufficient to resume in a clean thread. Rollback removes the tool
   and `docs/context/` projection; authoritative source documents remain
   untouched.
8. **Assigned actor** — Captain / Codex, scheduled before the next engineering
   sprint.
9. **Evidence and completion state** — **Verified complete and recorded,
   2026-07-29.** `scripts/context-checkpoint` is the documented one-command
   workflow. It generated `docs/context/current-brief.md`,
   `current-state.json`, `continuation.md`, and the explicit immutable
   `archive/20260729-continuous-umap-passage-23b18b208b0dc869.md` checkpoint.
   `python3 -m unittest tools/context-steward/test_context_steward.py` passed
   five tests covering deterministic refresh, source citation, secret
   refusal, missing-section refusal, visible budget omissions, exclusion of
   historical/completed chatter from continuation prose, and idempotent
   archives. The real checkpoint totals 11,792 bytes across its three current
   outputs; JSON validation passed. Two consecutive refreshes had identical
   SHA-256 hashes for all three outputs. Captain manually reviewed the
   ready-to-paste continuation packet and confirmed that it states the
   Beastscape mission, current course, vocabulary, established live state,
   verification, defects, next action, deferred ideas, and authoritative
   source paths without claiming that conversation context was purged.
