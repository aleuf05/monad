# Monad Fleet Motion Mk2

A standalone browser experiment for moving a small simulated fleet across a
real-world map. It is deliberately separate from the Monad Bridge, doctrine,
agents, deployment automation, and production infrastructure.

Mk2 is a command-visualization pass over the V1 prototype. The priority is
legibility, motion feel, and a more deliberate operational display rather than
deeper simulation realism.

## Run Locally

```sh
cd toys/fleet-motion
python3 -m http.server 8080
open http://localhost:8080
```

On Linux, use `xdg-open http://localhost:8080` if the `open` command is not
available.

## Features

- Leaflet map with OpenStreetMap tiles
- MONAD flagship and three formation escorts
- Click-to-set-course navigation
- Visible course vector with a modest turn-arc presentation
- Frame-based simulated movement with smoothed heading transitions
- Eased acceleration, deceleration, and heading changes
- Time warp controls for Pause, 1x, 10x, 100x, and 500x
- Bounded, fading wake trails for each ship
- Clickable ships with a current ship info panel
- Captain's Log panel for course, warp, pause/resume, arrival, and reset events
- Rough land exclusion boxes around obvious Strait of Hormuz demo-area landmasses
- Destination and direct-route rejection when a course crosses a land box
- Manual waypoint routing with staged route legs
- Route editing controls for undoing, selecting, removing, and canceling routes
- Suggested detour waypoints when a route crosses a rough land box
- Independent escort motion; escorts chase nearby formation slots instead of
  being fixed to MONAD's exact position
- Escort screen modes: Tight Screen, Loose Screen, and Patrol Weave
- Scenario tuning controls for MONAD speed, escort speed scale, and formation spread
- Scenario presets for repeatable playtest drills
- Designer note fields for playtest observations and suggested changes
- Exportable scenario JSON for non-engineer design handoff
- Short skippable opening sequence
- Passive-viewer startup route so the fleet appears active without input
- Visual feedback for selection, waypoint creation, rejected navigation, route cancellation, escort mode changes, and reset
- Faint formation-link lines showing escort relationship to MONAD
- Live position, distance, ETA, and motion status
- Pause/resume, return-to-Hormuz, and reset controls

Use `Add Waypoint` to arm one waypoint placement, then click the map. After the
waypoint is staged, the next normal map click sets the final destination and
starts the route. Hold Shift while clicking to stage additional waypoints without
using the button. Each leg is checked against the rough land boxes before MONAD
accepts the route.

If a direct destination click crosses a rough land box, `Suggest Detour` tries a
small set of visible waypoint routes around the blocking box. `Accept Detour`
starts the suggested route. If no simple detour is found, use manual waypoints.

Use `Undo Waypoint` to remove the newest staged waypoint. Click a waypoint marker
to select it, then use `Remove Selected` to delete that point and re-check the
remaining staged route legs. `Cancel Route` stops an active route while keeping
MONAD at its current position.

The Captain's Log uses local browser time for simple human readability. It is
not persisted and is cleared when the page reloads.

## Design Console

The Design Console is the non-engineer collaboration layer. It lets a playtester
tune a small set of scenario parameters, play the result immediately, write
plain-language notes, and export a structured JSON artifact.

Scenario presets provide repeatable starting points:

- `Freeplay / Manual` leaves routing to the player.
- `Hormuz Transit` loads a baseline movement route.
- `Patrol Weave Review` loads wider escort spacing and the patrol maneuver mode.
- `Waypoint Threading` loads a tight-screen waypoint route.

The export includes:

- Tuned parameters
- Active scenario preset
- Current MONAD and escort positions
- Current route state
- Designer notes
- Standalone-toy constraints

The export is local only. It is shown in the page for copy/paste and can be
downloaded as a `.json` file. No backend, account, database, or deployment
automation is involved.

## Mk2 Combat Presentation Boundary

V1 briefly explored a single-contact threat drill. Mk2 removes that combat-game
presentation from the primary interface. The old threat code is retained only as
a disabled internal path guarded by `INTERNAL_FEATURES.threatDrill = false`; it
does not appear in the UI and does not affect normal exports.

Implementation notes for the current motion model live in `ENGINEERING_NOTES.md`.

## Intentionally Out of Scope

- Live AIS or vessel telemetry
- Realistic marine navigation or great-circle routing
- Full coastline routing, terrain models, restricted waters, or real marine safety checks
- Persistence, networking, authentication, or backend services
- Connections to the Monad site, Bridge, doctrine, Qdrant, or agents
- Weapons, damage, targeting, combat scoring, or tactical doctrine

Navigation v0.6 uses manually defined rectangular land bounding boxes, manual
waypoints, a small suggested-detour helper, and simple independent escort
slot-chasing. This prevents some obvious demo-area land crossings, but it is not
full pathfinding and does not represent real coastlines.

This toy is not for real navigation.
