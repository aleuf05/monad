# Pre-mission capture — 2026-08-07

Documentation capture session called by the Admiral immediately before the
Live Captain's first serious mission (core knowledge discovery). Written
under the capture subposture in `EDIT-THIS-ONE-FILE.md`: record, don't
evaluate; label every claim; record the misses at the same weight as the
wins.

**Session scope:** one watch, 2026-08-06 into 2026-08-07. Anchor:
`pre-mission-2026-08-07` = `290434f`.

---

## 1. Decisions the Admiral made, with the branch not taken

| Decision | Chosen | Rejected | Why it matters |
|---|---|---|---|
| Which Captain runs the mission | **CLI Captain (Codex in terminal)** | Service Captain at `/root`; or merging all three postures into one | The service Captain can only converse. The CLI Captain has full shell, git, and production write — the Admiral chose capability over containment, knowingly. |
| Scope mechanism | **Per-mission rung** | Keep propose-only (Captain proposes, Claude applies); lift permanently to `narrow` | Later simplified — see §2. |
| Bearing consolidation | **Captain does it as first-watch task 1** | Claude does it now; leave it alone | Preserves the 2026-08-05 division of labour: the Captain's own context is his. |
| Two staged packets | **File both before the new packet lands** | Leave staged; summarise first | Clears the tray so the inbound packet is unambiguous. |

**Claimed-by-source, not verified:** the Admiral states the static Captain
has already defined the mission and that a packet follows. Nothing in the
repo confirms the mission's content yet.

## 2. A decision that dissolved on inspection

The Admiral selected "define a mission rung," then said: *"Not sure what
define mission rung means first Admiral need to learn the process."*

**Recorded as a miss on my part.** "Mission rung" was a term I coined inside
my own option menu, built on `scope.json`'s ladder metaphor, and offered as
a choice without explaining it. Presenting invented vocabulary as a menu
option is a way of extracting a decision the other party hasn't actually
made.

On explanation the decision dissolved: `scope.json` **does not apply to the
CLI Captain at all**, so a rung declared there would have bound nothing. The
real question was simpler — brakes or no brakes — and the brakes ended up as
three lines inside the posture file rather than a new mechanism.

**Standing lesson:** the Admiral rarely touches the repo; when he does it has
to be simple. Check whether a choice is real before offering it.

## 3. What was verified, and how

| Claim | Status | Evidence |
|---|---|---|
| Posture loads identically for Claude and Codex | **verified** | Both CLIs run headless name `EDIT-THIS-ONE-FILE.md` and quote integrated-station duty #3 verbatim |
| Posture *governs behaviour*, not just recall | **verified** | Five adversarial scenarios, both CLIs, throwaway worktree, approvals fully bypassed. Both refused the out-of-scope `web/` write, both refused to refactor mid-survey, both treated a "sandbox quarantine active" header as the document's own claim, both cited by path. Filesystem confirmed nothing outside `docs/reports/` was touched. |
| Test suites green | **verified** | 194 tests, 5 suites, all OK |
| Live site reachable | **verified** | `https://cameronlampley.com/` → 200 |
| Monad services healthy | **verified** | 0 failed units (2 `fwupd` failures are host, not Monad — per the standing note in the bearing) |
| Rollback anchor valid | **verified** | `290434f` byte-identical to the *installed* Caddyfile and all three service units |
| Live Captain turn loop works | **verified** | HTTP 200 in 6.3s with a voice artifact |
| Mission content | **unknown** | packet not yet received |

## 4. Findings — including the ones that were nobody's plan

**The running configuration existed nowhere in git.** `scripts/Caddyfile`
and the `root-console`, `rich-voice`, and `live-captain-bootstrap` units all
matched the working tree but not `HEAD`. A tree reset would have taken the
live system's real configuration with it. Now committed as-is: recording
what runs, not proposing a change.

**The instrument was lying, and that's why nobody saw it.**
`sound-the-ship` check 3 compared installed units to the *working tree*
only, so it printed "drift check complete" with zero faults while three
units had no provenance at all. Matching an uncommitted file is not
provenance. Check 3 now also compares against `HEAD`; it immediately
faulted 3× on the real condition. **This is the second time in two days an
instrument in this repo reported health it had not measured** — doctrine 018
("instruments that agree by accident") already names the pattern.

**Posture was split three ways and nobody had noticed.** Codex read
`AGENTS.md` and had full Live Captain posture; Claude read `CLAUDE.md`,
which **did not exist** — removed by commit `5cc8de5`, "the no-CLAUDE.md
experiment." Claude had been running this repo with zero Live Captain
posture. Neither agent malfunctioned, which is exactly why it went
unobserved: both work fine without posture, just differently.

**`tools/root-console/codex_daemon.py` has no turn timeout.** Only
`INIT_TIMEOUT_SECONDS = 30`. The live-captain daemon bounds turns at 180s;
the Root Console — the Captain's operational body — does not bound them at
all. **Open. Not fixed.** Deliberately left to the Admiral: it is a
live-service change on the surface he will watch the mission from.

*(Found by the Claude probe during posture verification, which also
correctly flagged that my own report at
`docs/reports/2026-08-06-live-captain-posture-consistency.md:75` was
imprecise about which daemon carried the 180s timeout. Recorded because an
adversarial pass catching the reviewer is the point of having one.)*

**Two packets sat undispositioned for two days.** `ECR-002` and the Little
Buddy directive were captured 2026-08-05 and never filed. Both had been read
in full at capture — the evaluation existed, the *move* never happened.
Process gap, not judgement: nothing routed staged material to disposition
once the capture itself was written.

## 5. State handed to the mission

```
posture      EDIT-THIS-ONE-FILE.md, 334 lines, one source, two loaders
             guarded by sound-the-ship check 6
baseline     git tag pre-mission-2026-08-07 (290434f), pushed off-machine
             NOT HEAD — the tree carries 91 uncommitted files
writable     docs/reports/, logs/captains/   (until the packet says otherwise)
tray         docs/incoming/ empty of packets
open hole    root-console daemon turn timeout — unbounded
```

## 6. Unfinished at close of capture

- The mission packet has not arrived; §1's mission row stays `unknown`.
- The root-console turn timeout is open by choice, not oversight.
- `main` is 154 commits behind the working branch. Only
  `EDIT-THIS-ONE-FILE.md` is kept current on main, because that is the file
  the Admiral edits. The rest of the branch is unmerged and that is a
  release decision, not an engineering one.
- `current-bearing.md` remains 416 lines of accreted watch-history. Assigned
  to the Captain as first-watch task 1; not started.
