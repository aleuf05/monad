# Cognitive Jiu-Jitsu Studio Note — Exact Evidence Span

## Problem

Candidate ingestion verified the origin and digest of evidence, but an
arbitrary candidate value could still be paired with those genuine bytes.

## Abstraction

Provenance answers “where did this come from?” It does not answer “which part
supports this value?” The obstruction was an unbound extraction, not weak
cryptography.

## Intervention

Candidate schema v2 adds required `evidence_start` and `evidence_end` character
offsets. Ingestion decodes the attested bytes as UTF-8, validates a non-empty
in-range span, and requires the extracted text to equal the candidate value.
The verified range is retained in the candidate's source string. Promotion
remains side-effect-free; no governing-context writer was added.

## Evidence

- Focused Live Captain suite: 45 tests passed.
- Added coverage proves a multibyte value can be extracted by character offset.
- Added coverage rejects a forged value and an out-of-range span.
- Existing digest, strict-schema, persisted-Admiral-role, duplicate, conflict,
  and closed-promotion tests remain passing.
- A read-only live dry run used persisted Admiral message sequence 217,
  `maintain proper captain posture and continue to fire`. Schema v2 reproduced
  the full 52-character value from range `0-52` and retained this attestation:
  `message:admiral:217#sha256:107dd24f5b820dcfba8d8ccdb178ef17a19a63878bd9bbea306452d564da1c88#chars:0-52`.
  The run neither mutated the ledger nor promoted the provisional key
  `admiral.command.literal`.

## Learning

The smallest useful reframing was to make the candidate identify its quote,
not merely its document. This closes arbitrary-value substitution while
leaving the harder semantic question visible: a literal value can be proven by
span, but the meaning assigned by its candidate key still requires judgment.
The live dry run made that distinction concrete: the value and provenance were
mechanically verified; the key remained an unpromoted interpretation.

## Nuclear Action follow-through: semantic counterexample

A second read-only dry run used persisted Admiral message 214. A dedicated
read-only evidence loader avoided the normal store initialization path, so it
performed no migration and recorded no restart. It extracted `Keep the session
light` from character range `773-795`, with evidence digest
`e38c39aa9e1b630f5f84ca423f45688c979bf763948138efc39e0feb1ee8dbae`.
Restart rows remained `5` before and after the run.

The exact phrase was assigned the provisional key
`commissioning.session.scope`. When that key and the attested-message source
were explicitly allowlisted, the existing boundary returned `promote`. This is
a useful negative result: exact quotation, trusted provenance, and policy
eligibility still do not establish that a candidate key correctly interprets
the quoted language. No promotion or ledger mutation occurred. The focused
suite now passes 46 tests.

## Candidate-key semantics: narrow proof

The semantic boundary is now executable without pretending that arbitrary
interpretation can be inferred. A `LiteralKeyContract` defines one mechanically
checkable meaning: the candidate key denotes only an exact character span from
an attested Admiral-authored message. Interpretive keys and sources outside
that class fail closed.

A live read-only dry run applied the contract to persisted Admiral message 224,
`be bold Captain`. Exact span `0-15` and SHA-256
`f068d9ab1794723d49980f03950046d401f34eab4f3129a569a6ee677502c5ce`
supported the narrow key `admiral.message.literal`. The same candidate did not
support the interpretive contract `admiral.command.scope`. No promotion or
ledger mutation occurred. Two adversarial tests bring the focused suite to 48
passing tests.

The result closes the candidate-key proof only for literal quotation. Meanings
such as command scope, durability, preference, or authorization require an
explicit semantic source or human judgment; attestation plus an allowlist
cannot manufacture them.
