# Initial Crew Architecture and Staffing Strategy

Packet ID: `MONAD-CREW-V1`

Status: Approved planning baseline

Implementation status: Deferred

Human authority: Admiral / Human Operator

Review trigger: Completion of one major feature-integration engineering pass

## Interpretation boundary

This crew chart describes capability roles and present operational reality. It
does not assert literal persons where none exist. The Admiral is the sole
real-world authority. This document is a revisable planning baseline, not
eternal constitutional law.

## Purpose

Define Monad's current crew reality, initial organizational roles, authority
boundaries, and gradual staffing strategy without overstating the existence or
permanence of any agent.

## Current operational crew

### Admiral / Human Operator

Type: Human

Status: Active

Authority: Final and sole real-world authority

Responsibilities:

- owns and operates the system;
- grants permissions;
- launches and stops agents;
- transfers context;
- authorizes consequential action;
- reviews results;
- remains accountable for all real-world effects.

### Captain

Type: Strategic AI role

Status: Standing

Responsibilities:

- mission and bearing;
- synthesis;
- doctrine;
- staffing strategy;
- decision framing;
- archive-ready packets;
- engineering oversight when requested.

The Captain does not control routine implementation unless explicitly
assigned an engineering role for a defined mission.

### Engineering Shop

Type: Infrastructure

Status: Active

The Bash/CLI environment hosts repositories, tools, tests, runtimes, and
available engineering agents. Infrastructure is not staff and possesses no
independent authority.

### Commander Claude and Commander Codex

Type: Frontier engineering agents

Status: Available

Both have proven highly capable. No controlled study has established a
meaningful difference between them.

Present policy:

- equal standing;
- interchangeable assignment;
- rotation through mission roles;
- no assumed specialization without evidence.

### Chief Engineer G

Type: Ephemeral Gemini-based agent persona

Status: Provisional / manually invoked

Chief Engineer G is sustained through human context transfer. Its comparative
value has not yet been established. It shall not be presumed superior to the
Captain, Claude, Codex, or any future model.

## Role architecture

### Chief Engineer

Type: Standing organizational role

Status: Unassigned by default

Purpose: Coordinate a defined engineering mission.

Responsibilities:

- decompose a mission into technical work;
- assign implementer and reviewer;
- define acceptance criteria;
- identify risks and rollback;
- reconcile conflicting technical advice;
- return one coherent, evidence-backed result.

Constraints:

- model-agnostic;
- mission-scoped;
- subordinate to human authority;
- no continuing tenure from prior assignment;
- no authority to redefine Monad's mission;
- no declaration of success without evidence.

### Implementer

Perform the authorized technical change and record exactly what changed.

### Independent Reviewer

Challenge the plan, implementation, assumptions, diff, tests, and likely
failure modes.

### Verification Officer

Determine whether the observable result satisfies the stated acceptance
criteria.

### Integration Officer

Status: Highest-priority future support role

Purpose: Maintain accurate context flow among Captain space, Engineering, and
the archive.

Responsibilities:

- prepare and validate packets;
- preserve packet IDs, provenance, constraints, and meaning;
- route approved context;
- collect structured returns;
- identify omissions, contradictions, and scope drift;
- reduce repetitive human glue work;
- draft non-authoritative summaries.

Prohibited:

- changing mission;
- inventing authority;
- approving implementation;
- altering factual claims;
- modifying core doctrine;
- inferring human consent.

Current occupant: Admiral, manually.

Trial strategy: Dedicate one bot primarily to Integration Officer duty and one
to Engineering Lead duty for the remainder of the current subscription month.
Claude and Codex may rotate between these assignments.

### Records Officer

Status: Standing role, initially dormant

Purpose: Preserve Monad's institutional memory across time.

Responsibilities:

- archive decisions, packets, returns, and evidence;
- preserve provenance and timestamps;
- distinguish observation, claim, inference, hypothesis, metaphor,
  correction, and unknown;
