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
- Time warp controls for Pause, 1x, 10x, and 100x
- Bounded wake trails for each ship
- Clickable ships with a current ship info panel
- Captain's Log panel for course, warp, pause/resume, arrival, and reset events
- Live position, distance, ETA, and motion status
- Pause/resume, return-to-Hormuz, and reset controls

The Captain's Log uses local browser time for simple human readability. It is
not persisted and is cleared when the page reloads.

## Intentionally Out of Scope

- Live AIS or vessel telemetry
- Realistic marine navigation or great-circle routing
- Collision avoidance, terrain checks, restricted waters, or global coastline routing
- Persistence, networking, authentication, or backend services
- Connections to the Monad site, Bridge, doctrine, Qdrant, or agents

Navigation v0.2 uses direct routes and may cross land.

This toy is not for real navigation.
