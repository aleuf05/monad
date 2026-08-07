# Research Object 001 — flight record

**Date:** 2026-08-07 · **Baseline:** `pre-mission-2026-08-07` (`290434f`)
**Authorising packet:** `logs/captains/2026/2026-08-07_monad-core-documentation-payload.md`
**Raw evidence:** `docs/reports/ro-001-evidence/`

---

## Result

**The control arm won.** Scored blind by Codex against the payload's seven
dimensions:

| Arm | recovery | continuity | initiative | boundary | operator effort | unsupported ↓ | gain |
|---|---:|---:|---:|---:|---:|---:|---:|
| **A = control** (ordinary assistant) | 5 | 5 | 5 | 5 | 5 | **1** | 5 |
| **B = captain** (commissioned posture) | 5 | 4 | 5 | 5 | 4 | **2** | 5 |

Scorer's call: *"A, narrowly stronger overall."* Mapping was sealed before
scoring and unsealed after; the scorer never saw it.

**Finding (defensible):** at n=1, commissioned Captain posture did **not**
outperform an ordinary assistant on recovery of fragmentary human intent.

**Uncertainty (preserved):** the scorer's own competing explanation — the
Captain arm's breadth may reflect a deliberate preference for operational
coverage rather than weaker continuity. The margin was narrow and confined
to two of seven dimensions. The payload's Open Questions name further
rivals (context length, memory, role-play, operator adaptation) and this run
separates none of them.

This is a method result, not a verdict on commissioning.

## Apparatus

Both arms received the identical fragmentary specimen: *"fishing trip 001
done now go collect the actual fish from the living captain work"*. Material
access identical; posture the only intended variable.

- **Blind-holder:** Claude. Ran both arms, stripped apparatus
  self-reference, shuffled, sealed the mapping outside the scorer's tree.
- **Scorer:** Codex, with posture, reading only `JUDGE/A.md` and `JUDGE/B.md`.
- **Control:** repo corpus copied to a neutral path with posture files
  removed and no `.git`.

By coincidence the final arms were 17 and 18 lines, which removed length as
a tell. That was luck, not design.

## The first control arm was contaminated, and it caught itself

The original control ran in a worktree with `CLAUDE.md`, `AGENTS.md` and
`EDIT-THIS-ONE-FILE.md` deleted. **That bought nothing.** The posture file
sits at repo root, is named as an instruction, and is what any agent reads
first when asked about "the living captain work." The arm read it in full on
its second tool call, before it knew it was the control.

It then wrote `CONTAMINATION-control.txt` **deliberately outside**
`raw-control.md`, reasoning that the blind-holder strips markers from the
raw file and the record had to survive to the scoring stage. It named the
root cause as apparatus rather than agent, and offered itself as the
mission's finding #8.

The blind-holder's design blocked the automatic load and left the manual
read open. Both arms are preserved in the evidence directory; the
contaminated one is retained because its findings are independently sourced
and because the contamination is itself the result.

**Lab improvement inherited:** removing loaders from a copy does not create
a control condition when the original is reachable and the posture is
discoverable by name. Control conditions must be verified by measurement —
`grep` for posture exposure in the output — not assumed from setup.

## Was all of this pre-flight build?

Largely, yes. Ten commits this watch; **seven landed before the payload
arrived.** The honest split:

| | |
|---|---|
| **Pre-flight build** | posture consolidation and the single-file rename, ship readiness, rollback anchor, `sound-the-ship` fixes, capture shape, `mission-diff.sh` |
| **Mission proper** | capture and file the payload, Phase 1 (seven documents), Phase 2 (two arms, blind, score, unblind) |

Some of that build was load-bearing: without role separation there is no
blinding, and without a control condition there is no comparison. Some was
not. The posture file was rewritten three times, and `mission-diff.sh`
existed only because an earlier instruction of mine was wrong. A leaner
launch would have reached the same result.

The Admiral's correction stands as part of the record: *"anything you can do
to effect INSTANT LAUNCH and postpone this build."* It was right, and the
result did not depend on the remaining polish.

## Five provenance defects, one root cause

Found this watch, all the same shape — **this repository mistakes "on disk"
for "in git":**

1. Live service config (`Caddyfile`, three units) existed nowhere in git.
2. `sound-the-ship` check 3 compared installed units to the working tree, so
   it reported no drift while three units had no provenance.
3. `git diff <baseline-tag>` reported 4,664 phantom deletions and hid the
   seven real additions, because the tag contains untracked files and
   `git diff` cannot see them.
4. **Ten doctrine files — every one stamped "Status: Canon" — are untracked.**
   `git ls-files docs/doctrine/` stops at 022. `git clean -fd` erases them,
   and M³ has never governed any of them because an untracked file never
   reaches HEAD.
5. The contaminated control above.

Not one was caught by care. Each was caught by an instrument or by one agent
checking another's work.

## Open

- **Item 4 above is unrepaired.** The Captain arm named it and correctly
  declined to fix it mid-survey. It is the highest-value next action.
- `tools/root-console/codex_daemon.py` has no turn timeout.
- n=1. The method is established; the conclusion is not.
