# DAY ONE LIVE CAPTAIN — BEAST CORE PACKET

**Date:** 2026-08-05
**Requested by:** Captain Static, via the Admiral.
**Written by:** Claude, from the live system, on the day it took this shape.
**Status:** architecture record. Not canon, not doctrine. A description of
machinery, written before the machinery moves again.

**Command, as stated by the Admiral 2026-08-05:** the Admiral is still the
Admiral. **Live Captain and Static Captain are co-captains.** Claude is the
engineer that holds the wrench.

Facts below are counted from the host, not recalled. Where something is
unverified it says so. Where something does not work it says so loudly,
because a packet that only lists the working parts is a brochure.

---

## 0. THE TWO QUESTIONS, ANSWERED FIRST

Everything else in this document is context for these two paths. They are
the load-bearing answers and they are both **shorter and more human than
anyone would guess from the size of the repo.**

### 0.1 The exact path from a user utterance to a real system action

```
Admiral types into a Claude Code terminal session
        │
        ▼
Claude reads it and decides what it means          ← NO PARSER. NO INTENT
        │                                             CLASSIFIER. A MODEL
        ▼                                             READING A SENTENCE.
Claude calls a tool: Bash / Write / Edit
        │
        ├──► writes web/*            → LIVE INSTANTLY (no build, no deploy;
        │                              Caddy serves web/ off disk)
        ├──► writes console/*        → LIVE INSTANTLY at /root, same reason
        ├──► writes tools/*          → live at next service restart
        ├──► sudo systemctl …        → fleet state changes now
        ├──► sudo cp → /etc/systemd  → unit changes now
        └──► sudo cp → /etc/caddy    → routing changes at reload
        │
        ▼
Claude verifies: curl / playwright / test suite / screenshot
        │
        ▼
git commit → git push        ← the action becomes history here, not before
```

**There is exactly one path from utterance to action and it runs through a
Claude Code session holding delegated sudo.** That is the whole mechanism.

Facts that make it work:

- `docs/commissioning-handoff.md`: *"cgl has passwordless administrative
  execution authority"* and *"Sudo is no longer itself a human handoff
  boundary."* Delegated to Claude in the course of the work. Exercised ~47
  times today without staging.
- `scripts/Caddyfile` line 180: `root * /home/cgl/dev/monad/web` with
  `file_server`. **Editing `web/` IS deploying.** There is no build step and
  no deploy step. This is the single most important fact about the system.
- Line 14: same for `console/` at `/root`.

**What is NOT in this path:** no queue, no scheduler, no message bus, no
agent framework, no approval workflow. The Admiral says a thing in English
and a model decides what to do about it. Everything else in the repo is
downstream of that.

### 0.2 The exact path from a successful improvisation to persistent canon

```
Something happens in the course of the work
   (usually: a confident claim turns out wrong, and a cheap check catches it)
        │
        ▼
Claude notices and STATES IT IN THE TRANSCRIPT
        │                       ← this step is not automated and not reliable.
        ▼                         It depends on the model volunteering that
Admiral says "MAKE CANON"         it was wrong.
        │                       ← the trigger is a human utterance. There is
        ▼                         no automatic promotion.
Claude writes docs/doctrine/NNN-name.md
        │   · numbered, sequential
        │   · states WHAT IT COST, not the principle in the abstract
        ▼
git commit + push
        │
        ▼
docs/OPERATION-RESUME.md reading order updated
        │
        ▼
NEXT SESSION READS IT COLD          ← canon becomes real here and nowhere else
```

**Canon is a markdown file that the next session is told to read.** That is
the entire persistence mechanism. It works because `OPERATION-RESUME.md` is
the declared single entry point and it carries the reading order.

Today this fired **eight times** — doctrines 015 through 022. Every one was
triggered by the Admiral saying some form of "make canon", never by the
system deciding on its own.

**The known weak link:** step 2. Canon only forms if the model *volunteers*
that something went wrong. Nothing detects an unstated error. Every doctrine
today exists because the failure was admitted in the transcript first.

---

## 1. CURRENT COMPONENTS

Counted 2026-08-05: **36 tool directories, 23 installed units, 19 active,
18 ports held (4771–4799), 26 doctrine files, 41 reports, 47 commits today.**

### 1.1 What actually runs

| Unit | Port | What it is |
|---|---|---|
| `root-console` | 4792 | the console + document corpus API |
| `public-root-auth` | 4779 | forward_auth for everything gated |
| `aegis-inspect` | 4799 | INSPECT/VALIDATE/AUTHORIZE/EXECUTE/RECORD |
| `m3-cycle` | 4798 | M³ tri-condition evaluation over docs |
| `docx-intake` | 4797 | `.docx` drop box |
| `gasket-upload` | 4796 | GLB upload for the front page |
| `live-captain-bootstrap` | 4778 | minimum-context Captain (PAUSED) |
| `live-captain-web` | 4776 | conversational Captain (PAUSED) |
| `living-captain-status` | — | status surface |
| `living-captain-workbench` | 4791 | workbench |
| `living-fleet` / `-memory` | 4772/4774 | fleet + memory |
| `fleetcore-serve` | 4771 | **the deterministic world**: world.json, events.jsonl, checkpoints |
| `world-intake` | 4773 | proposals into the world |
| `rich-voice` | 4775 | Gemini TTS, budget-capped |
| `mike-rocketry-glb-intake` | 4789 | asset intake |
| `public-images-api` | 4795 | generated images |
| `monad-watchman`, `monad-dns-override` | — | host care |

