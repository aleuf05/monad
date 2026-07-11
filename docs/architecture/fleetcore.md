# FleetCore Architecture Study Mk I

FleetCore is the proposed canonical stateful world model for Monad.

Its purpose is to answer one question:

```text
What is true right now, even if no browser is open?
```

Browsers render. FleetCore remembers. Bridge instruments observe. Agents interact through defined commands and events.

FleetCore is not a replacement for Fleet Motion, Periscope Station, Watchbook, or Bridge Station. It is the future authoritative world layer beneath those instruments.

## Definition

FleetCore is a persistent deterministic simulation service that owns Monad's maritime world state.

FleetCore SHALL own:

- simulation clock,
- canonical entity registry,
- vessel state,
- navigation routes,
- event history,
- deterministic simulation ticks,
- persistence,
- world snapshots.

FleetCore SHALL NOT own:

- HTML,
- CSS,
- Canvas rendering,
- Periscope rendering,
- Fleet Motion rendering,
- UI layout,
- browser interaction.

## Current Context

The current system is still browser-first:

- Fleet Motion writes browser-local state under `localStorage["monad.fleetMotion.state"]`.
- Bridge Station observes that state when available.
- Periscope Station still has local demo contacts, with a documented path toward shared contact consumption.
- Passive Fleet Motion contacts now demonstrate that one browser instrument can publish a larger operational picture.

That is enough to prove the direction, but it is not enough to make the world persistent beyond a browser session.

FleetCore should be introduced only after the shared browser-state contract has stabilized.

## Responsibility Boundaries

FleetCore owns truth. Instruments own presentation.

FleetCore should know:

- which entities exist,
- where they are,
- what they are doing,
- what commands were accepted,
- what events occurred,
- what simulation tick produced the current state.

FleetCore should not know:

- how a marker looks on a Leaflet map,
- how Periscope projects a contact into a canvas,
- how Bridge panels are arranged,
- how a control is clicked or touched,
- how text wraps in a browser.

This separation protects FleetCore from becoming a UI backend shaped by one instrument's needs.

## Proposed Layered Architecture

```text
FleetCore
|
+-- World Clock
+-- Entity Registry
+-- Simulation Engine
+-- Route Engine
+-- Event Log
+-- Persistence
+-- Snapshot Export
        |
        v
Shared World State
        |
        +-- Fleet Motion
        +-- Periscope Station
        +-- Bridge Station
        +-- Future Radar
        +-- Scout Status Board
        +-- Future Bridge Instruments
```

Each component has one primary responsibility.

World Clock:
Controls simulation time, fixed ticks, pause, acceleration, replay position, and deterministic restart metadata.

Entity Registry:
Stores canonical entities by stable ID. It owns identity, type, lifecycle state, and references between entities.

Simulation Engine:
Applies deterministic movement and behavior rules to entities for each tick. It should be small and auditable at first.

Route Engine:
Owns route plans, active legs, route validation, navigation constraints, and future pathfinding policy.

Event Log:
Records accepted commands, simulation events, state transitions, warnings, and noteworthy observations.

Persistence:
Writes event log entries and periodic snapshots to durable local storage.

Snapshot Export:
Produces browser-consumable JSON snapshots and deltas. It translates core truth into stable external contracts.

## Entity Model

FleetCore should use a canonical entity registry with typed components rather than one giant vessel object.

Recommended high-level entity shape:

```json
{
  "id": "vessel.monad",
  "kind": "vessel",
  "displayName": "MONAD",
  "createdAtTick": 0,
  "updatedAtTick": 1200,
  "components": {
    "position": {},
    "motion": {},
    "navigation": {},
    "identity": {},
    "operationalStatus": {}
  }
}
```

The component vocabulary can stay small at first:

- `identity`: display name, callsign, class, allegiance or ownership.
- `position`: latitude, longitude, optional altitude/depth later.
- `motion`: course, heading, speed, acceleration model if needed.
- `navigation`: active route, destination, waypoint queue, route status.
- `operationalStatus`: nominal, holding, underway, blocked, degraded, offline.
- `observation`: confidence, source, last observed tick, sensor class.
- `port`: berth capacity, location, services, status.
- `aidToNavigation`: beacon, buoy, lighthouse, channel marker, status.
- `environment`: weather cell, current, visibility region, restricted water.
- `agentControl`: future autonomous owner, command policy, intent.

## Canonical Entity Categories

Monad flagship:
The primary commanded vessel. It has full identity, position, motion, navigation, operational status, command history, and agent-control metadata later.

Escort vessels:
Vessels with formation, station-keeping, screen mode, and relationship components tied to MONAD. They remain independent entities, not offsets on MONAD.

Merchant traffic:
Passive or semi-autonomous vessels with position, motion, route intent, and behavior class. Early traffic can remain deterministic and simple.

Ports:
Static or slowly changing entities with location, capacity, service state, and operational status. Ports should not be UI pages.

Harbors:
Operational regions containing ports, anchorages, channels, restrictions, and local traffic rules.

Navigation aids:
Static or movable entities used by route validation and instruments. They should be visible to browsers but owned by FleetCore.

Environmental contacts:
Weather, sea state, restricted waters, visibility zones, debris, and other non-vessel world state. Start with simple regions, not fluid simulation.

Future autonomous agents:
Entities or controllers that submit commands to FleetCore. Agents should not mutate state directly; they request actions through command interfaces.

## Browser Interface

FleetCore should expose state through display-neutral contracts:

- JSON world snapshot,
- JSON event stream,
- optional polling endpoint,
- local development file export,
- deterministic replay export.

Browsers should consume snapshots and events. They should not own canonical truth.

Recommended first browser-facing snapshot:

```json
{
  "schemaVersion": "monad.worldSnapshot.v1",
  "worldId": "monad.local",
  "tick": 1200,
  "simTime": "2026-07-10T20:00:00Z",
  "timeScale": 1,
  "entities": [],
  "eventsSince": [],
  "generatedAt": "2026-07-10T20:00:01Z"
}
```

Fleet Motion can render map markers from it. Periscope can derive bearing and range from it. Bridge can summarize operational status from it.

## Command Interface

Agents and future controls should interact with FleetCore through commands, not direct state mutation.

Examples:

- `SetRoute`
- `PauseClock`
- `ResumeClock`
- `SetTimeScale`
- `SpawnTraffic`
- `UpdateVesselIntent`
- `RecordWatchEvent`

Each accepted command should become an event with:

- command ID,
- actor,
- validation result,
- affected entities,
- tick accepted,
- deterministic payload.

Rejected commands should also be recorded when operationally useful.

## Recommendation

FleetCore should be designed now, but implemented later.

Recommended next sequence:

1. Keep Fleet Motion as the current browser-local state writer.
2. Extract shared browser state helpers into `toys/shared/`.
3. Let Periscope consume shared browser state with local fallback.
4. Define FleetCore contracts and fixtures in docs.
5. Build a minimal FleetCore prototype only after the static shared contract proves stable.

This avoids a big-bang rewrite while preserving the architecture FleetCore will eventually need.
