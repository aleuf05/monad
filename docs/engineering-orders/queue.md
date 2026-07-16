# Shared engineering task queue

Protocol: see [`AGENTS.md`](../../AGENTS.md) at the repo root. Non-privileged,
git-only tasks only — nothing requiring `sudo` (that stays in `cmd.sh` /
`commissioning-handoff.md`).

## BRIDGE-RETIRE-01 — Retire stale web/bridge.html

- Status: queued
- Source: `docs/architecture/component-consolidation-master-plan-v0.1.md`, Phase 1
- Objective: `web/bridge.html` reads `web/bridge-state.json`, confirmed
  stale (last written 2026-07-09, a week old as of this packet). Pre-dates
  FleetCore's live WebSocket feed. Retire it; `toys/bridge/` ("Bridge
  Station") and `toys/bridge-station-3.0/` already cover this need live.
- Scope: remove `web/bridge.html`, `web/bridge-state.json`, and any script
  that regenerates the latter (grep first — do not assume none exists).
  Remove the "Bridge" footer link from `web/index.html` and
  `web/command-deck.html`. Update `docs/deployment.md`'s own description
  of `web/bridge.html` to reflect its removal, not leave it describing a
  file that no longer exists.
- Exclusions: do not touch `toys/bridge/` or `toys/bridge-station-3.0/`.
- Done evidence: `https://cameronlampley.com/bridge.html` returns 404 (or
  the link simply no longer exists on the live site, per policy); no
  broken internal links remain; drift checker still clean.

## CMDDECK-SYNC-01 — Resync command-deck.html with index.html

- Status: queued
- Source: `docs/architecture/component-consolidation-master-plan-v0.1.md`, Phase 1
- Objective: `docs/deployment.md` requires `web/command-deck.html` be kept
  an identical mirror of `web/index.html` (distinct `<title>` only) so old
  bookmarked URLs keep working. It has drifted -- missing 3 links added to
  `index.html` since (`ops.html`, Cognition Graph, Living Captain).
  Resync it. Also apply BRIDGE-RETIRE-01's link removal here too, if that
  task lands first (check the queue/git log before starting).
- Scope: `web/command-deck.html` only, plus the same `docs/deployment.md`
  update BRIDGE-RETIRE-01 makes if these two tasks land out of order.
- Exclusions: no content changes to `web/index.html` itself.
- Done evidence: diffing the two files' link sets shows zero difference
  (same check used to find this drift in the first place).

## WATCHMAN-01 — Flesh out Watchman's missing checks

- Status: queued
- Source: `docs/architecture/component-consolidation-master-plan-v0.1.md`, Phase 1
- Objective: `watchman.py` implements 2 of the 8 checks its own role
  implies (disk usage, Qdrant health). Add process monitoring and
  endpoint/health checks for the other 5 live services not currently
  covered: `fleetcore-serve`, `world-intake`, `living-fleet-memory`,
  `living-captain-status`, `living-fleet`. Add stale-service and
  failed-restart detection if time permits within this packet's scope.
- Scope: `watchman.py` only. Extend `heartbeat()`'s output shape
  additively -- do not remove or rename existing fields (`disk`, Qdrant
  health) that other things may already read.
- Exclusions: no changes to how Watchman is run (systemd unit, restart
  policy) -- that's infrastructure, routes through cmd.sh if it's ever
  needed, not this packet.
- Done evidence: each new check verified against the real running
  services on this host (not mocked), heartbeat log shows the new fields
  populated with real values.

## BRIDGE3-CONSOLIDATE-01 — Fold Bridge, FleetCore Live, and FleetCore Control into Bridge Station 3.0

- Status: queued
- Source: `docs/architecture/component-consolidation-master-plan-v0.1.md`, Phase 2
- Objective: four toys currently overlap on "look at or command
  FleetCore" (`toys/bridge/`, `toys/bridge-station-3.0/`,
  `toys/fleetcore-live/`, `toys/fleetcore-control/`). Consolidate into
  Bridge Station 3.0 as the one authoritative instrument, staged:
  1. Add the same embedded-panel tabs old Bridge already has (Fleet
     Motion + Periscope + Radio Console iframes; Radio Console already
     has an `is-embedded` CSS mode built for this).
  2. Fold FleetCore Control's spawn/despawn/Harbor-Pilot-Boarding
     commands in as an additional control panel.
  3. Add a raw-feed debug tab covering what FleetCore Live shows (Bridge
     Station 3.0 already consumes this same feed internally).
  4. Only once all three are verified live and equivalent: retire
     `toys/bridge/`, `toys/fleetcore-live/`, `toys/fleetcore-control/`
     (and their `web/toys/` copies, and any homepage links to them).
- Scope: `toys/bridge-station-3.0/` (a Vite-built React app -- requires a
  rebuild step, not a plain file copy, per `docs/deployment.md`), plus
  the retirement cleanup in step 4.
- Exclusions: do not retire anything before its replacement is verified
  live on the real deployed page. No FleetCore backend changes -- this is
  purely a frontend consolidation of existing capability.
- Constraint: single-owner packet. This touches one React app across
  multiple stages -- do not split across two sessions working
  concurrently without an explicit handoff, to avoid conflicting edits
  to the same source files.
- Done evidence: `https://cameronlampley.com/toys/bridge-station-3.0/`
  shows compositing panels, full command surface, and raw-feed tab, each
  verified live before the corresponding old toy is removed.
