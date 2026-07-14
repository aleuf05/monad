# Engineering Packet: FleetCore API 1.0
**Assigned to:** Commander Claude, Engineering Watch
**Authority:** Captain T, Command Intent Memo (this watch)
**Status:** Ready for implementation

## Objective
Stand up FleetCore as the sole authoritative world model for Monad. Bridge instruments (Fleet Motion, Periscope, future consoles) observe and command through the API only — no independent canonical state in any browser toy.

## In Scope (v1.0)
- Deterministic simulation engine (world state advances predictably from commands)
- Canonical world state, held only in FleetCore
- Stable API contract — JSON request/response, versioned from the start
- Append-only event log (all state-changing commands recorded)
- Snapshot generation (materialized current-state view, rebuildable from the log)
- Read endpoint(s): retrieve current world state
- Write endpoint(s): accept operator commands, apply deterministically, update world
- Read-only default for toys; explicit grant required for command authority

## Explicitly Out of Scope (deferred)
- Full event sourcing (log exists, but not yet the sole source of replay/rebuild logic)
- Binary serialization
- Performance optimization
- Networking beyond what v1 requires (no push/WebSocket commitment yet)
- Database integration
- Distributed deployment
- Advanced conflict resolution (single-writer assumption is fine for now)

## Deliverables
1. FleetCore service exposing read + write API (JSON over HTTP)
2. Append-only event log, written on every accepted command
3. Snapshot/current-state generation from the log
4. One reference bridge instrument (Fleet Motion or a minimal stub) reading state through the API to prove the contract works end-to-end
5. Short doc: API contract (endpoints, payload shapes) for future toy authors

## Acceptance Criteria (per Captain T's Definition of Success)
- [ ] FleetCore maintains canonical world state
- [ ] A browser instrument retrieves that world through the API
- [ ] An operator command is accepted through the API
- [ ] FleetCore updates the world deterministically
- [ ] Every connected instrument observes the same resulting state

## Design Constraint
Guiding question for every implementation decision: *can a future bridge instrument connect to FleetCore without knowing how FleetCore works internally?* If yes, the interface is succeeding.

## Open Items for Commander Claude to Resolve
- Language/framework choice (not specified in command intent — implementation discretion)
- Exact endpoint list and payload schema
- Snapshot cadence/trigger (on every write vs. periodic vs. on-demand)

## Reporting
Log progress under the standard Ship's Log format. Flag any point where a v1.0 constraint (e.g. no push transport) blocks a bridge instrument's requirements — that's a command-intent question, not an implementation one.
