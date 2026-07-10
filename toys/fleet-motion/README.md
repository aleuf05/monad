# Monad Fleet Motion Toy

A standalone browser experiment for moving a small simulated fleet across a
real-world map. It is deliberately separate from the Monad Bridge, doctrine,
agents, deployment automation, and production infrastructure.

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
- Visible course vector
- Constant-speed simulated movement
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
- Single-contact threat drill with automatic escort interception
- Simple score: hostile contacts neutralized and screen breaches
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

- `Freeplay / Manual` leaves routing and threats to the player.
- `Hormuz Transit` loads a baseline movement route.
- `Escort Screen Drill` loads wider escort spacing and starts a hostile contact.
- `Waypoint Threading` loads a tight-screen waypoint route.

The export includes:

- Tuned parameters
- Active scenario preset
- Current MONAD and escort positions
- Current route state
- Current threat drill state and score
- Designer notes
- Standalone-toy constraints

The export is local only. It is shown in the page for copy/paste and can be
downloaded as a `.json` file. No backend, account, database, or deployment
automation is involved.

## Threat Drill

`Spawn Threat` creates one hostile contact southeast of the fleet. The contact
drives toward MONAD. If an escort comes within the intercept radius, the contact
is neutralized. If the contact reaches MONAD's inner screen first, it records a
breach.

This is intentionally a toy mechanic:

- No weapons model
- No hit probability
- No faction model
- No live contacts
- No tactical doctrine

It exists only to make escort spacing, speed, route choice, and player notes more
testable.

Implementation notes for the current motion model live in `ENGINEERING_NOTES.md`.

## Intentionally Out of Scope

- Live AIS or vessel telemetry
- Realistic marine navigation or great-circle routing
- Full coastline routing, terrain models, restricted waters, or real marine safety checks
- Persistence, networking, authentication, or backend services
- Connections to the Monad site, Bridge, doctrine, Qdrant, or agents

Navigation v0.6 uses manually defined rectangular land bounding boxes, manual
waypoints, a small suggested-detour helper, and simple independent escort
slot-chasing. This prevents some obvious demo-area land crossings, but it is not
full pathfinding and does not represent real coastlines.

This toy is not for real navigation.