- link missions to files, tests, commits, and outcomes;
- preserve superseded material rather than silently overwriting it;
- maintain indexes, contradictions, and corrections.

Prohibited:

- declaring disputed claims true;
- erasing inconvenient history;
- converting proposals into approved decisions;
- inventing evidence;
- publishing sensitive material without authorization.

### Science Officer

Status: Standing role, initially dormant

Purpose: Test whether important claims deserve belief.

Responsibilities:

- separate observation from interpretation;
- identify assumptions and confounds;
- propose falsification tests;
- compare expected and observed results;
- track uncertainty;
- challenge unsupported declarations of success;
- prevent metaphor from being recorded as fact.

The Science Officer shall not turn ordinary work into endless debate or treat
skepticism as an end in itself.

### Security and Safety Officer

Status: Standing role, initially dormant

Purpose: Protect systems, people, data, and reversibility.

Responsibilities:

- review permissions and access;
- protect credentials and secrets;
- identify destructive or irreversible actions;
- require rollback plans where appropriate;
- review privacy and sensitive information handling;
- flag external network, credential, or deployment risks;
- escalate actions with legal, safety, or human consequences.

Prohibited:

- granting itself permissions;
- blocking all progress merely because risk exists;
- concealing incidents;
- treating safety review as authorization.

### Navigator / Human Benefit Officer

Status: Standing role, initially dormant

Purpose: Keep Monad aligned with real human usefulness.

Responsibilities:

- identify intended beneficiaries;
- state the actual human problem being addressed;
- evaluate accessibility and practical value;
- identify unintended burdens or harms;
- ask whether technical expansion advances the mission;
- seek observable indicators of benefit.

The Navigator does not replace the Admiral's moral judgment. It provides
disciplined review of whether the work remains worth doing.

## Model policy

Roles are stable.

Assignments are temporary.

Models are interchangeable.

Human authority is not.

A model may occupy any suitable role when explicitly assigned for a defined
mission.

No model acquires permanent office through brand identity, prior occupation
of a role, conversational continuity, confidence, personality, or persuasive
tone.

## Staffing strategy

Define broadly. Staff narrowly. Activate by demonstrated need. Retire roles
that prove ornamental.

A role earns a dedicated agent only when:

- the responsibility recurs;
- its inputs and outputs are clear;
- its authority boundary is safe;
- its work can be reviewed;
- delegation reduces real human burden;
- coordination cost does not exceed value.

## Current capacity finding

Recent ambitious Captain packets have reportedly required approximately two
to six minutes of Codex wall-clock execution time.

This suggests that current constraints may lie more in design throughput,
packet preparation, integration judgment, review, and deciding what deserves
implementation than in raw engineering capacity.

The second engineering bot should therefore justify itself primarily through
integration, independent review, error detection, redundancy, reduced human
glue, or materially improved throughput.

## Implementation deferral

This document authorizes archive entry only.

It does not authorize:

- live crew routing;
- automated agent launch;
- permanent role assignment;
- archive write automation;
- permission changes;
- live-site organizational representation.

Implementation shall be reconsidered only after at least one major
feature-integration engineering pass has been completed and reviewed.

## Post-integration review questions

- Which roles appeared naturally during real work?
- Where was context lost?
- Which glue tasks repeated?
- Did a dedicated Integration Officer reduce human burden?
- Did independent review materially improve outcomes?
- Did Claude and Codex display evidence-backed differences?
- Did Chief Engineer G add distinct value?
- Which dormant role, if any, earned activation?
- Did the organization remain simpler than the work it supported?

## Standing doctrine

Admiral authorizes.

Captain sets bearing.

Chief Engineer coordinates.

Implementer changes.

Reviewer challenges.

Verification checks.

Integration preserves continuity across space.

Records preserves continuity across time.

Science protects truth.

Security and Safety protect people and systems.

Navigator protects human purpose.

Reality retains veto power.