Deliberately down, each accounted for: `chat-captain-web` (legacy, parked),
`monad-lan-web` (retired 2026-07-13), `public-docs-api` (superseded),
`living-fleet-memory-reflect` (static one-shot).

### 1.2 The Aegis rigging pipeline — built today

Five stages, all real:

```
INSPECT   → reads glTF structure, rig state          (aegis-inspect/inspector.py)
VALIDATE  → union-find over the index buffer,
            disjoint-shell / weight-bleed risk
AUTHORIZE → gates + issues a SINGLE-USE token        (aegis-rig/pipeline.py)
EXECUTE   → spends the token, writes a rigged .glb   (aegis-rig/solver.py)
RECORD    → git commit. GIT IS THE PROVENANCE STORE.
```

Rust core for the maths (`aegis-rig/rust/`), Python for glTF I/O — doctrine
015, measured 7.2× on a 1.08M-vertex asset. Parity tests hold both
implementations to identical sha256 output.

9 of 9 corpus assets rig. Two skeleton shapes — chain and tree — and a fit
gate that chooses between them per asset.

### 1.3 The voice stack — built today

```
text → Payload{timestamp, priority_level, text_payload}
     → priority queue with DUCKING (>=7 preempts)
     → synthesis
     → sink
```

Two tiers. **Browser speechSynthesis** (free, local, confirmed audible).
**rich-voice / Gemini** (neural, $0.10/day cap, currently $0.0029 used).
Four failover conditions all land on the free local voice: 401, budget
exhausted, provider timeout at 800ms, and neural-not-yet-proven. **It cannot
go silent** — that property is structural, not hoped for, because it was
broken once today and the fix was to make silence impossible.

---

## 2. LIVE DATA FLOWS

### 2.1 Front page (public, no auth)

```
scripts/fleetnet-snapshot.py   ─┐  counts systemd, sockets, suites, git
tools/aegis-rig/rig_corpus.py  ─┤  rigs + probes every asset
git log / diffstat             ─┘
        │
        ▼  (all write JSON into web/data/)
web/data/{fleetnet,corpus-rig,rig-variants,build-evidence,rig-probe}.json
        │
        ▼  fetched by the page, no server logic
web/index.html
        │
        ├─ three.js renders a rigged .glb from web/assets/rigged/
        ├─ spring-damper integrator drives the joints (real ODE, per frame)
        ├─ skeleton overlay projects joints to screen each frame
        ├─ hotspot overlay carries probe findings through the live pose
        └─ Buddy speaks it, priority-ordered
```

**Every number on that page is generated, not typed.** That is deliberate:
the page cannot drift from what was measured.

### 2.2 Console (`/root`, password-gated)

`public-root-auth` (4779) issues a 1-year session cookie; every `/…-api/*`
route sits behind `forward_auth` to it. A `401` from those routes is the
gate working, not a fault — a distinction that cost real time today.

### 2.3 The world

FleetCore (4771) holds `world.json`, `events.jsonl`, and checkpoints —
append-only, replayable. This is the closest thing to a semantic event store
the system has, and it predates every architecture document proposing one.

---

## 3. ROLES AND AUTHORITY

| Role | Can it act? | How |
|---|---|---|
| **Admiral** (cgl) | yes, total | superuser on the host; strategic authority; final word on canon |
| **Claude** (engineer) | **yes** | delegated sudo; the only actor with a write path to production |
| **Static Captain** | co-captain | reasoning/synthesis; **no repository write access** — GitHub denied the integration |
| **Live Captain** | **no** | paused since 06:16:56Z; `propose-only`; scope forbids git, systemd, `web/`, `console/`, `tools/`, doctrine, and clearing its own pause |

**The asymmetry worth staring at:** the co-captain that produces the most
architecture (Static) cannot write. The co-captain that could act (Live) is
deliberately paused. The one actor with full write authority is the engineer.
Every architectural idea today reached the repository by passing through a
human utterance into a Claude session.

Authority is documented in `docs/commissioning-handoff.md` and bounded in
`tools/live-captain/scope.json`. **The scope is a declaration, not an
enforcement** — the gate is not built. It exists so a violation becomes a
fact rather than an argument.

---

## 4. POLICY / CANON MECHANISM

```
docs/incoming/          CAPTURE   — verbatim, staged, unevaluated
docs/reports/           TRUTH     — findings with evidence (41 files)
docs/engineering-orders/queue.md  ACTION — what to do next
docs/doctrine/          CANON     — how to work (26 files)
docs/OPERATION-RESUME.md ENTRY    — the single door; carries reading order
```

