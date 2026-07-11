# Radio Console Bridge Integration & Deployment Watch Log

Date: 2026-07-11
Operator: Commander Claude, Engineering Watch
Directed by: Admiral C — deploy Radio Console publicly and wire it into Bridge Station's Live Console as a third panel, rather than leaving it standalone.
Objective: Bridge Station Mk V — integrate `toys/radio-console/` into the composited Live Console, and deploy both it and the integration to the public site.

## Problem

Radio Console shipped standalone in the prior watch (`2026-07-11_radio-console-v1.md`), with both deployment and Bridge integration deliberately left open pending confirmation — a different kind of decision than the read-only FleetCore Live viewer, since it plays audio once a visitor powers it on. Directed to do both.

## Integration

- `toys/bridge/index.html` / `style.css`: added Radio Console as a third Live Console panel, spanning full width in its own row below Fleet Motion and Periscope (`.live-console` grid gained a second, `auto`-sized row; the new panel uses `.live-instrument-compact { grid-column: 1 / -1; height: 360px }`) rather than squeezing into the existing two-column split, since it's a much shorter instrument than the two map/optics panels.
- The 360px figure came from measurement, not a guess: a Playwright script loaded Radio Console inside a bare iframe at Bridge's actual ~490px embedded width and read back real rendered heights. First pass (no panel-specific trimming) needed ~436px and was clearly too tall for a first guess of 220px — confirmed directly from a screenshot showing Power/volume/signal/transcript entirely cut off and, because `.station-deck` uses `overflow: hidden`, genuinely inaccessible rather than just needing a scroll.
- Rather than keep growing Bridge's panel to match Radio Console's full standalone layout, added an embedding-aware mode to Radio Console itself: `window.self !== window.top` (try/catch-wrapped) sets an `is-embedded` body class, and CSS under that class hides the subtitle/eyebrow, shrinks headings and control padding, and caps the transcript's height — bringing the measured height down to ~337px, which is what the final 360px panel budget is based on. The same page still renders full-size when opened standalone.
- Also had to lower Radio Console's own two-column-to-one-column stacking breakpoint from 780px to 420px: Bridge's ~490px-wide panel falls inside the old breakpoint, which would have stacked the signal meter and transcript vertically instead of side by side — taller, exactly backwards from what a compact embedded panel needs. Real 390px phones in standalone mode still fall below 420px and stack as intended.
- `toys/bridge/index.html`'s Status Board "Current Sprint" field still said "Bridge Station Mk III," unchanged since the Mk IV selection-sync watch — caught and fixed to Mk V while in here, along with the engineering-note paragraph, which only mentioned Fleet Motion and Periscope.
- Deployed both instruments: `web/toys/radio-console/` is a plain copy (no divergence needed — unlike `fleetcore-live`, Radio Console has no server URL to repoint). `web/toys/bridge/` required manual reconciliation rather than a raw copy, since it already carries an intentional divergence from source (the Watchbook tab is a static Ship's Log redirect, not an iframe, because Watchbook isn't deployed publicly — see `docs/deployment.md`). Applied the Radio Console panel markup and the Mk V text updates by hand to the deployed copy, confirmed via `diff` afterward that the only remaining difference from source is the documented Watchbook divergence.
- Added a "Radio Console" launch card to `web/command-deck.html` as the new "Newest Toy," demoting FleetCore Live to "Toy," and updated Bridge Station's own card description to mention all three Live Console instruments.

## Verification

Playwright, desktop (1440×900) and mobile (390×844), against a LAN-reachable local server: confirmed the Radio Console iframe loads inside Bridge (`frameLocator` reached `#powerButton`), zero console/page errors, no horizontal overflow on mobile. Powered it on via a real click and forced an immediate transmission: Power/channel chips/volume/mute, an animating amber signal meter, and a populated transcript entry are all visible within the panel on both viewports without scrolling to reach them — confirmed by screenshot, not just by absence of layout-overflow warnings.

Deployed via direct `rsync -av --delete web/ /var/www/monad/` (no Caddy config changed, so no `caddy validate`/reload needed — matches the established pattern from prior static-content-only deploys). Confirmed locally on Granite and via `https://cameronlampley.com/monad/toys/bridge/` and `https://cameronlampley.com/monad/toys/radio-console/` that both serve the updated content.

## Follow-up

None new for Radio Console itself — v2 (live-fleet-state-aware chatter) and the real-broadcast stretch goal remain fully deferred per the original request's priority note. Bridge's own next direction (richer contact rail, station handoff) is unchanged from the prior watch log.
