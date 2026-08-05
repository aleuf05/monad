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

## TOOL-INVENTORY-01: Classify every directory under tools/

Status: queued

36 tool directories, 7 running services. Precedent that the gap is real:
`mission_bus.py`'s own header records that `engineering-comms/schema.py`
was a tested 17/17 validator wired to nothing. Classify each directory as
running / wired / orphan and file the list. Delete nothing.
Spec: chief plan section 3.

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

