# Engineering Order: Living Captain V0.2

Priority: High

Scope: Custody and spend only — still zero canon write authority

Doctrine: The standard is not artificial consciousness. The standard is
durable command presence. Narrative proposes. FleetCore decides. The record
persists.

Predecessor: [`living-captain-v0.1.md`](living-captain-v0.1.md) — the
persistent-state/sight/action/recovery spine, live-demonstrated 2026-07-15.

> Result — 2026-07-15: Custody and spend boundaries implemented in
> `tools/living-captain/`. The read adapter now rejects non-GET and
> out-of-manifest requests before network I/O. The Captain persists its
> custody manifest and observe budget, logs custody rejections and spend
> exhaustion, and the restart demo plus unit tests prove the ceiling survives
> restart without silent reset.
>
> **READY FOR WRITE-PATH DESIGN.**

## Mission

V0.1 deferred custody and spend with an explicit reason: "custody has no
gate yet, so there's nothing to safely authorize." This order builds that
gate — and a spend ceiling to go with it — but still does not grant the
Captain any canon-mutating authority. That is a deliberate two-step: prove
the boundary mechanism works and survives restart before there is anything
dangerous for it to bound. A V0.3 order, not this one, is where an actual
narrow write path would be proposed, and only after this gate is live and
tested.

## Components

### 6. Custody boundary

A declarative manifest of what a Captain instance may reach, checked before
every outbound call `sight.py` makes — not just documented convention, an
enforced gate. V0.2's manifest permits exactly the two read endpoints
already in use (FleetCore snapshot, World Intake pending queue) and
authorizes zero write endpoints. Any attempt to call through `sight.py`
(or a future module) against a URL not on the read-allowlist, or any
attempt to issue a non-GET request at all, must be rejected before the
network call happens, with a clear exception naming what was blocked —
never a silent no-op and never a silent pass-through.

This is infrastructure for a boundary that has nothing to bound yet in
V0.2, and that is the point: prove the gate rejects correctly now, while
the cost of getting it wrong is zero, not later once a real write path
depends on it.

### 7. Spend boundary

A bounded ceiling on how much a single assembled instance may do before it
must be reassembled. V0.2's ceiling is the simplest thing that's real: a
maximum number of `observe()` calls per assembled instance (a fixed
constant is fine — Command may tune it later), persisted alongside the
rest of captain state so it survives restart correctly. Once the ceiling
is hit, further `observe()` calls raise a clear, named exception rather
than silently continuing or silently truncating; reassembly (an
operator-driven action, same as today) is what resets it. There is no
scheduler or unattended loop in V0.2 — this proves the concept for when
one eventually exists, it does not require building one now.

## Required behavior

- Custody rejection is enforced code, not a comment or a docstring.
- Custody state (the manifest itself) and spend state (the call counter)
  both persist through `captain_state.py` and survive the same restart
  discipline V0.1 already proved — no new persistence mechanism.
- A rejected custody check and an exhausted spend ceiling are each
  recorded as their own `action_log.py` entry kind
  (`custody_rejection`, `spend_exhausted`) so the record shows *why*
  something didn't happen, not just that it didn't.
- Extend `demo_restart.py` (or add a sibling demonstration script) to
  prove, against real live services:
  1. an out-of-manifest URL is rejected before any network call is made;
  2. hitting the spend ceiling blocks further observation with a named
     exception;
  3. both the manifest and the exhausted-ceiling state persist correctly
     across a restart — a reassembled instance does not silently regain
     allowance it had already spent.

## Scope freeze

Do not add: any canon-mutating write path (still zero — that's V0.3 at the
earliest, and only after this gate is live); a scheduler or autonomous
unattended loop; a client/UI surface; a machine-readable constitution
loader; a second memory store separate from `tools/living-fleet/memory`;
configurable/operator-editable manifests through a network surface (the
manifest is a code-level constant in V0.2, not something remotely
mutable). Do not fold in any FleetCore or World Intake behavior change —
this order only touches `tools/living-captain/`.

## Completion recommendation

Return exactly one of:

- READY FOR WRITE-PATH DESIGN (custody/spend gate proven; V0.3 may propose
  the first narrow write capability against it)
- READY WITH LIMITATIONS
- HOLD FOR CORRECTION
