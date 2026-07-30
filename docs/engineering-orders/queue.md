# Shared engineering task queue

Protocol: see [`AGENTS.md`](../../AGENTS.md) at the repo root. Non-privileged,
git-only tasks only — nothing requiring `sudo` (that stays in `cmd.sh` /
`commissioning-handoff.md`).

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

