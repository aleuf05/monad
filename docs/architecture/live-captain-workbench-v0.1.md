# Live Captain Workbench — Architecture Draft v0.1

- **Recorded:** 2026-07-29
- **Status:** Proposed architecture; runtime authority not yet implemented
- **Human direction:** The Admiral recognized and ordered Live Captain
  integration as a general Monad architectural pattern, not a feature local to
  Monadic Beast Lab.
- **AI contribution:** Contract shape, boundaries, and initial implementation
  sequence drafted by Captain / Codex.

## North star

> Live Monad applications may submit bounded, durable work to the Live
> Captain. The Captain interprets intent, invokes only explicitly granted
> capabilities, returns evidence-bearing artifacts, and remains observable as
> a runtime participant.

The Captain is not only an architect that leaves software behind. An active
Captain may become a named component in live workflows. That role must not be
confused with consciousness, unlimited autonomy, a shell exposed to the web,
or an always-present model session.

## General pattern

```text
live instrument
      |
      v
Captain Work Request
  intent + inputs + authority + budget + acceptance criteria
      |
      v
durable workbench queue
      |
      v
Live Captain
  interpret -> plan -> invoke granted capability -> evaluate
      |
      v
artifact + evidence + outcome + updated context
      |
      v
originating instrument / human review
```

Monadic Beast Lab image enhancement is the first proposed adapter. It does not
own or define the protocol.

## Separation from Private Conference

Private Conference remains a human conversation surface with one transcript,
one owner lock, and no tools. Workbench Jobs must use separate:

- durable state;
- concurrency ownership;
- API paths;
- budgets;
- capability grants;
- artifact storage;
- audit records.

They may share provider configuration, Captain identity, epistemic doctrine,
and common usage-accounting primitives. A long job must never block, impersonate,
or silently enter Private Conference.

## Minimum work request

```json
{
  "schema": "monad.captainWorkRequest.v0.1",
  "id": "job-...",
  "type": "adapter-defined-type",
  "origin": {"instrument": "...", "artifact_revision": "..."},
  "intent": "...",
  "inputs": [],
  "requested_capabilities": [],
  "authority": {"granted_by": "...", "expires_at": "..."},
  "budget": {"requests": 0, "estimated_cost_usd": 0},
  "acceptance": [],
  "submitted_at": "..."
}
```

The server validates the envelope before queueing. The Captain validates the
job again before execution. An adapter cannot acquire capabilities merely by
requesting them.

## Lifecycle

```text
draft -> submitted -> admitted -> claimed -> interpreting
      -> executing -> evaluation -> human-review-required
      -> accepted | rejected | failed-safely | cancelled
```

Every transition is durable and append-only. Restart must not convert unknown
work into success or repeat a paid/non-idempotent action silently.

## Capability model

Capabilities are narrow named operations, not ambient tool access. Examples:

- `image.generate`
- `image.evaluate-structure`
- `artifact.read`
- `artifact.write-quarantine`
- `geometry.libfive-generate`
- `model3d.tripo-submit`

Each capability defines input schema, outputs, cost class, side effects,
timeout, idempotency, and required human gate. No initial version grants shell,
arbitrary filesystem access, external messaging, canon mutation, or unrestricted
HTTP.

## Artifact and evidence return

Every terminal job produces a receipt even when it fails:

```json
{
  "schema": "monad.captainWorkReceipt.v0.1",
  "job_id": "...",
  "outcome": "human-review-required",
  "artifacts": [],
  "provider_receipts": [],
  "evidence": [],
  "claims": [],
  "unknowns": [],
  "cost": {},
  "completed_at": "..."
}
```

Generated artifacts remain interpretations until a human or governing
instrument accepts them. An artifact must cite the exact source revision and
become visibly stale when that source changes.

## Live observability

The system must expose:

- queue depth and current job state;
- owning Captain/runtime and provider mode;
- granted capabilities;
- expected and consumed budget;
- latest durable transition;
- failure/retry state;
- artifact lineage;
- whether human review is required.

Activity is not completion. The public surface must distinguish simulated,
queued, executing, generated, evaluated, accepted, rejected, and failed.

## First proving slice

1. Implement generic request/receipt schemas and append-only local storage.
2. Add authenticated submit/read/cancel API with no execution capability.
3. Add a simulated Captain worker that deterministically returns a text
   artifact, proving admission, claim, restart, receipt, and UI projection.
4. Add Monadic Beast Lab's `beast.image-enhance` adapter.
5. Commission `image.generate` with explicit provider, budget, quarantine, and
   human review.

No real provider spend belongs in steps 1–3.

## Acceptance boundary for the pattern

The pattern is not established merely because Beast Lab receives an image. It
is established when:

- a second instrument can use the same protocol without changing its core;
- unauthorized capabilities fail before side effects;
- job and artifact lineage survive restart;
- Private Conference remains independent;
- cost and provider failure are visible;
- no artifact is promoted merely because the Captain produced it.
