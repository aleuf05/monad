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
- Four passive local-traffic NPC contacts
- Click-to-set-course navigation
- Visible course vector with a modest turn-arc presentation
- Frame-based simulated movement with smoothed heading transitions
- Eased acceleration, deceleration, and heading changes
- Time warp controls for Pause, 1x, 10x, 100x, and 500x
- Bounded, fading wake trails for each ship
- Clickable ships with a current ship info panel
- Captain's Log panel for course, warp, pause/resume, arrival, and reset events
- Rough land exclusion boxes retained for route-planning demos
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
- Pause/resume, return-to-station, and reset controls

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

## Quarantined Scenario Tools

The Scenario Editor/Evaluator is intentionally out of the normal Fleet Motion
experience. Its implementation is retained in `app.js` behind
`INTERNAL_FEATURES.scenarioTools = false` for possible future restoration, but
there are no UI entry points and it does not run in the default application
flow.

The active surface is the navigation engine: movement, routing, formation
behavior, persistence, time warp, ship inspection, and the Captain's Log.
## Persistent Fleet State

Fleet Motion stores the current voyage in `localStorage` under the key
`monad.fleetMotion.state`. Startup attempts to restore that state before loading
any baseline route. If saved state exists, ordinary reloads and browser restarts
resume the current voyage instead of silently returning MONAD to the Arabian
Sea watch baseline.

The persisted schema is versioned:

```json
{
  "schemaVersion": 2,
  "savedAt": "ISO-8601 timestamp",
  "activePresetId": "arabian_sea_watch",
  "designSettings": {
    "flagshipSpeedKmh": 180,
    "escortSpeedScale": 1,
    "formationSpread": 1
  },
  "flagship": {
    "position": { "lat": 20.5, "lng": 63.2 },
    "headingDegrees": 270,
    "speedKmh": 120,
    "engineOrderKmh": 180
  },
  "navigation": {
    "destination": { "lat": 20.28, "lng": 62.82 },
    "finalDestination": { "lat": 20.28, "lng": 62.82 },
    "waypoints": [],
    "routeQueue": [],
    "waypointMode": false,
    "selectedWaypointIndex": null,
    "lastStatus": "Underway",
    "lastNavigationMessage": "Clear"
  },
  "time": {
    "timeWarp": 1,
    "lastMovingWarp": 1,
    "simulationClockSeconds": 0
  },
  "escorts": {
    "modeIndex": 1,
    "modeId": "loose",
    "formation": [],
    "ships": []
  },
  "contacts": {
    "mode": "passive",
    "ships": [
      {
        "id": "traffic-dhow-01",
        "name": "DHOW LANTERN",
        "role": "civilian dhow",
        "position": { "lat": 20.58, "lng": 63.29 },
        "speedKmh": 32,
        "headingDegrees": 312,
        "status": "Transiting"
      }
    ]
  },
  "selection": {
    "selectedShipId": "monad"
  }
}
```

## Passive Traffic NPCs

Fleet Motion includes four deliberately simple local-traffic contacts. They are
not tactical units and do not plan routes. Each contact holds a speed and
heading, turns when it reaches the toy's operating bounds or a rough land box,
and remains selectable through the existing ship details panel.

These contacts are persisted under `contacts.ships` in the canonical browser
state so Bridge Station can observe them without coupling to Fleet Motion's DOM.

`Reload Saved State` reloads the current voyage from `localStorage`. It does not
return MONAD to the Arabian Sea watch baseline. Applying a scenario preset still
requires confirmation because it replaces the current voyage with a documented
preset scenario.


## Persistent State Manual Test Checklist

1. Run the toy locally and let the opening route start.
2. Move MONAD away from the baseline position by selecting a new destination.
3. Change MONAD speed, time warp, and escort mode.
4. Add at least one waypoint or route edit.
5. Wait until `Last State Saved` updates.
6. Reload the page.
7. Confirm MONAD, escorts, heading, speed/order, time warp, route state, and escort mode are restored.
8. Close and reopen the browser, then open the toy again.
9. Confirm the same saved state is restored and startup does not teleport to the Arabian Sea watch baseline.
10. Click `Reload Saved State`; confirm the page reloads the saved voyage from `localStorage`.
11. Confirm the button does not teleport MONAD back to the Arabian Sea watch baseline.


## State Inspector

The State Inspector exposes the active canonical fleet-state model in the command
panel. It is intended for LT/debug visibility, not as a simulation mechanic.

It shows:

- schema version
- saved timestamp
- active route profile
- flagship position and heading
- speed and time warp
- route-leg and waypoint counts
- escort mode and vessel count
- passive contact count
- selected ship

Controls:

- `Copy State JSON` forces a save and copies the persisted state JSON when browser permissions allow it.
- `Download State JSON` forces a save and downloads the current persisted state JSON.
- `Clear Saved State` removes the state from this browser after confirmation and pauses autosave for the current page session so the store is not immediately recreated by animation.

## Mk2 Combat Presentation Boundary

V1 briefly explored a single-contact threat drill. Mk2 removes that combat-game
presentation from the primary interface. The old threat code is retained only as
a disabled internal path guarded by `INTERNAL_FEATURES.threatDrill = false`; it
does not appear in the UI and does not affect normal operation.

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
