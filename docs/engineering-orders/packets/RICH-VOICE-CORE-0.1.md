# Rich Voice Core 0.1

1. **Originating intent** — The Lieutenant ordered continued work toward a rich engine under a strict low-API-spend constraint.
2. **Verified starting state** — The provider-neutral browser engine and complete rich architecture existed; no executable cache, budget ledger, prompt compiler or Gemini TTS provider existed.
3. **Objective / problem** — Implement the non-service rich-render core so cost safety and cache identity are proven without making a paid call.
4. **Scope and exclusions** — Character/performance request records, deterministic prompt compiler/hash/estimate, Gemini Interactions TTS adapter, immutable WAV cache, SQLite budget reservations and unit tests. Exclude HTTP exposure, systemd/Caddy commissioning, Studio rich-take button and real API calls.
5. **Constraints / authority** — Gemini is the only generative provider; API key stays backend-only; cache check precedes reservation; budget fails before provider execution; exact transcript instruction is mandatory.
6. **Acceptance criteria** — Duplicate request invokes provider once; character revision invalidates cache; over-budget request invokes provider zero times; failed generation releases reserved budget; audio writes atomically; spend is inspectable.
7. **Tests / rollback** — Python unit tests with fake PCM provider; no network. Remove `tools/voice-engine` and this packet to roll back.
8. **Assigned actor** — Codex, authorized by the Lieutenant on 2026-07-16.
9. **Evidence and completion state** — Verified complete and recorded. Four network-free unit tests prove single-generation cache reuse, revision-sensitive identity, fail-before-provider budget enforcement and reservation release after provider failure. Python compilation and diff checks pass. No Gemini call or API spend occurred.
