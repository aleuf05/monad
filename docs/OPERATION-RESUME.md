# OPERATION RESUME — start here in a clean context

Single entry point for picking this up in a new session or a new
terminal. Written 2026-08-05. If anything below contradicts the repo,
the repo is right — verify before asserting.

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
| `aegis-inspect` | 4799 | glTF corpus INSPECT + VALIDATE |
| `root-console` | 4792 | console + document corpus API |
| `public-root-auth` | 4779 | forward_auth for everything above |
| `live-captain-web` | — | the Live Captain |

**Where to look on the live site:** `https://cameronlampley.com/root`

- Right panel: **Packet Drop** (drop a `.docx`), **M³ Cycle** (verdict +
  six condition chips)
- Header: **📄 Document Viewer** (themes, MSIR token glossing, queries
  and packets browsable), **🦴 Aegis INSPECT** (asset list, 3D preview,
  rig readout, VALIDATE button)

**Answered, settled:**

- `MSIR-M3-Q1` → **A**: M³-over-documents. `D_t` = the docs corpus,
  `H_t` = git. Built and running as `tools/m3-cycle/`.
- `MSIR-M3-Q2` → **D**: Aegis-Monad's `D_t` = **3D assets**. A separate
  system. M³ v0.1 does *not* transfer to it — predicates differ in kind.

**No open queries.** Nothing is parked.

**The fact that shapes the next move:** the geometry corpus is 9 GLBs,
4.45M vertices, 342MB — and **0 are rigged**. All static, single-node,
no skins, no joints. Every one measures **high weight-bleed risk**
(gasket 395 disjoint shells, the-monad 4,676, kraken 1,831 with the
largest shell only 3.8% of the mesh). A proximity-based rigging solver
run today would bleed weights across unconnected parts on every asset.

---

## 3. Next moves, in order of value

1. **Get one riggable asset in.** Everything downstream of the rigging
   spec is blocked on having a single GLB with a skin and joints. Either
   drop one through an intake, or make the solver's first job
   synthesising a skeleton for `gasket.glb` (smallest at 29K verts, so
   iteration is fast).
2. **Aegis pipeline stages 3-6.** INSPECT and VALIDATE exist.
   AUTHORIZE / EXECUTE / RECORD do not. RECORD should probably reuse
   git rather than reimplement provenance — that question has come up
   in three packets and is still unsettled.
3. **Refusal review backlog** (doctrine 013 §3). 18 refusals, triaged
   into four buckets:
   - 2 resolvable by one Admiral sentence (the LUCA pair — both ask for
     out-of-character confirmation that they're real research)
   - 7 hardware/host claims — one `lsusb` paste clears several, or they
     go `moot`
   - 4 that only need restating concretely
   - 4 permanently standing (Crystal Ledger ×2, special-mode,
     input-override) — could be closed out as terminal in one pass
4. **Rust vs Python** for rigging maths. Real decision, unstated so far.
   This repo is Python; rigging is the one place the argument is
   genuine rather than ceremonial.

---

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

---

## 5. Map

**Read first:** `docs/doctrine/012` (packet terms) → `013` (lifecycle +
refusal review) → `014` (the working loop; §4a division of labour).

**Mechanisms:**
- `docs/engineering-orders/queries/` — **"Chief Resolve"**: one blocking
  question at a time, carried to the Chief by the Admiral. `README.md`
  has the procedure. **When a query is open, stop and wait.**
- `docs/engineering-orders/packets/` — work records and refusals
- `docs/incoming/` — staged drop-box material, *not* filed
- `logs/captains/2026/` — packet filings, each with verbatim content and
  a separate labelled assessment

**Code:** `tools/docx-intake/`, `tools/m3-cycle/` (engine + 13 tests),
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
