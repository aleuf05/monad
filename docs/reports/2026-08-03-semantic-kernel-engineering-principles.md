# Semantic Kernel Engineering Principles — Design Proposal

Date: 2026-08-03

Prepared for: Admiral

Scope: two related transmissions -- "Chief Handoff Packet: Semantic Kernel
Engineering Principles v0.1" and "Chief Work Card 004: Focus Study —
Semantic Physics." Recorded per [[monad-transmission-posture]]:
documentation only, nothing built. Unlike the PMA hardware transmissions,
neither of these makes a checkable false claim -- both are pure design
proposals, so this report is an assessment against real repo state, not a
refusal.

## What was proposed

**Semantic Kernel v0.1:** meaning is the primary state; conversation,
story, images, simulation, hardware, and FleetCore are all *projections* of
one underlying semantic world, none of them canonical on their own. A
kernel holds stable identities, explicit relationships, append-only
history, and immutable provenance; every transformation must declare what
it preserves, what it changes, what it introduces, and its provenance.
Engineering rules: identity changes rarely, appearance changes freely,
history accumulates, relationships are first-class, unknown information
stays explicit, contradictions become investigation tasks.

**Semantic Physics (Work Card 004):** reframe entities not as "what they
are" but as "what they tend to cause" -- a campfire has a field of
influence (gathering +++++, conversation ++++, warmth +++++, danger ++,
exploration -, sleep ++) that nearby entities respond to per their own
state, and stories emerge from these fields interacting rather than being
authored (a broken engine attracts mechanics, which need tools, which need
storage, which becomes logistics, which becomes a mission -- no one wrote
that chain).

## Verified starting state

No file, class, or schema named anything like "semantic kernel," "semantic
field," or "semantic physics" exists anywhere in this repository today.
But three independent, already-real parts of this project have already
converged on large pieces of the same idea, unprompted:

1. **This repo's own `CLAUDE.md` (Canon and Evidence section)** already
   states almost exactly the kernel's "unknown information remains
   explicit" and provenance rules: "distinguish canon, proposal,
   reconstruction, uncertainty, and superseded material... preserve source
   paths and provenance... do not invent missing history." The Semantic
   Kernel's rules aren't a new constraint on Monad -- they're a
   generalization of a constraint this project already enforces on itself.
2. **FleetCore** (`fleetcore/src/event.rs`, `canon.rs`, `world.rs`,
   `snapshot.rs`) already separates events, canonical world state, and
   snapshots -- the same append-only-history-plus-canon shape the kernel
   proposes, in a real, running service (`fleetcore-serve.service`).
3. **The Living Basin** (`web/toys/living-basin/engine.js`) already
   implements almost exactly "Semantic Physics" empirically: a
   causal-event/feature/lineage model where every feature on the 64x64
   basin traces back through a `causedBy` chain to a `genesisId`, and the
   toy's entire pitch (per `build.html`'s own description) is "click any
   water pool, trail, or gully to inspect the exact recorded events that
   caused it" -- emergent causal chains from interacting local rules,
   not authored narrative. This is the closest thing in the repo to a
   working prototype of the campfire/storm/library influence-field idea,
   already built and live.

## Assessment

The kernel's core thesis (meaning as primary state, everything else a
projection) is a coherent, defensible architectural stance, and the
"append-only, immutable provenance, explicit relationships" rules are
genuinely good engineering discipline -- not because they're novel, but
because they're the same discipline this project already holds itself to
in `CLAUDE.md` and already partially built in FleetCore. That consistency
is a point in this proposal's favor: it's not asking Monad to adopt a
foreign practice, it's asking Monad to name and generalize a practice three
separate parts of it already arrived at independently.

The Semantic Physics work card is the more speculative half, and its own
stated research question is the right one to ask before building anything:
*can influence-field interactions produce coherent, human-understandable
emergent behavior, or just noise?* The Living Basin is real, live evidence
this can work at small scale (its causal chains are legible enough that a
UI can present them to a user as "why this gully exists"). The honest
open risk, not addressed in the work card: Living Basin's rules are
physical/deterministic (rainfall, erosion, grazing pressure), while
"semantic" tendencies (a campfire *tending toward* conversation) are
fuzzier and more interpretive -- legibility may degrade as the entity
vocabulary grows past a handful of physically-grounded concepts into
purely social/narrative ones. Worth treating as the actual open question
for a first prototype, not an assumed yes.

## Not yet real

No kernel, no schema, no event types, no influence-field engine exist. If
pursued, the concrete, small-prototype-first path this project's own
stated values (and the Chief's own "small prototypes over elaborate
architecture" preference) point toward: extend Living Basin's existing
`causedBy`/lineage engine with 2-3 semantic influence vectors on top of its
current physical rules, rather than building a new general-purpose
Semantic Engine from scratch -- test the open legibility question on the
one system in this repo that already does something adjacent, before
generalizing to campfires, storms, and libraries.

## Completion state

**recorded** -- design proposal only, assessed against real repo state.
No repository or live-service change resulted. Any future work requires
its own scoped packet under `docs/engineering-orders/packets/` with a
concrete first prototype target before becoming buildable work.
