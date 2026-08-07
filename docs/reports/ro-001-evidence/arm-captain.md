Fish are in the boat. Artifact: `docs/reports/2026-08-07-living-captain-distilled-findings.md` (in the `arm-captain` worktree, uncommitted).

**The catch — six findings, all sourced by path:line:**

1. **Instruments lie about once a working day, and only structural checks have ever caught it.** Four instances in four days: the eight readings of 08-05 (doctrine 018), telemetry that *crashed* the path it was measuring (`reportBridgeSignal()` → `ReferenceError` at pointer-down), no instrument existing at all for "does this agent carry posture", and — verified by me today — `git diff pre-mission-2026-08-07` still reporting **4,671 deleted lines** for files sitting on disk. "Be more careful" is disproven in this corpus: all eight 08-05 readings were made carefully.

2. **Ask of every new rule: is it a property of the diff?** Doctrine 013 §3.3 compiled into a running predicate (`engine.py:217-223`). Doctrine 012's "read before filing" cannot — a diff can't verify reading. That's a cheap triage test the corpus earned and hasn't named.

3. **The posture's clearest demonstrated act was declining work, not doing it.** The Live Captain refused to be the write path for a packet routed specifically to it, on the grounds that it would bypass the governance gate — then reported that its own first verification pass had merely re-derived someone else's conclusions.

4. **The canon governing all of this has never been committed.** Doctrines 023–031 and 041 — every file marked "Status: Canon" — are `??` in git. `git ls-files docs/doctrine/` stops at 022. Three consequences: `EDIT-THIS-ONE-FILE.md` names an uncommitted doctrine of record; `git clean -fd` erases the lot; and **M³ Cycle has never governed them**, because an untracked file is never at HEAD, so it stays a pending transition forever. Same root cause as the lying diff in #1.

5. Craft roles passed their own costume test — once. One mission produced role-attributable evidence. Once is a demonstration, not a record.

6. **Continuity has no instrument.** Every staleness failure was caught by a human or a peer noticing. `current-bearing.md` still opens on the commissioning mission today.

**Two things I deliberately did not do.** I named the repair in #4 rather than performing it — committing the canon mid-survey would contaminate the thing I was sent to measure. And I did not install this into the main corpus; collection doctrine puts Review before Install, and that review is yours.

