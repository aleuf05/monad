# Web IA — Codex Entry Checklist

**Prepared:** 2026-07-28  
**Status:** Draft operational handoff; no assignment implied  
**Prepared by:** Codex

## Resolution note — 2026-07-28

**Technical finding:** The entry conditions became historical after
`WEB-IA-01` closed. The duplicate Crew-page navigation hook was removed and
the live behavior was verified under packet `WEB-NAV-DUPLICATE-0.1`, recorded
in commit `619e17c`. This checklist is retained as handoff history, not as an
active assignment.

Codex remains outside Claude's claimed `web/` scope until `WEB-IA-01` is
closed or an explicit file-level handoff is given.

## Entry conditions

1. Confirm `WEB-IA-01` has been removed from
   `docs/engineering-orders/queue.md`, or obtain an explicit handoff.
2. Pull and re-read the queue before claiming follow-on work.
3. Confirm the working tree no longer contains Claude's uncommitted sprint
   changes.
4. Re-run top-level HTTPS and local-link checks.
5. Inspect `web/staff.html` for exactly one shared-navigation script hook.

## Safe follow-on lane

The first independent follow-on is browser-visible acceptance testing:
desktop and phone-width navigation, section switching, breadcrumb placement,
keyboard operation, and confirmation that every top-level category makes its
contents obvious without hunting. Findings belong in `docs/verification/`;
runtime fixes require a new queue claim or packet as applicable.