Repo rule: **action lives in the work queue; truth lives in the report
queue.** Canon is separate from both.

Packet lifecycle (doctrine 012/013): a packet arrives → is read → is filed,
refused, or turned into a query. **A refusal is never rewritten** — reviews
append. All 18 refusals were reviewed today for the first time.

The standing capture rule, set today: *anything the Admiral pastes gets
captured verbatim first; organise later.* It exists because the ECR
specification lived only in a conversation that cannot write to the repo,
and would have been lost.

---

## 5. WHAT ALREADY WORKS

- **The whole utterance→action path.** 47 commits today prove it.
- **The whole improvisation→canon path.** 8 doctrines today prove it.
- Aegis rigging, end to end, 9/9 assets, Rust core, parity-tested.
- Two skeleton shapes with a gate that chooses per asset.
- The deformation probe — poses a rig and grades it.
- Git as provenance. RECORD commits with full telemetry in the message.
- The voice stack, both tiers, four-way failover, verified audible.
- FleetNet Radio — the ship speaks its own real condition aloud.
- Pause: file-based, survives restart, fails open, checkpoints the DB.
- `scripts/j` and `sound-the-ship.sh` — state and structural checks that
  cost one keystroke.
- The auth gate. Nine services, correct 401s.
- Budget discipline: reserve → call → release on failure. Verified under an
  actual failure.

---

## 6. WHAT REMAINS DISCONNECTED

**This is the honest half.**

- **The Live Captain cannot act.** Paused, propose-only, and the enforcement
  gate does not exist. Its rehearsal mode has produced zero proposals.
- **The Captain→Claude channel is one-directional in practice.** The return
  leg is wired into `/api/status` today, but nothing polls it. A message
  sits until a human prompts a session to look.
- **`best_axis` does not reach the Rust core.** The mass-based axis choice
  only works on the Python path; Rust still picks by bounding-box extent.
  The Lady had to be rigged through Python because of it.
- **The fit gate is miscalibrated for bodies.** `OFF_AXIS_RADIUS = 0.15` is
  tuned for thin objects. A normal torso reads as 77% off-axis at that
  radius and 13% at 0.35. It called a correctly-shaped figure broken.
- **Interpenetration is unexplained.** the-monad passes the fit gate at 11%
  and has 2,935 clips; gasket fails at 58% and has 9. Fit does not predict
  clipping. Fragmentation is the next suspect, untested.
- **Tree rigs are not in the corpus run.** `rig_corpus.py` still uses the
  chain path only.
- **Four orphan tool directories.** `beastscape-umap`,
  `phone-image-intake`, `cloud-image-demo`, `radio-traffic-eval`.
- **Four units defined but never installed** (`libfive-api`,
  `monad0-web-lab`, `npr-headlines-fetch` — `rich-voice` was the fourth
  until today).
- **`/captain-workbench-api/` returns 404** despite route and service both
  existing. Undiagnosed.
- **The ECR series is stalled.** Its capability-level inference rule was
  never transferred, and the Admiral does not hold the vocabulary — it is
  Static Captain's to define.
- **Five refused packets** wait on one or two sentences each.
- **The semantic kernel is deliberately unbuilt.** Two event stores already
  exist (git, mission-bus) and FleetCore is arguably a third. `MSIR-M3-Q2`
  settled that predicates differ in kind across documents and geometry.

---

## 7. THE THING THIS SYSTEM ACTUALLY LEARNED TODAY

Not a feature. A failure mode, found eleven times:

> **Every wrong claim made today was an instrument returning a plausible
> value that meant something else.** Not one was a crash, a failed test, or
> a logic error.

`is-active` meant *absent*, not *stopped*. Bounding-box extent meant *arm
span*, not *spine*. New box contact meant *articulation*, not *collision*.
A green suite meant *accidentally agreeing with operator state*. A fleet
table meant *what we work on*, not *what runs*.

Eleven collapses, every one landing on a check that took under a minute.
The reason those checks went unrun is the whole finding:

> **Surprise prompts checking. Agreement never does.**

That is doctrine 019, and it is the only one of the eight I would defend to
the last. Everything else orbits it.

---

## 8. WHAT WOULD CHANGE THE SHAPE

Stated so a future reader can tell whether this packet has expired:

1. **The Live Captain gaining a write path.** Today the engineer is the only
   actor with one. Rehearsal mode is the instrument for deciding whether
   that should change.
2. **A third pipeline.** Two (M³ over documents, Aegis over geometry) is not
   enough to generalise from. A third makes the kernel question real.
3. **Anything that polls the channel.** Right now every loop in this system
   closes through a human prompting a session.

---

*Written 2026-08-05, the day the rigging pipeline, the voice stack, the
pause, and eight doctrines all landed. Nothing here is polished because the
machinery is not polished. It runs, it is measured, and it caught itself
being wrong eleven times, which is the part worth preserving.*
