# Shared engineering task queue

Protocol: see [`AGENTS.md`](../../AGENTS.md) at the repo root. Non-privileged,
git-only tasks only — nothing requiring `sudo` (that stays in `cmd.sh` /
`commissioning-handoff.md`).

## WEB-CLEANUP-01: Remove or document two orphaned web assets

Status: queued

Found during the WEB-IA-01 audit (`docs/reports/2026-07-28-web-ia-reorganization.md`),
re-confirmed 2026-07-28: `web/status/fleet.json` and `web/assets/js/main.js`
have zero inbound references anywhere in `web/` (`grep -rl` on both paths
returns nothing; the live fleet map reads `web/fleet.json` at a different
path instead). Not navigation surfaces, so out of scope for the IA sprint
itself. Confirm still unreferenced, then either delete both or, if you find
a reason they're still needed, note it here instead of removing.

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

