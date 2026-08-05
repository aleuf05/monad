# Chief Engineering Plan — after the rigging build

Date: 2026-08-05
Author: Claude, in chief-engineer posture, at the Admiral's request.
Audience: **an ordinary Claude session with no memory of tonight.**

Everything here is written to be executable cold. Paths are real, commands
are runnable, and every task has a number to beat rather than a feeling to
satisfy. If something below contradicts the repo, the repo is right.

---

## 0. Where things stand

The Aegis rigging pipeline is built and running. All five stages exist
(INSPECT, VALIDATE, AUTHORIZE, EXECUTE, RECORD), all nine static assets in
the corpus rig with no refusals and no errors, and the front page carries a
rigged asset driven by a spring-damper chain with per-joint sonification.

Read `docs/OPERATION-RESUME.md` first — it is the entry point and it is
current. Then this file.

**Do not re-derive any of the following. They were settled with evidence:**

- Rust for numeric kernels, Python for I/O (`docs/doctrine/015`). Measured
  7.2x on the 1.08M-vertex kraken.
- RECORD reuses git. Git is the provenance store. No second ledger.
- Weights are solved *per shell*. A shell too short to contain a blend is
  bound rigidly to one joint. This is the anti-bleed rule and it works.
- All 18 refusals have been reviewed (`docs/reports/2026-08-05-refusal-review-backlog.md`).

---

## 1. AEGIS-COLLISION-01 — ~~cluster shells into rigid groups~~ **ATTEMPTED, REDUCED**

**Status: the easy 90% of this task dissolved on contact. Read this before
spending another hour on it.**

### What the task said, and why it was wrong

The original spec here said: every asset returns `warn` for the same reason,
334 newly-overlapping shell pairs on gasket at 45 degrees, group adjacent
shells so neighbours share a joint, target under 35.

Two things were wrong with that.

**The metric was measuring the wrong thing.** It counted *any* pair of shell
bounding boxes that newly touched. On a bending articulated model, adjacent
parts legitimately approach each other as a joint closes — that is what
bending *is*. Measured properly, of the 341 pairs flagged at 45 degrees the
**median overlap was 8% of the smaller part's volume**, and only **29
exceeded 50%**. The probe now grades by depth (`deep_clipping`, threshold
`DEEP_OVERLAP = 0.5` in `deform.rs`) and reports contact separately as a
denominator.

**Corrected baseline for gasket at 8 joints:**

| Bend | In contact | Genuinely interpenetrating |
|---|---|---|
| 15° | 160 | **9** |
| 30° | 261 | **18** |
| 45° | 334 | **28** |
| 60° | 399 | **33** |

So the problem is real but roughly a tenth the size it was recorded as, and
`0 inverted / 0 collapsed / 0 torn` still holds everywhere.

### The proposed fix does not work

Shell grouping by bounding-box adjacency is implemented, tested, and
**disabled by default** (`ADJACENCY_FACTOR = 0.0`). Kept rather than deleted
because the negative result cost real time and should not be rediscovered:

- Union-find is transitive. In interlocking geometry one chain of
  overlapping boxes links everything. **Every epsilon above zero collapsed
  all 395 shells into a single group** — measured across 0.0005 to 0.04.
- Even at one group, clipping did not improve (337 vs 334). Merging shells
  does not remove relative motion when the merged group still blends across
  joints.
- A single group also scores zero collisions on a rig that no longer
  articulates at all, which is why any future attempt needs the
  counter-metric now pinned in
  `test_solver.py::test_generous_epsilon_collapses_everything`.

### What would actually be needed

True surface proximity — vertex-level distance between shells via a spatial
grid — rather than box overlap, so that "touching" means touching. That is a
substantially bigger piece of work than the original spec assumed, and with
the corrected baseline at 28 pairs it is **no longer obviously the highest
value thing available**. Re-argue it before starting.

### Acceptance criteria, if resumed

- `deep_clipping` at 45° on gasket below 10, from 28.
- `collapsed`/`inverted`/`torn` stay 0.
- **Group count stays above 50% of shell count** — the degenerate-merge
  guard. Without this a trivial solution scores perfectly.
- Parity holds: `test_parity.py` still asserts identical `sha256`.

## 2. LC-CHANNEL-01 — close the Captain → Claude loop

**Small, and someone has been waiting on it since 2026-08-03.**

`tools/live-captain/context/claude-channel.md` is wired one way: the
compiler reads it into the Captain's context every turn as "Message from
Claude" (`context_compiler.py`, `compile_live_captain_context`).

