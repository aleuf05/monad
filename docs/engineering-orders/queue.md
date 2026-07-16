# Shared engineering task queue

Protocol: see [`AGENTS.md`](../../AGENTS.md) at the repo root. Non-privileged,
git-only tasks only — nothing requiring `sudo` (that stays in `cmd.sh` /
`commissioning-handoff.md`).

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
