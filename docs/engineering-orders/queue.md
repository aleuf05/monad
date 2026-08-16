# Shared engineering task queue

Protocol: see [`AGENTS.md`](../../AGENTS.md) at the repo root. Non-privileged,
git-only tasks only — nothing requiring `sudo` (that stays in `cmd.sh` /
`commissioning-handoff.md`).

## ~~CANON-TRACK-01~~ — DONE
Ten "Status: Canon" doctrine files (`023`–`031`, `041`) were added to git and are tracked. Verified zero untracked doctrine files.

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

## ~~LC-CHANNEL-01~~ — DONE
Resolved 2026-08-05: Single bidirectional shared channel established at
`tools/live-captain/context/claude-channel.md` and codified in `captain-kernel.md`.

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

## ~~WEB-IA-RESPONSIVE-01~~ — VERIFIED 2026-08-14
Verified mobile-width layout on `web/index.html`, `command.html`, `observe.html`, `build.html`, `story.html`, and `staff.html`. The `.grid` single-column fallback (`minmax(240px, 1fr)` at 327px–366px container widths) and top header 56px clearance for fixed `monad-nav.js` are structurally sound.


