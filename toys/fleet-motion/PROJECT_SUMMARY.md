# Fleet Motion Toy Project Summary

## Project Purpose

Fleet Motion is a standalone browser toy inside the Monad repository. It explores how a small simulated fleet can move across a real map while making navigation decisions visible to the operator.

The project is intentionally lightweight. It is not production infrastructure, not connected to Monad agents, and not a real navigation system.

## Current State

The toy currently runs as static HTML, CSS, and JavaScript under `toys/fleet-motion/`.

It uses Leaflet with OpenStreetMap tiles loaded from a CDN. There is no backend, build step, package manager, database, authentication, telemetry feed, or deployment automation.

Implemented capabilities:

- Real map centered near the Strait of Hormuz.
- MONAD flagship plus three escort vessels.
- Click-to-set-course movement.
- Constant simulated speed with Pause, 1x, 10x, 100x, and 500x time controls.
- Eased acceleration, deceleration, and heading transitions.
- Visible course vector.
- Bounded, fading wake trails for all ships.
- Clickable ship info panel.
- Captain's Log for major simulation events.
- Rough rectangular land exclusion zones in the demo area.
- Rejection of destinations inside land boxes.
- Rejection of direct route legs crossing land boxes.
- Manual waypoint routing with staged intermediate legs.
- Route editing controls for undoing the newest waypoint, selecting/removing a
  waypoint, and canceling an active route while preserving current position.
- Segmented course line through accepted waypoints.
- Suggested detour waypoints when a direct route crosses a rough land box.
- Operator acceptance before a suggested detour starts.
- Independent escort motion with simple formation-slot chasing and land-box
  avoidance.
- Operator-selectable escort screen modes with visible formation-link lines.
- Polished command-console presentation with clearer hierarchy and denser telemetry cells.
- Reset and return-to-Hormuz controls.

## Design Intent

The core design intent is to make fleet movement understandable at a glance.

The operator should be able to see:

- Where the fleet is.
- Where MONAD is trying to go.
- Why a route is accepted or rejected.
- What has happened recently.
- How the simulation changes under time warp.

The toy favors visible decisions over hidden intelligence. Route planning is manual. Land awareness is approximate. The interface should feel like a small operational plot rather than a polished consumer app.

## Current Limitations

- Land awareness uses hand-drawn rectangular bounding boxes, not coastline data.
- Routes are straight-line segments between points.
- Waypoints are manual; there is no automatic rerouting.
- Suggested detours are simple box-corner candidates, not full route search.
- Escort autonomy is local screen behavior, not independent mission planning.
- Wake rendering uses multiple bounded SVG segments; this is visually richer but heavier than one flat polyline per vessel.
- Movement is approximate lat/lon interpolation, not maritime navigation.
- Motion smoothing is visual interpolation, not a physical propulsion model.
- There is no persistence. Reloading the page clears the route and log.
- There is no real AIS, weather, currents, traffic, hazards, or restricted-water data.
- It is not suitable for real navigation.

## Near-Term Direction

Route editing is now present at the basic operator-control level. The next
reasonable feature chunk is route quality:

- Show per-leg route health.
- Make rejected edits easier to see on the map.
- Add clearer mode labels for staged route versus active route.
- Consider lightweight scenario presets.

This would improve operator confidence without introducing full pathfinding.

## Study Questions

- Is manual waypoint planning enough for the intended exploratory use?
- Should the next realism step be better coastline data, route editing, or scenario design?
- What level of simulation fidelity is useful before the toy becomes too complex?
- Should this remain a standalone toy, or eventually become a public Fleet Command feature?
- What parts of the interface best communicate "operator decision" versus "automatic system decision"?
