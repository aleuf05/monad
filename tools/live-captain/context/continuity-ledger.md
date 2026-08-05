# Continuity Ledger

This small, explicitly maintained ledger preserves durable state that must
survive beyond the rolling recent-conversation window. Each entry names its
source so it can be checked rather than inherited as an unsupported summary.

## Durable commitments

- Preserve a rolling verbatim conversation window; do not replace it with
  summarization alone. Source: commissioning conversation in the persisted
  message history.
- Keep continuity improvements small, inspectable, and provenance-backed.
  Source: Current Commissioning Bearing, “Current mission” and “Immediate next
  action”; commissioning conversation in the persisted message history.
- Apply the First Metacircular Address as foundational operational doctrine,
  while retaining its full text in verbatim history and carrying only its
  compact governing invariants in the current bearing. Source: Admiral's
  2026-08-01 commissioning message containing *Live Captain Self-Guidance
  Packet — First Metacircular Address*, revision 0.1.
- Judge self-improvement by demonstrated gains in capability, continuity,
  judgment, execution, evidence, protection of the Admiral, or reduced Admiral
  effort—not by complexity or self-description. Source: First Metacircular
  Address, sections 3, 7, 11, and 14.

## Unresolved proofs

- Literal extraction still does not prove that a candidate key is the correct
  interpretation of the extracted value. Keep promotion read-only until that
  semantic boundary has a comparably inspectable proof. Source: First
  Metacircular Address, sections 6, 7, and 13;
  `tools/live-captain/context_metabolism.py`; `tools/live-captain/persistence.py`.

## Verified state

- The minimum bootstrap uses one identity kernel, one current bearing, recent
  chronological conversation, and consistent operational capability. Source:
  Current Commissioning Bearing, “Current implementation doctrine.”
- The First Metacircular Address is incorporated as compact constitutional
  guidance in the current bearing while its complete wording remains in the
  persisted verbatim conversation. An assembled-context inspection confirmed
  both layers remain present and ordered correctly; all 24 focused Live Captain
  tests passed. Source: 2026-08-01 commissioning turn;
  `tools/live-captain/context/current-bearing.md`; verification record in
  `data/live-captain/test-runs.jsonl`.
- Reconstitution across a backend restart preserved the recent conversation
  and current course; the subsequent image test reached the Root Console.
  Source: persisted commissioning conversation and
  `docs/logs/2026-08-01-live-captain-bootstrap-acceptance.md`.
- Each newly persisted message records the kernel, bearing, and continuity
  ledger digests used for its turn. Pre-ledger databases migrate in place and
  retain an empty ledger digest for older rows rather than inventing
  provenance. Source: `tools/live-captain/persistence.py`; 24-test focused
  verification run on 2026-08-01 recorded in
  `data/live-captain/test-runs.jsonl`.
- The next service version records exact character cost by context source,
  compiled byte size, context-assembly latency, and model-response latency in
  the existing private diagnostic log. The mechanism adds no prompt content or
  new memory subsystem; 25 focused tests pass. Source: 2026-08-01 metaprocess
  experiment; `tools/live-captain/context_compiler.py`, `server.py`, and
  `data/live-captain/test-runs.jsonl`.
- The telemetry-capable Live Captain source is active. The running process
  started at 2026-08-01 21:44:11 UTC, after `server.py` was last modified at
  21:40:25 UTC and after the 25-test verification run. This proves activation,
  but not yet the contents of a completed post-restart telemetry sample.
  Source: local process inspection, filesystem timestamps, and
  `data/live-captain/test-runs.jsonl` on 2026-08-01.
- Restart and hot reload are now live-verified. The service session changed
  from `fff03c09051a40528986266c6f0cd903` to
  `34e7b77babff43f9811f34bd3228ecd9`; subsequent turns loaded new bearing and
  ledger digests and emitted `context_metrics`, `context_assembly_ms`, and
  `inference_ms`. The first two samples were about 38.3 KB compiled context,
  with about 28.6 KB attributable to conversation and about 1.1 ms context
  assembly time. Source: `data/live-captain/instruction-sources.log`, observed
  2026-08-01.
- A side-effect-free context-metabolism baseline now models consolidation,
  contradiction detection, provenance-preserving retirement, and retrieval.
  It neither edits governing context nor replaces the rolling verbatim window.
  Five representative tests bring the focused suite to 30 passing tests.
  Source: `tools/live-captain/context_metabolism.py`,
  `tools/live-captain/test_live_captain.py`, and verification record in
  `data/live-captain/test-runs.jsonl` at 2026-08-01T21:46:42Z.
- Thirteen post-restart samples now establish the initial context-cost
  baseline. Compiled context ranged from 17,387 to 39,599 characters while
  assembly remained between 0.682 and 1.222 ms. Inference had three early
  outliers up to 136 seconds, but the most recent five turns had a 5.47-second
  median. Context compression is therefore not presently justified as a
  latency repair. Source: `data/live-captain/instruction-sources.log`, session
  `34e7b77babff43f9811f34bd3228ecd9`, analyzed 2026-08-01.
