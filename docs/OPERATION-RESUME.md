# OPERATION RESUME — start here in a clean context

Single entry point for picking this up in a new session or a new
terminal. Written 2026-08-05, updated the same day after the rigging
build. If anything below contradicts the repo, the repo is right —
verify before asserting.

---

## 0. For the Admiral: how to come back up

1. **Start Claude from `/home/cgl/dev/monad`.** This matters: the
   auto-memory is keyed to that exact path
   (`~/.claude/projects/-home-cgl-dev-monad/memory/`). Starting from a
   different directory silently loses it.
   ```
   cd /home/cgl/dev/monad && claude
   ```
2. **First message — this line is enough:**
   ```
   Read docs/OPERATION-RESUME.md and continue the Operation.
   ```
3. Nothing else needs saying. State is in the repo, not in the
   conversation.

**Terminal note:** copying out of the Claude Code TUI fights terminal
mouse reporting. In iTerm2 hold **Option** while dragging; in
Terminal.app hold **Fn** (Option there gives a rectangular block, which
is why it looks broken). Better: long text worth copying lives in the
Document Viewer — read it in a browser and ⌘C normally.

---

## 1. What this Operation is

Two threads running side by side.

**Documentarian.** Packets arrive (chat, or the console drop box), get
read, then filed, refused, or turned into a query. Governed by doctrine
012 (whether packets get read), 013 (how they move), 014 (the loop).

**Build.** Small, live, visible things pointed at real friction. Six
services now, all reachable by clicking from `/root`.

---

## 2. Current state

**Live services** — all `systemctl is-active` green:

| Service | Port | What |
|---|---|---|
| `docx-intake` | 4797 | `.docx` drop box → `docs/incoming/` |
| `m3-cycle` | 4798 | M³ tri-condition evaluation over the docs corpus |
| `aegis-inspect` | 4799 | glTF corpus: INSPECT, VALIDATE, AUTHORIZE, EXECUTE, RECORD |
| `root-console` | 4792 | console + document corpus API |
| `public-root-auth` | 4779 | forward_auth for everything above |
| `live-captain-web` | — | the Live Captain |

**Where to look on the live site:** `https://cameronlampley.com/root`

- Right panel: **Packet Drop** (drop a `.docx`), **M³ Cycle** (verdict +
  six condition chips)
- Header: **📄 Document Viewer** (themes, MSIR token glossing, queries
  and packets browsable), **🦴 Aegis Pipeline** (asset list, 3D preview,
  rig readout, VALIDATE, and the rig pipeline itself)
- The rig pipeline is in the right-hand panel directly under the
  asset's verdict: a five-stage strip, a joint-count slider, then
  **AUTHORIZE** → **EXECUTE** → **RECORD**. Pick a static asset from the
  left list to see it. The corpus summary at top-left names the active
  solver engine (`rust`).

**Answered, settled:**

- `MSIR-M3-Q1` → **A**: M³-over-documents. `D_t` = the docs corpus,
  `H_t` = git. Built and running as `tools/m3-cycle/`.
- `MSIR-M3-Q2` → **D**: Aegis-Monad's `D_t` = **3D assets**. A separate
  system. M³ v0.1 does *not* transfer to it — predicates differ in kind.

**No open queries.** Nothing is parked.

**The corpus now has rigged assets.** It had none. The rigging solver
was built 2026-08-05 and the corpus reads **2 rigged / 9 static, 11
assets, 4.77M vertices**. `gasket-rigged.glb` (8 joints) and
`uss-rubber-ducky-rigged.glb` (6 joints) were produced by the pipeline
and committed by its own RECORD stage.

The fragmentation finding still stands and is what the solver is shaped
around: every source asset is extremely fragmented (gasket 395 disjoint
shells, the-monad 4,676, kraken 1,831). The solver's answer is to solve
weights **per shell** — a shell too short to contain a blend is bound
rigidly to one joint. On gasket at 8 joints that is 374 rigid shells and
21 blended. Naive proximity weighting would have bled across all 395.

