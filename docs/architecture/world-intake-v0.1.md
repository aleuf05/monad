# Living World Intake V0.1

**Status:** thin-slice integration contract

Living World Intake converts a pasted engineering report into inspectable
proposals. It does not convert prose into canon. The governing seam is:

```text
immutable source -> candidate assertion -> Captain adjudication
                 -> compiled FleetCore command -> canon event -> current state
```

FleetCore remains the only canon writer. Confidence measures interpretation; it
never supplies authorization.

## Four-layer storage model

1. **Source** stores original bytes plus author, received timestamp,
   attachments, mission context, and content hash. Source content is immutable.
2. **Interpretation** stores extractor-produced assertions, excerpts,
   confidence, resolution candidates, and detected conflicts. Assertions are
   proposals, not facts.
3. **Adjudication** records the Captain's approve, approve-with-edit, reject,
   defer, flavor-only, mark-unverified, or link-existing decision. Rejections
   and failed command submissions remain durable.
4. **Canon** is FleetCore-owned state and its event log. An approval authorizes
   command submission; it does not itself mutate canon.

Stable identifiers connect every transition. The provenance index follows a
source ID and assertion ID through adjudication ID, command ID, resulting event
ID, and any later compensating event. Corrections append events such as
assignment revocation, permission removal, merge, corrected location, claim
downgrade, or supersession. No correction erases the earlier record.

## Supported slice

V0.1 accepts pasted engineering reports. It recognizes crew, agent, station,
department, vessel, and contact references and classifies identity, assignment,
capability, permission, location, relationship, event, request, claim, and
flavor assertions.

Supported proposals are entity creation, alias addition, role/station
assignment, onboarding status, unverified capability, reporting relationship,
authorization request, and approval/denial recording. Capabilities default to
unverified. A title never grants permission. A request never becomes a
completed event. Flavor has no operational command.

Identity resolution searches canonical IDs and aliases before suggesting a new
entity. Similar references are presented as link candidates; ambiguity creates
a review item. There is no silent merge or duplication.

Validation surfaces duplicate exclusive assignments, conflicting locations,
incompatible roles, contradictory identity/chassis data, missing stations,
permissions beyond qualification, unavailable watch personnel, command-authority
conflicts, superseded orders, duplicate events, and impossible chronology.
Material conflicts are not automatically resolved.

Permissions, command authority, reactor state, vessel movement, injury, death,
and safety status are marked for individual approval. Bulk approval is
deliberately absent.

## Captain review surface

Open `https://cameronlampley.com/toys/world-intake/`. The surface
shows the subject, proposed change, class, source excerpt, confidence, current
canon, conflicts, proposed command, provenance, and all required review actions.
It is intentionally separate from FleetCore controls.

The loopback `world-intake` service implements this narrow HTTP contract:

```text
GET  /world-intake-api/proposals?status=pending|deferred|all
POST /world-intake-api/adjudications
```

The GET response may be an array or `{ "proposals": [...] }`. The POST body is:

```json
{
  "proposal_id": "assertion-id",
  "action": "approve_with_edit",
  "amended_command": { "type": "..." },
  "linked_entity_id": null
}
```

Set an alternate base URL with `?api=/local/intake`. When the API cannot be
reached, the page visibly uses a single reactor-watch demo fixture. Demo actions
are local and explicitly report that canon was not changed.

Adjudication POSTs require `Authorization: Bearer <Captain review token>`.
The token is entered by the Captain in the review surface and retained only in
that browser tab's session storage. Queue reads do not require it.

The ingestion CLI/API should accept report bytes plus author, timestamp,
attachments, and mission context; return the source ID/content hash; and allow
idempotent extraction by source hash. Exact executable names are owned by the
core implementation, not this static surface.

## Command path and authority boundary

For an approved proposal, the compiler constructs a normal typed FleetCore
command with provenance identifiers and an idempotency key. Submission still
passes through authentication, authorization, schema validation, domain
validation, conflict policy, FleetCore handling, event logging, and checkpoint
persistence. The intake database must not open or update FleetCore canonical
tables directly. A rejected FleetCore command is linked back to its adjudication
and remains queryable.

On retry or restart, source hashes, assertion identity, adjudication identity,
command idempotency keys, and canon event IDs prevent duplicates. Replay derives
corrected current state from original and compensating events while retaining
their provenance chain.

## Operating notes

- Use the deployed review surface at
  `https://cameronlampley.com/toys/world-intake/`; do not launch an ad hoc
  static server for this repository.
- Install or update the loopback API, FleetCore binary, Caddy route, fixture,
  and systemd unit with `scripts/install-world-intake.sh`. The generated review
  token is stored at `~/.config/monad/world-intake.env` and is never committed.
- Start the intake API before review to leave demo mode. Confirm the header says
  **API linked** before making a real decision.
- Compare excerpts against the immutable source before approval. Resolve all
  identity ambiguity and material conflicts explicitly.
- Treat approve-with-edit as a command amendment. Server-side validation remains
  mandatory; UI JSON validation is only an operator convenience.
- After submission, inspect the adjudication, FleetCore acceptance/rejection,
  canon event, and provenance query. Approval alone is not evidence of mutation.
- Verify restart behavior by stopping both services after a committed fixture,
  restarting them, and querying the same source, review, event, and provenance
  IDs. Retry the commit and confirm no additional event appears.
- Correct mistakes with a new adjudicated compensating proposal, never by
  deleting or rewriting a source, decision, command, or event.

## Known limitations

- The review client is static and depends on the intake service for
  authentication, authorization, persistence, concurrency control, validation,
  and audit identity.
- V0.1 has no upload UI, attachment preview, batch approval, natural-language
  command box, automatic approval, or direct canon controls.
- The demo fixture proves presentation and operator flow only; it is not an
  integration or persistence test.
- The extractor is bounded to the supported entities and changes. Unsupported
  assertions must remain visible as deferred/unhandled material rather than be
  coerced into a nearby class.
- Concurrent Captain decisions require server-side optimistic concurrency; the
  browser does not arbitrate stale reviews.
- Generalized ontology, autonomous storytelling, voices/images, missions, and
  agent-framework work are outside this slice.
