# Bridge Station 2.1 LAN Deployment Watch Log

Date: 2026-07-11
Operator: Commander Claude, Engineering Watch
Directed by: Admiral C, Engineering Packet "Deploy Bridge Station 2.1 to LAN"
Objective: get the `bridge-station-2.1.jsx` reference implementation running live on Granite's LAN — no auth, no public exposure.

## Problem

The packet referenced `bridge-station-2.1.jsx` as "attached / in repo once committed" — at the time the packet arrived, it was neither. Held the deploy until the operator provided the actual component (a single-file React component: Fleet Motion + Periscope panels, mock in-memory vessel simulation, click-to-select, click-to-set-waypoint). This is the first component in this repo requiring a real build toolchain (React + Vite + `lucide-react`) — every other toy is deliberately zero-dependency vanilla JS, stated explicitly in nearly every other toy's README. Flagged this before starting, and separately flagged that "2.1" (Select → Act → Set Waypoint, mock state) sounded like a different scope than the just-shipped "Bridge Station 2.0" (read-only observer, real FleetCore data) rather than a version bump of it. Reading the actual component confirmed it has no backend calls anywhere — "Act" here means local React state only, not a write to any real system, which lowered the stakes of the scope question considerably. Proceeded treating 2.1 as a separate artifact alongside 2.0, neither replacing the other.

## Integration

- Scaffolded via `npm create vite@latest bridge-station-2.1 -- --template react` inside `toys/`, `npm install`, `npm install lucide-react`, matching the packet's steps.
- Dropped the provided component in as `src/App.jsx` verbatim. Removed the scaffold's default `App.css` and unused starter assets (`react.svg`, `vite.svg`, `hero.png`) once confirmed the new `App.jsx` doesn't reference them.
- Caught before it caused a visible bug: the Vite template's `src/index.css` carried a full default theme — light background, purple accent, and critically a `#root { width: 1126px; max-width: 100%; text-align: center; border-inline: 1px solid ... }` rule that would have fought the component's own full-viewport dark layout. Replaced with a minimal reset (matching this repo's established minimal-CSS-reset convention elsewhere) before ever loading the page, not after seeing it break.
- `npm run build` succeeded clean on the first attempt after those fixes — 203KB JS bundle, gzipped 65KB.
- `npx serve -s dist -p 8080` deviated slightly from the packet's suggested `-l 0.0.0.0:8080` flag, which errored (`serve`'s `-l` expects a full URI scheme like `tcp://0.0.0.0:8080`, not a bare host:port string) — `serve`'s default listen address is already `0.0.0.0`, so `-p 8080` alone was sufficient and correct.

## Verification

Playwright against the deployed build, using Granite's actual LAN address (`http://192.168.0.100:8080/`), not `localhost` — matching what a second device on the network would actually resolve. First verification pass had two false negatives from imprecise test selectors (clicking a vessel's non-interactive label `<text>` instead of its clickable `<g className="contact-icon">` polygon, and manually computed chart-click coordinates missing the target); confirmed via screenshot these were test-script issues, not app bugs, then re-verified with selectors targeting the actual clickable elements:

- Selecting a contact (Pilot Amber) shows "OBSERVE ONLY" and a live bearing/range readout on the Periscope panel.
- Selecting MONAD (own ship) exposes "Set Waypoint"; clicking it then clicking the Fleet Motion chart plots a waypoint, logs "Waypoint set — bearing N°," and the button resets.
- Confirmed this isn't just a UI state flip: MONAD's own course readout changed from 250° to 268° over the following ticks, matching the component's `turnToward`/`stepVessel` logic actually running, not a static demo.
- Mobile (390×844): the component's own `@media (max-width: 860px)` rule correctly stacks the two panels, no horizontal overflow.
- Zero console errors or page errors across every run, desktop and mobile.

## Follow-up

Per explicit operator instruction, reboot durability was not addressed — the `npx serve` process is ad hoc and has no systemd unit, same open item as `fleetcore-serve` and the Bridge Station 2.0 LAN server. No auth was added, matching the packet's own explicit scope ("LAN is treated as the trust boundary") — there is no backend for this artifact to protect either way, so this is lower-stakes than FleetCore's own no-token-by-default posture.