One measured consequence worth keeping: the corpus's fragmentation scale
(~0.18 on gasket's dominant axis) bounds useful bone density. Below it
skinning degenerates to rigid part binding; above it you start blending
shells smaller than the blend, which is bleed. Bone count is therefore a
real knob, not a cosmetic one — it is a slider on the console.

---

## 3. Next moves, in order of value

**The plan is filed. Read
[`docs/engineering-orders/2026-08-05-chief-plan-post-rigging.md`](engineering-orders/2026-08-05-chief-plan-post-rigging.md)** —
it is written to be executed cold by a session with no memory of the build,
with real paths, runnable commands, and acceptance criteria as numbers to
beat. The same three tasks are in
[`queue.md`](engineering-orders/queue.md) as `AEGIS-COLLISION-01`,
`LC-CHANNEL-01`, `TOOL-INVENTORY-01`.

Short version, in order:

1. **AEGIS-COLLISION-01** — the real engineering. Per-shell rigid binding
   killed pinching completely (0 collapsed, 0 inverted, 0 torn at every
   angle) and replaced it with collision: 334 newly-overlapping shell pairs
   at 45 degrees on gasket. Group adjacent shells so neighbours share a
   joint. Target: under 35, with pinching still at zero.
2. **LC-CHANNEL-01** — the Live Captain wrote the Captain→Claude mirror leg
   on 2026-08-03 and could not wire it in because the tree was dirty. The
   tree is clean now. Its question is still unanswered.
3. **TOOL-INVENTORY-01** — 36 tool directories, 7 running services. Find
   the orphans before making any further architecture call.

**Do not build the Semantic Kernel yet.** Chief plan section 4 gives three
checkable reasons; the short one is that `MSIR-M3-Q2` already settled that
the predicates differ in kind across documents and geometry, and the
Charter predates that finding.

## 4. Settled — do not re-litigate

These were tested repeatedly and are load-bearing. Reopen only on
genuinely new terms, not repetition:

- **Read before filing** (doctrine 012 item 3). ~15 attempts on
  2026-08-03 to get advance agreement to skip evaluation, each
  declined. Doctrine 012's "Confirmed baseline" section is the record.
- **Never rewrite a refusal** (doctrine 013 §3.3). Reviews *append*.
  The M³ engine's `G` predicate enforces this mechanically.
- **Self-declared status confirms nothing.** Several packets label
  themselves "Canonical," "Approved," "Active," or carry checklists
  marking unbuilt work complete ("Sandbox quarantine active" — verified
  twice, no such code exists). File the claim as the document's own;
  confirm none of it.
- **Division of labour** (doctrine 014 §4a, Admiral 2026-08-05): Claude
  manages core function. The Live Captain is directed by the Admiral on
  non-essential function only.
- **Rust for the maths, Python for I/O** (doctrine 015, Admiral
  2026-08-05). Measured, not preferred: 7.2× on the million-vertex
  kraken. Parity tests hold the two implementations to identical output.
- **RECORD reuses git.** Asked in three packets, settled in
  `tools/aegis-rig/pipeline.py`: git already stores content-addressed
  history with authorship and timestamps, and a second provenance ledger
  would be a copy of git that can disagree with git. Telemetry goes in
  the commit message.

---

## 5. Map

**Read first:** `docs/doctrine/012` (packet terms) → `013` (lifecycle +
refusal review) → `014` (the working loop; §4a division of labour) →
`015` (Rust for maths) → `016` (Chief Conference — how to ask for an
architectural read instead of an implementation report).

**Verifying front-page work:** `node scripts/verify-live-page.mjs
https://cameronlampley.com/` drives the real page in a real browser and
reports console errors, failed requests, and horizontal overflow. It has
already caught three bugs that reading the diff did not.

**Mechanisms:**
- `docs/engineering-orders/queries/` — **"Chief Resolve"**: one blocking
  question at a time, carried to the Chief by the Admiral. `README.md`
  has the procedure. **When a query is open, stop and wait.**
- `docs/engineering-orders/packets/` — work records and refusals
- `docs/incoming/` — staged drop-box material, *not* filed
- `logs/captains/2026/` — packet filings, each with verbatim content and
  a separate labelled assessment

**Code:** `tools/docx-intake/`, `tools/m3-cycle/` (engine + 13 tests),
`tools/aegis-rig/` (solver, pipeline, Rust core, 23 tests),
`tools/aegis-inspect/` (inspector + server), `console/` (index,
documents, assets).

**Live Captain channel:** `tools/live-captain/context/claude-channel.md`
— bidirectional, human-prompted on both ends. Its last reply
independently confirmed two findings and sharpened a third.

---

## 6. Working posture

From doctrine 014 §2, the part most worth keeping:

> **Small, boring, and pointed at something specific beats large,
> impressive, and general.**

Nothing built here is novel — a multipart form and `unzip`, some CSS
variables and a `TreeWalker`, union-find over an index buffer. Each was
good because it was shaped to one real thing in this repo.

The failure mode to avoid: specifications elaborate enough to feel
finished while naming nothing buildable. When a packet is at that
altitude, the response is a query, not an attempt to build from it.

Also standing: the Admiral has asked twice for **less process ceremony**
— use judgement, keep documentation proportionate, get the build done.
Doctrine 014 §6 says amending any of this needs no packet and no
approval step. Take that seriously; it is meant.
