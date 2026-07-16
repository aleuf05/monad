# Radio Console Content Activation — First Salvo

Date: 2026-07-15

## What changed

The live radio console now does more than speak isolated vessel-status flips.
It derives a denser watch from real FleetCore state:

- a baseline watch summary on the first live snapshot;
- explicit threads from captain controls, escort intents, and agent decisions;
- canonical ledger updates when FleetCore canon changes;
- structured narration from retained `vessel_events` using stable
  `event_seq`;
- existing vessel-status and fuel-threshold narration preserved.

This keeps the console grounded in the live vessel state instead of a scripted
playlist.

## What the new content covers

- routine watch establishment;
- ongoing requests awaiting decision;
- captain handoffs and runtime changes;
- route updates, waypoint arrivals, route completion, and holds;
- fuel-margin changes;
- canon ledger advances.

## What remains intentionally out of scope

- fabricated weather or environmental traffic;
- unlimited procedural generation;
- a separate synthetic scenario engine detached from FleetCore state;
- scripted fallback chatter.

## Validation

- `node --check web/toys/radio-console/app.js`

## Notes

The console still speaks only from live FleetCore snapshots and the retained
structured event tail. Silence remains a valid outcome when the world is quiet.
