# Web IA Independent Verification

**Observed:** 2026-07-28T12:02:56Z  
**Status:** Draft technical finding  
**Observer:** Codex  
**Method:** Direct HTTPS requests plus repository link and script inspection.

## Resolution note — 2026-07-28

**Technical finding:** The exception recorded below was subsequently resolved.
Commit `619e17c` removed the duplicate Crew-page hook and added an idempotency
guard to the shared navigation component. Packet `WEB-NAV-DUPLICATE-0.1` and
the accompanying sustained live-site watch preserve the verification
evidence. The original exception remains below as historical evidence.

| Surface | Live response | Repository target |
|---|---:|---|
| Home | 200 | `web/index.html` |
| Command | 200 | `web/command.html` |
| Observe | 200 | `web/observe.html` |
| Build & Research | 200 | `web/build.html` |
| Story & Records | 200 | `web/story.html` |
| Crew | 200 | `web/staff.html` |

The local links extracted from the six top-level pages resolved to existing
repository files at the time checked. `node --check
web/assets/js/monad-nav.js` passed.

## Exception

`web/staff.html` contained two references to `assets/js/monad-nav.js`:
one multiline hook with `data-page="Staff"` and one single-line hook. Both
execute, so a successful HTTP response does not establish correct rendering.
This requires removal of one hook followed by browser-visible verification.

## Limits

This check did not claim browser layout, interaction, mobile behavior, or
screen-reader verification. Runtime-generated JSON files were outside the
sprint verification scope.
