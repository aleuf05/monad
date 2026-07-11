# FleetCore Migration Plan

FleetCore should arrive through evolutionary extraction, not a big-bang rewrite.

Current Monad instruments must remain operational at every stage.

## Target Direction

```text
Current independent browser toys
        |
        v
Shared Fleet State
        |
        v
Bridge Station
        |
        v
FleetCore
        |
        v
Persistent Maritime World
        |
        v
Agent-operated Fleet
```

## Stage 0: Current State

Status: active.

Current characteristics:

- Fleet Motion owns browser-local vessel state.
- Bridge Station reads Fleet Motion local state opportunistically.
- Periscope owns local demo contacts.
- Passive Fleet Motion contacts are now persisted in Fleet Motion state.
- No backend is required.

Value:

- Fast iteration.
- Static artifacts remain easy to run.
- Instruments prove product feel.

Limitation:

- The world stops existing when the browser state is absent or stale.

## Stage 1: Shared Browser State

Goal:

Extract a small shared state contract without adding a backend.

Deliverables:

- `toys/shared/fleet-state.js`
- schema version constants,
- storage key constants,
- normalization helpers,
- contact adapter helpers,
- browser-safe read/write utilities.

Fleet Motion:

- remains the writer,
- imports or consumes shared helpers,
- keeps existing UI and behavior.

Bridge:

- reads through shared helpers rather than hand-parsing local storage.

Periscope:

- reads shared contacts when available,
- falls back to local demo contacts when no shared state exists.

Acceptance:

- All toys still run statically.
- Periscope can observe at least MONAD escorts or passive contacts from shared state.
- No backend exists yet.

## Stage 2: Explicit Shared Contact Contract

Goal:

Stabilize the contract that instruments observe.

Deliverables:

- `monad.worldSnapshot.v0` or `monad.fleetState.v2` document,
- `monad.contact.v1` document,
- unit policy,
- entity ID policy,
- migration notes from current `monad.fleetMotion.state`.

Key decisions:

- latitude/longitude are canonical,
- bearings and ranges are derived by instruments or adapters,
- speed units are explicit,
- UI selection state is not canonical world truth,
- source and confidence are included for observed contacts.

Acceptance:

- Browser instruments consume state through a display-neutral shape.
- Periscope-specific projection fields are not embedded in the shared model.
- Fleet Motion Leaflet details are not embedded in the shared model.

## Stage 3: Bridge Station As Primary Observer

Goal:

Bridge becomes the main demonstration artifact for the shared operational picture.

Deliverables:

- Bridge reads shared state through a helper.
- Engineering Status reports schema, tick or saved timestamp, entity counts, and active route summary.
- Bridge keeps iframe composition while state contracts stabilize.

Acceptance:

- Visitors can see Fleet Motion, Periscope, Watchbook, and Engineering Status as one ship.
- Existing standalone toys remain useful.

## Stage 4: FleetCore Prototype

Goal:

Build the first non-browser source of truth.

Scope:

- local process only,
- no cloud deployment,
- no authentication,
- no multiplayer,
- no production database.

Recommended deliverables:

- seed world file,
- deterministic tick loop,
- entity registry,
- route advancement,
- append-only JSONL event log,
- periodic JSON snapshots,
- command-line replay tool,
- JSON snapshot export compatible with browser shared-state fixtures.

Acceptance:

- FleetCore can run without a browser.
- FleetCore can emit a snapshot consumed by a simple browser adapter.
- Replaying seed plus events produces the same snapshot hash.

## Stage 5: Browser Adapter

Goal:

Let current browser instruments observe FleetCore snapshots while preserving static fallback.

Possible modes:

- local polling from `http://localhost`,
- static snapshot file loaded from `docs` or `out`,
- development event stream,
- localStorage bridge adapter for compatibility.

Recommended order:

1. Static JSON snapshot fixture.
2. Manual refresh polling.
3. Local event stream only after snapshot contracts are stable.

Acceptance:

- Fleet Motion can render a FleetCore snapshot.
- Periscope can project contacts from a FleetCore snapshot.
- Bridge can summarize FleetCore state.
- If FleetCore is absent, toys still use browser-local fallback.

## Stage 6: Persistent Maritime World

Goal:

FleetCore becomes the long-lived local world service.

Capabilities:

- durable world state,
- restart recovery,
- replay,
- watch logs,
- port and harbor entities,
- navigation aids,
- passive traffic,
- environmental contacts.

Acceptance:

- The world continues across browser sessions.
- Bridge instruments become observers of persistent state.
- Fleet Motion no longer needs to be the authoritative state writer, but can still be a control/display surface.

## Stage 7: Agent-operated Fleet

Goal:

Agents submit commands to FleetCore through a narrow command interface.

Rules:

- agents do not mutate state directly,
- every accepted command becomes an event,
- every rejected command can be audited,
- human-facing instruments remain observers and controls.

Example commands:

- set route,
- request patrol pattern,
- spawn passive contact,
- record watch note,
- change time scale,
- pause simulation.

Acceptance:

- Agent actions are replayable.
- Agent decisions are visible in event history.
- Human instruments can inspect what happened.

## Compatibility Rules

Every stage must preserve:

- standalone Fleet Motion operation,
- standalone Periscope operation,
- standalone Bridge operation,
- static browser development path,
- documented fallback behavior.

Do not require FleetCore just to open a toy until FleetCore is stable and clearly valuable.

## Risks And Mitigations

Architectural risk:
FleetCore becomes a UI backend shaped around one instrument.

Mitigation:
Keep browser-specific fields out of FleetCore snapshots. Put projection in adapters.

Scaling risk:
The event log or snapshot model is overbuilt before real scale exists.

Mitigation:
Start with JSONL and JSON snapshots. Add indexed storage only when query needs are real.

Synchronization risk:
Browsers show stale state or disagree with FleetCore.

Mitigation:
Include tick, generated timestamp, schema version, and source in every snapshot.

Over-engineering risk:
FleetCore absorbs ports, weather, agents, and traffic before vessel truth is stable.

Mitigation:
First prototype only MONAD, escorts, passive traffic, routes, ticks, events, and snapshots.

Premature optimization risk:
Binary protocols or complex networking distract from domain clarity.

Mitigation:
Use JSON until it is proven insufficient.

## Recommended Next Implementation Sprint

Do not start by building FleetCore.

Recommended next sprint:

Shared Fleet State Extraction Mk I.

Scope:

- create `toys/shared/fleet-state.js`,
- move schema constants and pure normalization helpers out of Fleet Motion,
- add adapter from Fleet Motion state to display-neutral contacts,
- update Bridge to use shared helper,
- update Periscope to consume shared contacts with fallback,
- validate all three browser instruments.

That sprint removes uncertainty needed before FleetCore can be implemented cleanly.