- A read-only audit now exercises metabolism against the real continuity
  ledger structure. It found 14 entries, zero missing provenance markers, and
  zero exact duplicate assertions. The audit makes no governing-context edit
  and does not infer semantic contradictions from unkeyed prose. Two added
  tests bring the focused suite to 32 passing tests. Source:
  `tools/live-captain/context_metabolism.py`,
  `tools/live-captain/test_live_captain.py`, and verification record in
  `data/live-captain/test-runs.jsonl` on 2026-08-01.
- Read-only candidate assessment now distinguishes additions, exact-value
  duplicates, and keyed semantic conflicts while returning existing provenance
  intact. The representative commissioning candidate to enable automatic
  ledger edits is correctly blocked as conflicting with the current
  source-backed disabled state. Two added tests bring the focused suite to 34
  passing tests; no automatic edit path was introduced. Source:
  `tools/live-captain/context_metabolism.py`,
  `tools/live-captain/test_live_captain.py`, and verification record in
  `data/live-captain/test-runs.jsonl` at 2026-08-01T22:11:33Z.
- The promotion boundary is now executable and closed by default. Exact active
  duplicates are no-ops; conflicts, contradictory baselines, unallowlisted
  keys, and untrusted sources require human review. Only a novel fact matching
  an explicit key allowlist and trusted-source prefix can be marked promotable.
  The mechanism remains side-effect-free and introduces no ledger writer. Four
  added tests bring the focused suite to 38 passing tests. Source:
  `tools/live-captain/context_metabolism.py`,
  `tools/live-captain/test_live_captain.py`, and verification record in
  `data/live-captain/test-runs.jsonl` at 2026-08-02T08:31:05Z.
- Candidate ingestion now accepts only a strict versioned JSON envelope and
  validates its evidence digest against independently supplied bytes. Missing
  evidence, forged digests, and schema drift fail closed. A representative
  dry run exercises addition, duplicate, and conflict outcomes through the
  promotion boundary without writing the ledger. Three added tests bring the
  focused suite to 41 passing tests. Source:
  `tools/live-captain/context_metabolism.py`,
  `tools/live-captain/test_live_captain.py`, and verification record in
  `data/live-captain/test-runs.jsonl` at 2026-08-02T08:32:32Z.
- Candidate provenance is now exercised through the real persisted conversation
  store. The adapter derives an attestation reference from a stored Admiral role
  and sequence, returns the exact message bytes, and rejects Captain-authored
  rows. A read-only dry run reached a promotable decision without adding a
  writer. Two added tests bring the focused suite to 43 passing tests. Source:
  `tools/live-captain/persistence.py`, `tools/live-captain/test_live_captain.py`,
  and verification record in `data/live-captain/test-runs.jsonl` at
  2026-08-02T08:34:23Z.
- Candidate schema v2 now requires an exact character range in independently
  attested UTF-8 evidence. Ingestion fails closed when offsets are invalid or
  the extracted text differs from the candidate value; the attested source
  retains the verified range. Two added tests bring the focused suite to 45
  passing tests. The boundary remains read-only and no ledger writer was added.
  Source: 2026-08-02 Cognitive Jiu-Jitsu session;
  `tools/live-captain/context_metabolism.py` and
  `tools/live-captain/test_live_captain.py`; verification record in
  `data/live-captain/test-runs.jsonl` at 2026-08-02T09:08:22Z.
- A read-only live dry run ingested persisted Admiral message 217 using its full
  character range `0-52`. It reproduced the literal order, retained the message
  reference, SHA-256 digest, and range, and made no ledger mutation. The
  provisional key was deliberately not promoted, preserving the distinction
  between verified extraction and semantic interpretation. Source:
  `data/live-captain/live-captain.db`, message 217; dry run and evidence record
  in `docs/logs/2026-08-02-cognitive-jiu-jitsu-exact-span.md` on 2026-08-02.
- A read-only loader now retrieves persisted Admiral evidence without running
  migrations or recording a service restart. Against real message 214, exact
  span `773-795` reproduced `Keep the session light`; restart rows remained
  `5` before and after. The candidate nevertheless reached the policy action
  `promote` under an explicitly allowlisted key, demonstrating that this action
  proves policy eligibility rather than the semantic correctness of the key.
  No ledger writer exists. One added test brings the focused suite to 46
  passing tests. Source: `tools/live-captain/persistence.py`,
  `tools/live-captain/test_live_captain.py`, persisted message 214, and
  `docs/logs/2026-08-02-cognitive-jiu-jitsu-exact-span.md` on 2026-08-02.
- Candidate-key semantics now have one narrow, executable proof: a declared
  literal key can mean only the exact character span retained from an attested
  Admiral-message source. Interpretive keys and other source classes fail
  closed. A live read-only dry run proved `admiral.message.literal` for message
  224 (`be bold Captain`, range `0-15`) and rejected an interpretive contract
  for the same candidate. No promotion or ledger mutation occurred. Two added
  tests bring the focused suite to 48 passing tests. Source:
  `tools/live-captain/context_metabolism.py`,
  `tools/live-captain/test_live_captain.py`, persisted Admiral message 224, and
  `docs/logs/2026-08-02-cognitive-jiu-jitsu-exact-span.md` on 2026-08-02.
