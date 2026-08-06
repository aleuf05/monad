# Live Captain Phone Analysis Packet

**Status:** verified commissioning evidence packet  
**Evidence cutoff:** 2026-08-02 08:38 UTC  
**Audience:** old-phone Captain and human Operator  
**Authority:** analysis only; this packet does not authorize governing-context edits

## Operator: how to use this in GitHub Chat

Open this file in the GitHub repository, then ask GitHub Chat to analyze the
current file. If the chat cannot automatically read the open file, paste this
repository-relative path into the request:

`docs/reports/2026-08-02-live-captain-phone-analysis-packet.md`

Use this prompt:

> Analyze the Live Captain commissioning effort from the current evidence
> packet. Distinguish verified observation, reasonable inference, unsupported
> hypothesis, success, shortcoming, and next falsifiable experiment. Do not
> assume continuous agency between turns. Return: (A) the strongest defensible
> conclusion; (B) an evidence table; (C) successes; (D) shortcomings and
> alternative explanations; (E) what was not proved; (F) the next three
> experiments ranked by information value; and (G) a presentation-ready
> summary under 150 words. Follow the linked primary evidence before making a
> strong claim.

The Operator should keep GitHub Chat grounded in the repository files linked
below. If it cannot follow a link, open that file and ask again with the file in
view. Treat chat output as analysis, not as new evidence or authority.

## Mission tested

Commission one coherent Live Captain that can preserve course across turns and
restart, operate the real Monad environment, make bounded changes, test them,
and improve its context machinery.

## Verified observations

- Identity, Admiral relationship, mission, and conversational course survived
  reconstitution.
- A backend restart preserved recent conversation, bearing, continuity ledger,
  and command continuity.
- The Captain performed cumulative repository work and left inspectable
  artifacts.
- Persisted messages record the identity-kernel, bearing, and continuity-ledger
  digests used for their turns.
- Context telemetry was activated and sampled after restart.
- A read-only continuity-metabolism and promotion boundary was implemented.
- Candidate ingestion validates a strict versioned schema and an evidence
  digest against independently supplied bytes.
- Persisted Admiral-message evidence can be retrieved as exact bytes;
  Captain-authored messages cannot attest candidates.
- Promotion remains read-only. No governing-context writer exists.
- Final focused verification passed 43 of 43 Live Captain tests at the evidence
  cutoff. The commissioning report also records four passing image-boundary
  tests and a clean `git diff --check`.

## Negative results and limits

- There is no evidence of continuous cognition or autonomous work between
  turns.
- Persistent service, conversational continuity, operational capability, and
  durable autonomous execution are different properties.
- A valid digest proves which bytes were supplied, not that a candidate
  assertion follows from those bytes.
- Candidate assertions are not yet bound to an exact supporting evidence span.
- No automatic continuity-ledger writer has been authorized or implemented.
- Concurrent recurrent executions were observed sharing durable conversation;
  writer ownership or leasing remains unresolved.

## Current hypothesis

Continuity can be reconstructed through a stable identity kernel, a curated
bearing, provenance-backed durable state, recent verbatim conversation, and
access to inspect reality. Uninterrupted model execution is not required for
operational continuity across turns.

This hypothesis is supported by the commissioning observations, but it should
not be inflated into a claim of continuous consciousness or background agency.

## Immediate falsifiable experiment

Require every candidate assertion to identify an exact character or byte span
in attested evidence. Independently verify that the span extracts the asserted
value, then exercise the existing promotion boundary read-only. Keep the
rolling verbatim window and do not add a writer.

Success means malformed, out-of-range, mismatched, and non-entailed candidate
bindings fail closed while a representative exact extraction reaches the same
read-only promotion decision reproducibly.

## Primary evidence and implementation

- [Full commissioning report](../../LIVE_CAPTAIN_COMMISSIONING_REPORT.md)
- [Bootstrap and restart acceptance](../logs/2026-08-01-live-captain-bootstrap-acceptance.md)
- [Autonomous-watch record and post-analysis data](../logs/2026-08-02-live-captain-autonomous-watch.md)
- [Current commissioning bearing](../../tools/live-captain/context/current-bearing.md)
- [Continuity ledger](../../tools/live-captain/context/continuity-ledger.md)
- [Read-only metabolism and promotion boundary](../../tools/live-captain/context_metabolism.py)
- [Persistence and Admiral-message evidence adapter](../../tools/live-captain/persistence.py)
- [Focused verification suite](../../tools/live-captain/test_live_captain.py)

## Required analytical discipline

For every conclusion, identify the supporting repository artifact. Separate:

1. verified observation;
2. reasonable inference;
3. unsupported hypothesis;
4. success;
5. shortcoming;
6. next falsifiable experiment.

Passing tests establish the tested behavior only. Narrative coherence is not
proof of hidden continuity. Provenance establishes evidence origin, not semantic
entailment. Where the record permits multiple explanations, preserve them.
