# Local Agent With Heterogeneous Memory — Version 1

**Recorded:** 2026-07-28  
**Status:** Deferred research; set aside  
**Authority:** Admiral / Lieutenant cgl  
**Implementation authorization:** None  

## Study conclusion

**Captain recommendation:** If resumed, use a local-first Python and SQLite
architecture with Git-tracked policy and procedures, original files as primary
artifacts, deterministic local retrieval, explicit authority bands, append-only
events, hash-bound approval records, and manual semantic-memory promotion.

The operator Captain should remain logically separate from simulated Living
Fleet captains. Existing Living Fleet memory and Mission Record patterns may be
reused, but their databases should not automatically become the operator
Captain's canonical memory.

Version 1 should defer Qdrant, mandatory cloud models, automatic reflective
promotion, multiple agents, autonomous execution, policy self-modification, and
public deployment.

## Principal findings

- Existing local primitives include SQLite/WAL memory, episodic, semantic,
  procedural, narrative and reflective records, supersession, local TF-IDF
  retrieval, Git artifacts, and append-only Mission Record patterns.
- Missing unified controls include first-class policy, artifact, working-memory,
  sensitivity, authority, retention, verification, and write-scope fields.
- Policy must load before tools and fail closed.
- Authority bands must outrank semantic similarity.
- Generated summaries and reflections must never promote themselves to canon.
- Cloud context requires local allowlisting, redaction, sensitivity checks, and
  an outbound audit record.
- Model output, tool execution, and independent verification must remain
  separate records.

## Deferred questions

- Canonical policy sources
- Operator Captain identity
- Version 1 tool scope
- Approval representation
- Sensitive-data retention and cloud eligibility
- Relationship to existing Living Fleet memory

## Stand-down

No code, schema, service, dependency, production configuration, API call, work
queue item, or implementation packet is authorized by this record.
