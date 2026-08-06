# Root Console Layout — tabbed rail

Date: 2026-08-05
Status: **Planned, not built.** Filed for execution.
Decision: Admiral, 2026-08-05 — tabbed rail, from three options offered.

---

## The problem, measured

`/root` is **two columns**, not three: `#terminal` (flex) and
`#status-panel` (260px, right). The three-column page is `console/assets.html`
(290 / 1fr / 250), which is a different screen.

The defect is the right rail. It carries **seven unrelated widgets stacked
vertically in 260px**:

1. Packet Drop *(badged NEW)*
2. Live Status
3. Dispatch
4. Captain Handoffs
5. Ship's Log
6. M³ Cycle *(badged NEW)*
7. Semantic Text Metamorphosis

Two are badged NEW and one of those sits sixth, below the fold. The stack
order is the order things were built, which is not an order anyone reading
the page cares about.

Those seven are **four different kinds of thing** presented as peers:

| Kind | Widgets |
|---|---|
| converse | the terminal |
| glance | Live Status |
| act | Packet Drop, M³ Cycle, Metamorphosis |
| review | Dispatch, Captain Handoffs, Ship's Log |

## The change

Right rail becomes three tabs. Nothing leaves the page; the grouping does
the work.

```
┌─ MONAD ROOT ──────────────────────────┐
│ 6 · GREEN · 4.4M · 88 · 18/18 · RUST  │  stat strip (unchanged)
├──────────────────────┬────────────────┤
│                      │ [Do] See  Log  │  ← tabs
│   terminal           ├────────────────┤
│                      │ Packet Drop    │
│                      │ M³ Cycle       │
│                      │ Metamorphosis  │
└──────────────────────┴────────────────┘
```

- **Do** — Packet Drop, M³ Cycle, Semantic Metamorphosis *(default tab)*
- **See** — Live Status
- **Log** — Dispatch, Captain Handoffs, Ship's Log

`Do` is default because two of the three NEW-badged things live there and
because it is the only tab containing verbs.

## Why this option

Smallest change that fixes the actual defect. No widget markup moves, no
JavaScript that populates a widget changes — only wrapper elements and a
tab switcher. Everything stays on one page, so nothing that currently works
by being adjacent to the terminal stops being adjacent to it.

The rejected options, recorded so they are not re-proposed blind:

- **Status bar + full-width terminal** — pushes records to another page.
  More space for the terminal, but it moves three working panels off `/root`
  for a layout gain, and nobody asked for the terminal to be wider.
- **Left nav + right context** — the strongest long-term shape and the
  closest to a real application shell, but it is a three-column layout and
  the Admiral said three columns are no good. Not re-proposed without him
  raising it.

## Acceptance

- No widget loses functionality. Packet Drop still accepts a `.docx`, M³
  Cycle still runs, all three record panels still populate.
- Nothing below the fold in any tab at 1080p.
- Tab state survives a page reload (`localStorage`), because a console you
  reload often should not keep resetting to a tab you were not using.
- `node scripts/verify-live-page.mjs` clean — though note it cannot reach
  `/root`, which is password-gated. Verification there is the throwaway
  harness pattern used on 2026-08-05, or a manual look.

## Files

- `console/index.html` — the whole change. Rail markup at ~line 631,
  layout CSS at ~line 74 (`#main`, `#status-panel`).

## Note on who executes this

`console/` is served live at `/root` with no build step, so this is
production work. It was added to the Live Captain's `never` list on
2026-08-05 — see `docs/doctrine/017`. This is Claude's to execute, not the
Captain's, unless the Admiral rules otherwise.
