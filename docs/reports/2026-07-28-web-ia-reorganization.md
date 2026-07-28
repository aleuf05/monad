# Monad Web UX — Information Architecture Reorganization

**Date:** 2026-07-28
**Requested by:** The Admiral (chat-delivered "Commander Claude Integration Packet," Monad Web UX — Information Architecture and Top-Level Organization Sprint)
**Status:** Implemented and live at `https://cameronlampley.com/`
**Queue entry:** `WEB-IA-01` in `docs/engineering-orders/queue.md` (removed on completion — evidence lives here)

## Problem

`web/index.html` had accreted into a single long page: 6 flat sections, ~24
cards, 8 crew tiles, 2 status widgets, and a 5-link footer — all equal visual
weight, all one click from the root. No shared navigation existed anywhere
else in the site; every toy page independently hardcoded (or omitted) a
single `← index.html` link. `bridge-station-3.0` had no back-link at all.

## Hierarchy

Five top-level paths, chosen by user intent rather than implementation
history (audited via a full-site inventory: 16 toys, 8 top-level pages, 3
mission/archive pages, `web/data/*.json` consumers, all cross-links):

```
Monad (web/index.html)
├── Command    — act: Bridge Station 3.0, Agent Operations, Ops Reader
├── Observe    — watch: Fleet Motion, Periscope, Radio Console, Fleet Map,
│                Watch Officer, Review Inbox, World Intake, Living Captain
├── Build & Research — make/study: Voice Studio, Asset Viewer, Shape Foundry,
│                Reaction-Diffusion Painter, Cognition Graph
├── Story & Records — history: Adventure Stations, Mission Archive,
│                Ship's Log, Sea Trial Report, media/posters
└── Crew       — web/staff.html, unchanged, now a peer top-level path
```

Every existing surface kept its original URL and file; nothing was deleted
or moved on disk. Category pages (`web/command.html`, `observe.html`,
`build.html`, `story.html`) are new files that link to the existing pages/toys
in place — this is index reorganization, not a migration.

## Navigation

One shared component, `web/assets/js/monad-nav.js`: a small fixed
top-left breadcrumb (`⚓ Monad › [Section ▾] › Page`) injected via a single
`<script>` tag. The section segment is a click-to-open switcher listing all
five top-level paths, so an experienced operator can jump laterally in one
click instead of returning Home first. It's a pure overlay — no existing
page layout, CSS, or DOM was touched to accommodate it — so it carries zero
risk to any toy's existing functionality.

Wired into all 21 existing pages that didn't already have it (16 toys, plus
`fleet.html` / `logs.html` / `final.html` / `ops.html` / `staff.html` / the 3
mission/archive pages) via a scripted insertion before each file's single
`</body>` tag, verified safe beforehand (`grep -c '</body>'` == 1 on every
target). `web/index.html` itself has no breadcrumb — it *is* the top.

## Landing page

`web/index.html` rewritten from a full control inventory down to: banner,
live fleet-status strip (unchanged, confirms the system is active), one
sentence of plain-language orientation, the 5 category cards, and a
2-link "Frequently used" row (Bridge Station, Ops Reader) for operators who
already know exactly where they're going. `web/command-deck.html`
regenerated from the new `index.html` via the existing
`tools/sync-command-deck.py --write` (keeps the documented byte-identical
mirror invariant for old bookmarks).

## What could not be placed cleanly

- **`web/status/fleet.json`** — orphaned data file, no HTML/JS anywhere
  references it (the map instead reads `web/fleet.json` at a different
  path). Not a navigation surface, so out of scope for this sprint; flagged
  here rather than silently deleted.
- **`web/assets/js/main.js`** — defined (fleet-doctrine role/brief data) but
  not `<script src>`-included by any page found. Same treatment: flagged,
  not touched.
- **`command-deck.html`** — intentionally left without its own identity in
  the new hierarchy; it remains a pure legacy-URL mirror of `index.html` by
  design (`tools/sync-command-deck.py`'s stated purpose), not a page users
  are meant to discover.

## Validation

Live-checked post-deploy (no staging — `web/` is production):
`https://cameronlampley.com/{,command,observe,build,story}.html` and
`/toys/{periscope,bridge-station-3.0}/` all return `200`; homepage content
and injected nav script confirmed present via direct fetch. Not
browser-screenshot-verified — flagging per policy rather than claiming
visual confirmation I don't have.
