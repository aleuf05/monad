# FleetCore Data Contract

FleetCore v1 uses JSON files for seed state, current world state, events, checkpoints, and browser-facing snapshots.

## Canonical Units

- Position: decimal latitude and longitude.
- Course: degrees true, normalized to `0 <= x < 360`.
- Speed: meters per second.
- Time: deterministic simulation timestamp derived from seed start time and tick.

Adapters may expose kilometers per hour or knots, but FleetCore stores meters per second.

## Seed And World Shape

`fleetcore/data/seed-world.json` and `data/fleetcore/world.json` use the same shape:

```json
{
  "schema_version": "monad.fleetcore.world.v1",
  "world_id": "monad.local",
  "clock": {
    "tick": 0,
    "tick_duration_seconds": 1,
    "time_scale": 1,
    "state": "running",
    "start_unix_seconds": 1783713600
  },
  "vessels": [],
  "event_sequence": 0,
  "watch_events": []
}
```

## Vessel Shape

```json
{
  "id": "vessel.monad",
  "name": "Monad",
  "callsign": "MONAD",
  "kind": "flagship",
  "position": { "lat": 26.56, "lng": 56.25 },
  "course": 270.0,
  "speed_mps": 20.0,
  "status": "underway",
  "route": [{ "lat": 26.25, "lng": 55.35 }],
  "last_update": "2026-07-10T20:00:00Z"
}
```

Allowed v1 vessel kinds:

- `flagship`
- `scout`
- `passive-traffic`

Allowed v1 statuses:

- `holding`
- `underway`
- `paused`
- `transiting`
- `arrived`

## Event Log

`data/fleetcore/events.jsonl` is append-only JSON Lines.

Each line is one event:

```json
{
  "sequence": 1,
  "tick": 0,
  "event_type": "time-scale-set",
  "command": {
    "type": "set-time-scale",
    "scale": 10
  },
  "sim_time": "2026-07-10T20:00:00Z"
}
```

Events are replayed in file order.

## Snapshot Shape

`data/fleetcore/snapshots/snapshot.json` is the browser-facing contract:

```json
{
  "schema_version": "monad.worldSnapshot.v1",
  "world_id": "monad.local",
  "tick": 120,
  "sim_time": "2026-07-10T20:02:00Z",
  "clock_state": "running",
  "time_scale": 1,
  "tick_duration_seconds": 1,
  "vessels": [],
  "watch_events": [],
  "event_sequence": 3
}
```

This snapshot is display-neutral. It does not include Leaflet marker state, Periscope projection fields, CSS, or UI selection state.

## Browser Adapter Boundary

`toys/shared/fleet-state.js` defines:

- `MonadFleetState.read()`
- `MonadFleetState.normalize(state)`
- `MonadFleetState.toScoutContacts(state)`
- `MonadFleetState.fromFleetCoreSnapshot(snapshot)`

The FleetCore adapter converts:

- FleetCore `flagship` into browser `flagship`,
- FleetCore `scout` vessels into shared contacts,
- FleetCore `passive-traffic` vessels into passive shared contacts,
- meters per second into kilometers per hour for the current browser-side state shape.

This is a bridge contract, not a live integration layer.

## Compatibility Rule

FleetCore must not export browser-specific presentation fields.

Browser instruments may derive:

- relative bearing,
- range,
- visibility,
- projected x/y,
- marker style,
- label text.

FleetCore remains the source of world truth only.
