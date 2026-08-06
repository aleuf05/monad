# FleetCore

## Executive Summary

Deterministic maritime world-model prototype for vessels, routes, commands,
events, persistence, replay, and snapshots.

## Why It Matters

It provides an inspectable stateful world substrate for Monad's maritime
instruments and tests the move from isolated browser state toward authoritative
world state.

## Current Status

Implemented prototype; operational posture and public command exposure require
review against current deployment evidence.

## What Exists

Rust source, CLI, server, data contracts, replay and architecture documents.

## What Is Demonstrated

Repository reports and FleetCore documentation demonstrate a designed and
implemented deterministic model; live-state claims remain date-specific.

## What Is Not Yet Demonstrated

That FleetCore is the sole or final center of Monad's cognitive architecture.

## Major Decisions

Deterministic state, event history, replay, and snapshots are central design
concerns.

## Risks and Limitations

Deployment documentation records intentionally permissive demo command access.

## Open Questions

How should FleetCore relate to private Admiralty authority and public projections?

## Recommended Next Action

Use the current architecture and deployment reports to reconcile live status.

## Source Record

[`fleetcore/README.md`](../../../../fleetcore/README.md),
[`docs/architecture/fleetcore.md`](../../../../docs/architecture/fleetcore.md),
[`docs/architecture/fleetcore-api.md`](../../../../docs/architecture/fleetcore-api.md)

## Confidence and Reconstruction Notes

High for existence and design; mixed for current operational state.
