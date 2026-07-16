# Legend Pipeline 1.0 — Component One

1. **Originating intent** — The Lieutenant selected component 1 from the complete legend-generation target plan: `tools/legend-pipeline/`.
2. **Verified starting state** — Operation QUacken has a complete authoritative mission JSON and an existing hand-authored fact/lore pair. No general evidence assembler, generator contract, or candidate validator existed.
3. **Objective / problem** — Build the reusable local pipeline boundary from verified mission evidence through fact rendering, provider request generation, and legend validation.
4. **Scope and exclusions** — Add a standard-library Python package, CLI, tests, and documentation. Do not write Living Fleet memory, mutate FleetCore, adjudicate candidates, publish lore, or fabricate model output when no provider is configured.
5. **Constraints / authority** — Facts must derive from evidence; lore remains explicitly non-operational; provenance uses content hashes; missing/contradictory evidence fails closed.
6. **Acceptance criteria** — Operation QUacken produces a hashed evidence bundle and deterministic fact summary; `prepare` emits a provider-neutral prompt; valid candidate JSON passes; unlabeled, source-less, fact-copying, or operational-truth claims fail; tests cover the full local path.
7. **Tests / rollback** — Run the unit tests and CLI against the real mission. Roll back by reverting the implementation commit.
8. **Assigned actor** — Codex.
9. **Evidence and completion state** — Verified complete and recorded. Four unit tests pass, covering real evidence preparation, valid-candidate completion, truth-claim rejection, and incomplete-mission rejection. The CLI prepared Operation QUacken with source SHA-256 `1f6332e95c5b0b2eb957a3a8bf35691d616b23666e43d218faa6b4e1a78ce871`, the verified 31-second dwell fact, and a `fleet-lore` output contract.
