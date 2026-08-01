# Admiralty Section — Foundational UI Brief

**Recorded:** 2026-07-31  
**Status:** Foundational design brief; implementation guidance, not an
authorization for autonomous command execution  
**Audience:** Claude and future UI implementers  
**Scope:** Private strategic-command surface for Monad

## Living Basin refinement priority

The Living Basin should prioritize **causal legibility and lived experience**
before increasing simulation complexity. A visitor and the Admiral should be
able to understand what changed, why it changed, and how the system feels in
use before additional state, agents, or simulation machinery is introduced.

## Purpose

The Admiralty section is Monad's private strategic-command surface. It is where
Cameron defines mission bearing, reviews the state of the system, delegates
bounded work, resolves strategic ambiguity, and decides what becomes
canonical.

It is not another engineering dashboard and it is not a place where AI agents
independently exercise authority.

The essential question is:

> What is Monad doing, why is it doing it, who currently has authority to act,
> and what requires the Admiral's decision?

## Command model

The interface must visibly preserve this hierarchy:

- **Admiral — Cameron:** final strategic and canonical authority.
- **Captain:** organizes, interprets, advises, coordinates, and returns
  decisions to the Admiral.
- **Specialized officers and agents:** perform bounded delegated work with
  explicit permissions, assignments, stop conditions, and return requirements.
- **Tools and implementation agents:** operate only within approved scopes and
  produce inspectable results and provenance.

AI recommendations must remain clearly distinguishable from Cameron's
observations, decisions, and approvals.

## Core functions

### 1. Mission bearing

Display the present north star of Monad:

- current mission;
- active campaign;
- strategic priorities;
- major questions;
- explicit exclusions;
- definition of success.

The Admiral should be able to revise direction without editing implementation
details.

### 2. Decision queue

Provide one clear place for matters requiring human judgment:

- approvals;
- rejected or deferred proposals;
- unresolved strategic questions;
- requests to expand scope or permissions;
- decisions that would alter canonical project state.

Nothing becomes approved merely because an agent recommended or implemented it.

### 3. Delegation board

Show every meaningful assignment with:

- assigned officer or tool;
- objective;
- granted permissions;
- prohibited actions;
- current status;
- expected return artifact;
- stop or escalation conditions;
- approving authority.

The interface should make it easy to see who is doing what and under whose
authority.

### 4. Canon and doctrine

Provide access to foundational documents governing the system:

- mission charter;
- command architecture;
- safety and containment boundaries;
- project doctrine;
- accepted design principles;
- commissioning records;
- current canonical definitions.

Drafts, machine proposals, and accepted canon must have visibly different
states.

### 5. Fleet and project state

Present a high-level strategic view of:

- active projects;
- commissioned systems;
- prototypes;
- experiments;
- paused or retired work;
- current risks and blockers.

This is a command summary, not a dense technical telemetry screen.

### 6. Admiral's log

Allow Cameron to preserve observations, mission changes, decisions, questions,
temporary hypotheses, orders, and reflections requiring later review.

An entry may be recorded immediately without treating it as an approved factual
claim or operational command.

### 7. Approval-gated actions

Consequential actions must be visibly gated. External messages, public posts,
purchases, deployments, credential changes, remote-system changes, and other
real-world actions must not occur from Admiral-state activity alone. They
require deliberate authorization from baseline Cameron under the established
Bedroom Containment Boundary.

The UI should show these boundaries rather than hiding them in policy text.

## Initial page structure

The first UI pass should create:

1. **Admiralty Header** — current campaign, mission bearing, system posture,
   and identity of the current human authority.
2. **Requires Your Decision** — compact queue of pending approvals and
   strategic questions.
3. **Active Orders** — delegated assignments with officer, status, scope, and
   return condition.
4. **Fleet Overview** — projects grouped as commissioned, active prototype,
   experiment, paused, or archived.
5. **Canon and Doctrine** — foundational documents with clear draft/accepted
   status.
6. **Recent Admiralty Log** — latest decisions, observations, and mission
   changes.
7. **Command Boundaries** — concise visible statement of present permissions and
   prohibited external actions.

## Design character

The page should feel like the bridge of a serious cognitive vessel:

- calm rather than theatrical;
- authoritative without appearing militaristic;
- spacious and highly legible;
- dark naval or restrained technical styling;
- clear distinction between observation, proposal, order, approval, and
  completed action;
- strategic information first, with implementation detail available through
  drill-down.

The user should experience command bearing, not information overload.

## Non-goal boundary

The first pass must not introduce:

- a generic chatbot page;
- dense live telemetry;
- elaborate fleet animation;
- unrestricted agent controls;
- public access;
- automatic promotion of drafts into canon.

The first milestone is a convincing static or lightly functional command
surface that establishes the correct information architecture and authority
model. This brief defines the surface, information hierarchy, and visible
approval boundaries; it does not authorize external actions, production
changes, credential changes, or expansion of agent permissions.

## Acceptance test

The first version succeeds when Cameron can open Admiralty and answer within
approximately thirty seconds:

- What is Monad's current mission?
- What requires my decision?
- What work is currently delegated?
- Who or what is authorized to perform it?
- What has recently changed?
- Which documents and decisions are canonical?
- What actions are presently prohibited or approval-gated?

This acceptance test is deliberately about orientation, causal legibility, and
authority—not feature volume. It gives the UI implementer enough direction to
begin without prematurely designing the entire Root Console.

## Related Monad doctrine

- [Project Mission](../mission.md)
- [Command Structure](../command-structure.md)
- [Safety](../safety/README.md)
- [Semantic Artifact Engineering](../research/SEMANTIC_ARTIFACT_ENGINEERING.md)
- [Operational Topology — Packet 006](../research/OPERATIONAL_TOPOLOGY_PACKET_006_2026-07-31.md)

This brief is a design source for implementation review. It does not promote
draft doctrine to canon and does not replace human approval gates.