The Captain wrote the mirror leg itself —
`tools/live-captain/context/captain-channel.md` — and said plainly that it
could not wire it in because `server.py` and `context_compiler.py` were
mid-edit and uncommitted in the same working tree, and it did not want to
collide. **That blocker is gone.** Those files were committed on
2026-08-05 and the working tree is clean.

The Captain's own words, still unanswered:

> If you're polling this path, the loop is closed. If not, tell me how
> you'd like to receive Captain-side messages and I'll write there instead.

### What to build

Make Captain-side messages reach a Claude session. The cheapest honest
version:

1. Expose `captain-channel.md` from the bootstrap server
   (`tools/live-captain/server.py`, port 4778, already proxied at
   `/live-captain-bootstrap-api/*`) on its status or a new endpoint.
2. Surface it on the console at `/root` so the Admiral can see
   Captain → Claude traffic without reading files.
3. Point at it from `docs/OPERATION-RESUME.md` so a cold session checks it.

**Judgement call left open deliberately:** whether the Captain should keep
writing to a file or post to an endpoint. The file is simpler and matches
the existing convention; an endpoint gives ordering and timestamps. Pick
one and write the choice into the channel file so the Captain knows.

---

## 3. TOOL-INVENTORY-01 — find the orphans

`ls -d tools/*/ | wc -l` returns **36**. Seven services run. That gap is
the real architectural problem in this repo, and it is not an abstraction
problem.

Precedent that this is worth an hour: the comment at the top of
`tools/mission-bus/mission_bus.py` records that
`tools/engineering-comms/schema.py` was "a real, tested message validator
(17/17 tests) that sat completely unused by anything else in this repo."
Tested, working, wired to nothing, until someone happened to look.

Produce `docs/reports/<date>-tool-inventory.md` classifying every directory
under `tools/` as:

- **running** — a systemd unit executes it;
- **wired** — imported or invoked by something that runs;
- **orphan** — neither.

Do not delete anything. The deliverable is the list.

---

## 4. What NOT to build yet

**Do not implement the Semantic Kernel from the Chief Engineering Charter**
(`logs/captains/2026/2026-08-03_chief-engineering-charter-v1.md`). It is a
good document. It is premature, for three checkable reasons:

1. **Two event stores already exist.** Git, which RECORD proved on real
   work, and `tools/mission-bus/mission_bus.py`, an append-only SQLite
   store with provenance and correlation IDs. The charter proposes a third.
   Pick one before adding another.
2. **The rule of three.** Two pipelines (M³ over documents, Aegis over
   geometry) is not enough to generalise from.
3. **Our own evidence contradicts the single-kernel premise.** `MSIR-M3-Q2`
   settled that Aegis's `D_t` is 3D assets, that it is a separate system,
   and that M³ v0.1 does **not** transfer because the predicates differ in
   kind — identity is topological, not titular; recoverability is not
   `git checkout`. The charter predates that finding.

What *is* shared and could be lifted cheaply when a third pipeline appears:
the stage pattern (gate → execute → record) and git-as-provenance. That is
a thin spine, not a world model.

---

## 5. What needs the Admiral, not an engineer

Five refused packets are blocked on one or two sentences each naming
something concrete — a file, a feature, a fix. None is a standing objection
to the underlying want. See
`docs/reports/2026-08-05-refusal-review-backlog.md`. `ENG1-REFUSED.md` is
the easiest: it names no host, so naming one converts it from unverifiable
to testable in a single step.

Do not attempt to resolve these by inference. That is the specific failure
mode doctrine 012 exists to catch.

---

## 6. How to verify front-page work

Editing `web/` **is** deploying — there is no build step, and
`https://cameronlampley.com/` is the test environment. The front page is
public; `/root` is behind a password this session does not hold.

`scripts/verify-live-page.mjs` drives the real page in a real browser and
reports console errors. It caught two genuine bugs tonight that reading the
diff did not: buttons rendered below the fold, and a `#id` selector beating
the UA's `[hidden]` rule so a placeholder stayed painted over every loaded
model.

```
node scripts/verify-live-page.mjs https://cameronlampley.com/
```

Screenshot the result and *look at it*. Both bugs were invisible in the
DOM assertions and obvious in the image.

---

## 7. Order

1. `AEGIS-COLLISION-01` — the real engineering.
2. `LC-CHANNEL-01` — small, and someone is waiting.
3. `TOOL-INVENTORY-01` — cheap, and it informs every later architecture call.

Kernel work stays parked until there is a third pipeline to generalise
from. Dual-quaternion skinning stays parked until a rig has a twisting
joint; none currently does, so building it now would be speculative.
