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

## 1. AEGIS-COLLISION-01 — cluster shells into rigid groups

**This is the highest-value work available. Do it first.**

### The problem, stated as a number

Every one of the nine assets returns `warn` from the deformation probe, all
for the identical reason. Per-shell rigid binding removed pinching
completely — 0 collapsed, 0 inverted, 0 torn faces at every angle tested —
but it replaced that failure with collision. Baseline on `gasket.glb` at 8
joints:

| Bend | Newly overlapping shell pairs |
|---|---|
| 15° | 160 |
| 30° | 261 |
| 45° | 334 |
| 60° | 399 |

Reproduce with:

```
python3 tools/aegis-rig/deform.py web/assets/rigged/gasket-rigged.glb
```

### Why it happens

`solve_weights` binds each shell independently to whichever joint is
nearest its centroid. Two shells that physically touch can therefore land
on *different* joints, and when those joints rotate apart the two shells
move relative to each other and interpenetrate. Nothing in the solver knows
they were neighbours.

### The fix

Group spatially-adjacent shells and bind each **group** to one joint, so
neighbouring parts travel together and have no relative motion to collide
with.

1. Compute each shell's AABB (the Rust core already does this in
   `deform.rs::shell_boxes` — lift or mirror it).
2. Build shell adjacency: shells whose AABBs overlap, or are within a small
   epsilon of each other, are neighbours. Epsilon should scale with the
   asset — a fraction of `bone_span` is a reasonable starting point.
3. Union-find over that adjacency to get rigid **groups**. The same
   `connected_components` idea, one level up.
4. Bind by group: a group whose axial span is under the rigid threshold
   binds entirely to the joint nearest the *group* centroid. Groups that
   straddle joints blend as shells do today.

### Acceptance criteria

- Clipping pairs at 45° on `gasket.glb` drop to **under 35** (a 10x
  improvement on 334). Report the real number whatever it is.
- `collapsed`, `inverted`, and `torn` stay at **0** at every tested angle.
  Trading collision back for pinching is not a win.
- `weights_sum_to_one` still true, `max_weight_error` still ~1e-8.
- All 23 tests in `tools/aegis-rig/` still pass.

### Files

- `tools/aegis-rig/rust/src/main.rs` — `solve_weights`, the hot path.
- `tools/aegis-rig/solver.py` — `solve_weights`, the Python reference.
- `tools/aegis-rig/test_solver.py` — add a test that two touching shells
  land on the same joint.
- `tools/aegis-rig/test_parity.py` — parity must still hold.

**Doctrine 015 obligation:** if you change the Rust kernel you change the
Python reference too, and `test_parity.py` must still assert both produce
an identical `sha256`. That parity test is the only thing making a
second language safe to keep. Do not let it rot.

### Rebuild and re-run

```
cd tools/aegis-rig/rust && cargo build --release
python3 tools/aegis-rig/test_solver.py && python3 tools/aegis-rig/test_parity.py
python3 tools/aegis-rig/rig_corpus.py 8      # rewrites web/data/corpus-rig.json
```

---

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
