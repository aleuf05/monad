# Model-Agnostic Crew Role Assignment

Status: Approved planning principle

Implementation: Deferred until after the next major feature-integration pass

## Decision

Monad crew roles shall be defined independently of specific AI models,
vendors, interfaces, or persistent personas.

Roles such as Chief Engineer, Implementer, Reviewer, Science Officer, Records
Officer, Integration Officer, and Security Officer shall be represented as
stable responsibility and authority contracts.

Any suitable frontier model may be assigned temporarily or persistently to a
role, subject to:

- declared mission scope;
- explicit authority limits;
- required inputs and outputs;
- provenance;
- human authorization;
- review requirements;
- observable performance.

No model shall acquire permanent organizational authority merely because it
previously occupied a role or maintained a convincing persona.

## Assignment contract

Each assignment should declare:

```yaml
role:
assigned_model:
provider:
instance_id:
mission_scope:
authority_scope:
required_outputs:
reviewer:
human_approval_required:
```

This permits assignments including:

- Claude as Chief Engineer and Codex as Implementer;
- Codex as lead and Claude as reviewer;
- Gemini as architecture critic;
- the Captain temporarily occupying a Science or Records role;
- multiple instances of the same model in different roles.

## Rationale

This approach permits:

- mixing and matching models by demonstrated strength;
- comparing models on equivalent work;
- rotating lead and review assignments;
- using multiple instances concurrently;
- changing providers without restructuring the organization;
- preventing vendor identity from becoming confused with institutional role.

## Standing principle

Roles are durable.

Assignments are temporary.

Models are interchangeable.

Human authority is not.
