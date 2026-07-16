# Engineering Order: Living Captain V0.1

Priority: High

Scope: Minimum spine only — five components, not the full ten-system
architecture

Doctrine: The standard is not artificial consciousness. The standard is
durable command presence. Narrative proposes. FleetCore decides. The record
persists.

Source: Admiral's packet, relayed 2026-07-15. This document reconstructs the
charter from that relay — no separate source file exists. Treat this as the
working referent; correct it directly if it misreads the original intent.

> Result — 2026-07-15: All five in-scope components implemented
> (`tools/living-captain/`). `demo_restart.py` ran against real live
> `fleetcore-serve` and `world-intake`, not fixtures: identity and
> `created_at` survived a hard drop-and-reassemble unchanged, `restart_count`
> advanced by exactly one, and the action log grew by exactly one entry with
> no gap or duplication. Sight adapters were delegated to and independently
> verified from Codex (mocked tests plus a separate live smoke check).
>
> **READY FOR CUSTODY/SPEND DESIGN.** Continued in
> [`living-captain-v0.2.md`](living-captain-v0.2.md).

## Mission

Give "the Captain" a presence that survives a restart with its identity and
history intact, can see real fleet state without being able to mutate it, and
leaves an inspectable record of what it did. Nothing about this order asks for
a mind. It asks for continuity: kill the process, start it again, and prove
nothing was lost or duplicated.

This is a spine, not the building. The other five systems below are named so
scope has a place to grow into later — none of them are in V0.1.

## Ten named systems

The full architecture, for reference. Only the five marked **[V0.1]** are in
scope for this order.

1. **Constitution** — the fixed rules a Captain instance operates under.
   Not rebuilt here: this is `CLAUDE.md`,
   `000_HIGHEST_PRIORITY_MONAD_CHARTER_2026-07-14.md`, and existing doctrine
   docs (`engineering-command-schema.md`, `captain-issue-reporting.md`).
   Deferred: a machine-readable form a Captain process loads at boot.
2. **Command state [V0.1]** — the minimum data that must survive restart.
3. **Memory** — longer-horizon reflection and identity drift. Deferred:
   reuse the existing `tools/living-fleet/memory` store rather than building
   a second one; no new work in V0.1.
4. **Sight [V0.1]** — read-only adapters onto real fleet/world state.
5. **Action [V0.1]** — the record of what the Captain did or proposed.
6. **Recovery [V0.1]** — restart without loss or duplication (proven by the
   demonstration, not a separate component).
7. **Custody** — what a Captain instance is and is not allowed to touch.
   Deferred: V0.1 has no write authority at all, so custody enforcement has
   nothing to gate yet. Required before any write path is added.
8. **Spend** — compute/cost budget for a persistent process. Deferred: V0.1
   is a bounded demonstration, not a standing service; budget matters once it
   runs unattended.
9. **Clients** — how humans reach it (Bridge, CLI, public page). Deferred:
   V0.1 has no client surface; it's proven by an operator-run demonstration
   script, not a UI.
10. **Demonstration [V0.1]** — the restart proof itself.

## V0.1 decomposition

### 1. Minimum persistent state

Define the smallest record a Captain instance needs to resume as *itself*
after a restart: stable identity, standing orders/context it was given, and a
pointer into command state 6 don't own or duplicate: fleet/world canon (that's
FleetCore's), World Intake's proposal queue, or Living Fleet's crew
memory — the Captain's own state references those by ID, it doesn't copy
them. Persist to disk in a form that survives an unclean process kill (same
bar as `fleetcore-serve` and `world-intake`: no fsync-less writes, no
in-memory-only state).

### 2. Captain assembly contract

Define the boot sequence: given persisted state + configuration, produce one
running Captain instance. This is the seam every other piece plugs into — the
function/constructor that composes state loading, sight adapters, and the
action-record writer into a single object, and that a restart calls again
identically. No hidden global state outside what component 1 persists; two
calls to the same constructor from the same persisted state must produce
equivalent instances.

### 3. First read-only sight adapters

Adapters are read-only, full stop — no adapter in V0.1 may issue a command
anywhere. Start with exactly two, both against existing live systems:

- FleetCore snapshot (`GET /snapshot` on `fleetcore-serve`) — current fleet
  state.
- World Intake's pending-proposal queue — what's awaiting Captain review.

Each adapter is a thin typed read, not a cache or a second copy of canon.

### 4. Action record

An append-only log of what the Captain did or proposed — same pattern as
FleetCore's `events.jsonl` and World Intake's provenance index. In V0.1,
"action" can only mean *recording an observation or a proposal*, because
nothing in this order grants write/command authority. Any actual canon
mutation still goes through FleetCore's existing authenticated command path,
same as everything else in this repo (`captain-issue-reporting.md`,
`living-world-intake-v0.1.md`). This is deliberate, not a placeholder: it
keeps V0.1 honest about the difference between "the Captain noted X" and "the
Captain changed X."

### 5. Restart demonstration

A script or test that: boots a Captain instance, has it observe real state
through both sight adapters, writes to the action record, kills the process
(not a graceful shutdown — a real kill, same rigor as the commissioning
rollback drills), reassembles it from persisted state via component 2, and
proves identity, prior action-record entries, and sight-adapter continuity
all survived unchanged. This is the acceptance test for the whole order —
V0.1 is not done until this passes against real `fleetcore-serve` and
`world-intake`, not fixtures standing in for them (per this repo's live-test
policy).

## Scope freeze

Do not build, in this order: any write/command authority for the Captain
(custody has no gate yet, so there's nothing to safely authorize); a client
UI or Bridge surface; a spend/budget meter; a second memory store separate
from `tools/living-fleet/memory`; a machine-readable constitution loader;
autonomous or scheduled operation (V0.1 runs only when an operator invokes
the demonstration); model-authored permissions, reactor state, vessel
movement, or safety status, per the same standing restriction already in
force for World Intake.

## Completion recommendation

Return exactly one of:

- READY FOR SPEND/CUSTODY DESIGN (V0.1 spine proven; next order defines
  write authority and its guardrails)
- READY WITH LIMITATIONS
- HOLD FOR CORRECTION
