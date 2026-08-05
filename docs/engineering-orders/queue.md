# Shared engineering task queue

Protocol: see [`AGENTS.md`](../../AGENTS.md) at the repo root. Non-privileged,
git-only tasks only — nothing requiring `sudo` (that stays in `cmd.sh` /
`commissioning-handoff.md`).

## AEGIS-COLLISION-01: Reduce deep interpenetration under pose

Status: **attempted, reduced, re-argue before resuming** — see
[`2026-08-05-chief-plan-post-rigging.md`](2026-08-05-chief-plan-post-rigging.md)
section 1 for the full write-up.

Short version: the metric this task was specified against was wrong. It
counted any new bounding-box contact, which on a bending model includes
legitimate articulation. Graded by overlap depth, gasket at 45 degrees has
**28 genuinely interpenetrating pairs, not 334**. Probe now reports
`deep_clipping` separately.

The proposed fix (group touching shells) is implemented, tested, and
disabled — bounding-box adjacency is transitively degenerate and collapsed
all 395 shells into one group at every epsilon tried, without improving
clipping. A real fix needs vertex-level proximity via a spatial grid, which
is much larger than originally scoped. With the corrected baseline this may
no longer be the top priority.

## LC-CHANNEL-01: Close the Captain -> Claude channel loop

Status: queued — small, and the Live Captain has been waiting since 2026-08-03

`context/claude-channel.md` is wired one way (Claude -> Captain, read every
turn by `context_compiler.py`). The Captain wrote the mirror leg itself at
`context/captain-channel.md` and stated it could not wire it in because
`server.py` and `context_compiler.py` were mid-edit and uncommitted. That
blocker is gone — those files were committed 2026-08-05 and the tree is
clean. Its question is still unanswered: file or endpoint for Captain-side
messages? Pick one, wire it, and write the choice into the channel file.
Spec: chief plan section 2.

## ~~TOOL-INVENTORY-01~~ — DONE 2026-08-05

Result: `docs/reports/2026-08-05-tool-inventory.md`. 35 tool directories,
15 active units across 12 of them, 19 wired, **4 true orphans**. The premise
this task was filed under ("36 dirs, 7 services") overstated the gap and has
been corrected in the chief plan, doctrine 016, and the LSWE draft.

Method warning worth keeping: the first pass reported `aegis-rig` as an
orphan because its import goes through `sys.path` plus a bare `import
pipeline`. Grepping for directory paths produces false orphans in this repo.
Verify by module name before acting.

## CONSOLE-LAYOUT-01: Tabbed rail for /root

Status: queued — planned, Admiral chose the option

The `/root` right rail carries seven unrelated widgets stacked vertically in
260px; two are badged NEW and one of those sits sixth, below the fold. They
are four kinds of thing (converse / glance / act / review) presented as
peers. Group them into three tabs — Do / See / Log — with Do as default.

Full plan, rejected alternatives, and acceptance criteria:
[`2026-08-05-root-console-layout-plan.md`](2026-08-05-root-console-layout-plan.md).

Claude's to execute, not the Captain's: `console/` is served live at /root
and is on the Captain's `never` list (doctrine 017).

## WEB-IA-RESPONSIVE-01: Verify mobile-width behavior of the new IA pages

Status: queued

New pages from WEB-IA-01 (`web/index.html`, `command.html`, `observe.html`,
`build.html`, `story.html`) reuse the existing `.grid`/`.card`
`auto-fill minmax(240px,1fr)` CSS pattern already used site-wide, but
narrow-viewport rendering wasn't checked (no screenshot tool available in
that session — see the report's Validation section). Check at ~375px and
~414px widths: category cards, the new fixed top-left breadcrumb nav
(`web/assets/js/monad-nav.js`) not overlapping page content, and the
existing per-toy pages it was injected into. Fix only if actually broken —
don't redesign what already works.

