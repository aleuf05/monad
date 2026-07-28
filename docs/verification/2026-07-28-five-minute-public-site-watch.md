# Five-Minute Public-Site Watch

- **Observed:** 2026-07-28
- **Status:** Verified structural and live findings
- **Observer:** Captain / Codex
- **Origin:** Admiral-requested proof of sustained useful work

## Scope

Maintain at least five minutes of active work on public-site reachability,
live integrity, discoverability, and visitor-facing truth language. Avoid
padding, speculative redesign, and code volume without an observed target.

## Findings

### Click reachability

A local HTML link graph found:

- 30 HTML surfaces under `web/`;
- 29 reachable from `web/index.html`;
- one unreachable surface: `command-deck.html`.

The exception is the documented intentional legacy mirror of `index.html`, not
a visitor destination.

Initial parsing reported ten broken targets. Refinement showed all ten were
false positives from data-URI icons or runtime template strings. They were not
recorded as defects.

### Live integrity

All 29 click-reachable HTML destinations returned HTTP 200 from the real
`https://cameronlampley.com/` domain during the watch.

A second pass extracted 132 static HTML resource references. They resolved to
67 unique local targets:

- zero targets were missing from `web/`;
- all 67 returned HTTP 200 from the live domain.

### Runtime feeds

The watch resolved page-relative runtime fetches separately from static script
paths to avoid false 404 findings.

Verified live and JSON-decodable:

- fleet projection and Watchbook log;
- fleet status;
- mission operations, artifacts, reviews, and radio projections;
- Periscope creature manifest;
- Living Captain status;
- review inbox and Watch Officer status;
- NPR headline and podcast projections.

The fleet-status feed was approximately one minute old at inspection. Review
Inbox and Watch Officer projections were approximately eight minutes old.

Several mission projections carry 2026-07-16 generation timestamps. This is
an observed age, not proof of staleness: the underlying mission records may be
intentionally unchanged.

### Optional and uncommissioned services

- Character Voice Studio's `/voice-api/status` returned HTTP 404. Its client
  catches that condition and visibly retains the free Browser Speech rehearsal,
  so the main instrument remains useful through its documented fallback.
- Shape Foundry's `/libfive-api/status` returned HTTP 502. No
  `libfive-api.service` unit is installed, and its static manifest fallback is
  absent. The existing `LIBFIVE-CONSOLE-1.0` packet already records repository
  implementation complete but privileged commissioning pending. This is an
  uncommissioned public capability, not a newly failed service.
- FleetCore, Living Fleet, memory, Watchman, World Intake, Living Captain
  status, and Private Conference services were active during inspection.

### External presentation dependencies

Direct, non-templated dependencies used by public pages responded during the
watch, including Google Fonts stylesheets, Leaflet, Three.js, Model Viewer,
OpenStreetMap attribution, and NPR's news page.

Map tile URLs and the optional Gemini endpoint contain runtime placeholders,
so a raw URL probe cannot test them meaningfully. They were excluded rather
than misreported as failures.

### Truth-language candidates

A deliberately coarse visible-text scan looked for language such as `live`,
`simulated`, `narrative`, `generated`, `archive`, `unknown`, and `read-only`.
Four pages contained none of those exact terms:

- Bridge Station 3.0;
- Character Voice Studio;
- Periscope Station;
- Reaction-Diffusion Painter.

This is not proof that those pages mislead visitors. It is a candidate list
for the human study: keyword absence cannot determine whether presentation,
context, or interaction communicates the source type adequately.

### Corrected integration defect

Crew contained two `monad-nav.js` script tags, and the shared component
unconditionally appended a fixed navigation bar on each execution. The watch:

1. removed the duplicate Crew inclusion;
2. added an idempotency guard to the shared component;
3. verified one local and live inclusion;
4. verified the guard through minimal DOM execution;
5. verified both live URLs returned HTTP 200.

Durable implementation evidence:
`docs/engineering-orders/packets/WEB-NAV-DUPLICATE-0.1.md`.

## Direction consequence

The public surface is structurally healthy: nearly every HTML page is
click-reachable, and every reachable page responded live. The stronger open
question is semantic rather than mechanical—whether humans understand what
Monad is, what is live, and why each surface matters.

The next study should show the four truth-language candidates to uncoached
participants before any blanket label system is implemented.
