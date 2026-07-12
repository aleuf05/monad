# Fleet Motion Full Live Roster Watch Log

Date: 2026-07-13
Operator: Lt. cgl
Objective: close the gap between what's actually in FleetCore's live world and what Periscope/Bridge/Fleet Motion's own map ever showed — confirmed via live testing that Bridge's Contact Roster reported 8 entries while FleetCore held 56 real vessels.

## Root cause

Periscope and Bridge don't read FleetCore directly — they read `MonadFleetState`, which Fleet Motion writes. In live mode, `applyLiveSnapshot()` matched incoming FleetCore vessels onto a **fixed 3-escort/4-contact local demo roster** (`FORMATION`/`NPC_CONTACTS`, originally built for local-simulation mode) by name keyword — e.g. a real vessel's callsign had to end in "ALPHA" to fill the "ESCORT ALPHA" slot. That keyword-matching existed to fix a real earlier bug (positional mismatch silently pairing "DHOW LANTERN"'s label with a different vessel's actual position), but its side effect was a hard cap: at most 7 vessels could ever be visible, and only ones whose names happened to match the seed roster's keywords. Every vessel spawned by this session's scenario work (Distress Call, Storm Convoy, Collision Course, Harbor Pilot Boarding, manual spawns) has a randomized-suffix callsign that never matches, so all of it was invisible in Periscope/Bridge/Fleet Motion's own map — real in FleetCore, visible only in FleetCore Control Center and FleetCore Live (which read the raw snapshot directly).

## Fix

`toys/fleet-motion/app.js`:

- `applyLiveSnapshot()`: `escortStates`/`contactStates` are now built directly from **every** real scout/passive-traffic vessel in the snapshot, using each vessel's own id/name/position — no matching against a fixed roster, no cap. Removed `matchByNameKeyword()` (dead code once nothing calls it); its positional-mismatch history is preserved in a shorter comment since the new approach sidesteps the problem structurally (nothing to mismatch when each vessel carries its own id).
- New `renderLiveVessels()`: a real dynamic marker pool (`Map<id, marker>`) that creates/updates/removes Leaflet markers to match whatever `escortStates`/`contactStates` currently contain. The original fixed `escortMarkers`/`contactMarkers`/`formationLinks` arrays (sized for the 3+4 local roster) are hidden once, on the first live snapshot, rather than reused — indexing into them past their fixed length would only ever show the first 3/4 real vessels.
- `updateFleetMarkers()` and `updateMarkerIcons()`: branch on `liveMode` — call `renderLiveVessels()` when live, run the original fixed-array logic unchanged otherwise.
- `syncTrails()`: capped the escort-trail loop at `trailLayers.length - 1` (the fixed roster's trail capacity) to avoid indexing out of bounds now that `escortStates` can be much longer in live mode. Per-vessel trails for live mode's dynamic roster aren't attempted — only the flagship's own trail (unaffected, always index 0) matters operationally there.
- `toys/fleet-motion/README.md`: documented the new live-mode roster behavior.

## Verification

Playwright against the real `fleetcore-serve` on this box:

- **Local simulation, forced offline** (`?fleetcoreServer=` pointed at a dead port, confirming true non-live behavior rather than relying on live-by-default silently succeeding): exactly 3 escort + 4 contact markers, `"4 passive contacts"` readout — unchanged from before this watch. Click-to-select still responsive.
- **Live mode**: real FleetCore counts (3 scouts, 52 passive-traffic at test time) matched exactly by on-screen marker counts and the `trafficStatus` readout. `MonadFleetState` in localStorage carried the full `escorts: 3, contacts: 52` — not capped.
- **Downstream**: loaded Fleet Motion (live) then Bridge in the same browser context (shared localStorage) — Bridge's Contact Roster showed 56 entries (was 8 before this fix), "55 shared contacts" readout. Screenshot of Bridge confirmed Periscope's embedded panel visually tracking real scenario-spawned vessels by name — `HARBOR TRAFFIC 2`, `WATER TEST`, `MAYDAY 78VA` — none of which were ever visible there before.
- Zero console/page errors across every run.

## Known follow-ups, not done here

- Per-vessel trails for live mode's dynamic roster are not rendered (only the flagship's trail). Would need a dynamic trail-layer pool mirroring `renderLiveVessels()`'s marker pool if wanted later.
- Bridge's Contact Roster and Periscope's contact strip have no pagination or virtualization — verified they still render and scroll correctly at 56 entries (existing `max-height`/`overflow-y: auto` CSS handles it), but neither was built with an unbounded, ever-growing list in mind (no despawn command exists, so this list only grows for as long as the server runs).

## Updated

- `toys/fleet-motion/app.js`
- `toys/fleet-motion/README.md`
