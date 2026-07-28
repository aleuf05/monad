# Packet: WEB-NAV-DUPLICATE-0.1

1. **Originating intent** — Five-minute sustained public-site integrity watch
   requested by the Admiral on 2026-07-28.

2. **Verified starting state** — Static inspection found two
   `monad-nav.js` script tags in `web/staff.html`. The shared script
   unconditionally appended a fixed `.monad-nav` element on every execution,
   so both inclusions produced visible overlapping navigation.

3. **Objective / problem** — Restore exactly one shared navigation bar on the
   Crew page and make the shared component harmless if accidentally included
   twice elsewhere.

4. **Scope and exclusions** — Remove one duplicate script tag and add one
   existing-element guard to the shared navigation script. No redesign,
   hierarchy change, backend work, or unrelated cleanup.

5. **Constraints / authority** — The Admiral authorized sustained useful work
   without reckless changes or fake progress. `web/` is live production; the
   correction must be minimal, immediately visible, and reversible.

6. **Acceptance criteria** —
   - `web/staff.html` contains exactly one `monad-nav.js` inclusion;
   - executing the shared script when `.monad-nav` already exists adds
     nothing;
   - Crew and the shared script continue returning HTTP 200 live;
   - no other navigation markup or hierarchy changes.

7. **Tests / rollback** — Static counts, JavaScript syntax check, a minimal DOM
   guard execution check, and live HTTP/content retrieval. Roll back the two
   localized hunks.

8. **Assigned actor** — Captain / Codex.

9. **Evidence / completion state** — **Verified complete.**
   - `node --check web/assets/js/monad-nav.js` passed.
   - A minimal DOM execution confirmed an existing `.monad-nav` returns before
     reading or appending component state.
   - Local and live Crew HTML each contained exactly one shared-script tag.
   - The live shared script contained the idempotency guard.
   - Live Crew and shared-script URLs returned HTTP 200.
