# Demo-Readiness Sweep — Findings

Date: 2026-07-15

Prepared for: Captain / Lieutenant / Admiral

Scope: whole-site verification pass ordered ahead of the Lt.'s live demo --
every page, every toy, checked live against `https://cameronlampley.com/`,
not just read as source. Load-time checks (HTTP status, console/page
errors) covered all 20 public surfaces (8 pages, 12 toys). A second pass
exercised the actual controls on the 11 toys that had only been
load-checked, not clicked through.

## Found and fixed

**BS3-01 -- Bridge Station 3.0 contact-label collision.** Vessel callsign
labels render at a fixed offset above each contact's icon with no
collision check between nearby vessels. When two vessels are close
together on the chart (observed live: QUACKEN and MONAD, both holding
near the same position), their labels overlapped into illegible smashed
text -- directly on the primary map view, the first thing anyone looks at
on this toy.

Fix: `layoutLabelPositions()` added in `toys/bridge-station-3.0/src/App.jsx`
next to the existing `toChart()` -- computes each label's default
position, then nudges it down in 12px steps against every label already
placed this render pass until it clears. Rebuilt (`vite build`), deployed
`dist/` -> `web/toys/bridge-station-3.0/`, stale bundle
(`index-CDUAAEvc.js`) removed, new bundle (`index-DzRKSaLu.js`) confirmed
reachable (200) and verified live via headless browser: labels now stack
vertically instead of overlapping, zero console errors, contact-select
(Fleet Motion -> Periscope) still works end to end.

## Checked live, no defect found

- All 8 top-level pages (home, bridge, command-deck, fleet, logs, final,
  ops, staff) and all 12 toys: HTTP 200, zero page/console errors.
- The `claude.png` / `reyes.png` 404s on `staff.html` and
  `command-deck.html` are the site's documented no-invented-likeness
  policy working as designed (`onerror` -> rank-insignia placeholder,
  confirmed visually, not a bug).
- agent-ops (pause/resume), bridge (tab switch), periscope (details
  toggle), reaction-diffusion-painter (sliders/preset/pause),
  world-intake (status filter, all 3 values, refresh), asset-viewer
  (upload control present) -- all exercised live, clean.
- fleetcore-live's "Connect" button is a manual-reconnect trigger by
  design (auto-reconnect already covers the live-state case); it doesn't
  toggle to "Disconnect" because there is no disconnect feature, not
  because it's broken.
- fleetcore-control's write-path controls (spawn/despawn/reset/route) were
  reviewed as code, not fired live -- reset is gated behind a `confirm()`
  naming the blast radius ("affects every connected visitor and cannot be
  undone"), spawn/route/despawn all validate their inputs before sending.
  Sound as written. Not exercised live because doing so would alter the
  shared world state other visitors (including the Lt., pre-demo) would
  see, for no verification benefit over reading the guard clauses directly.
- living-captain: passive read-only display, nothing to exercise.
- All 6 systemd services (`fleetcore-serve`, `world-intake`,
  `living-fleet`, `living-fleet-memory`, `monad-watchman`,
  `living-captain-status`) active, uptimes 5h-38h, no restarts observed.

## Bottom line

One real, visible defect found this pass (`BS3-01`); fixed, deployed,
verified live. Everything else checked live came back clean. Remaining
open items are exclusively the four `blocked-on-human` queue entries
(`HUMAN-01` through `HUMAN-04`) -- decisions or access, not code defects.
