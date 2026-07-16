# Abstract Voice Engine 1.0

1. **Originating intent** — The Lieutenant ordered the proposed voice model fleshed out after confirming no executable abstraction existed.
2. **Verified starting state** — Radio Console and Living Captain directly duplicate browser SpeechSynthesis selection/failure logic. A proposed provider contract exists in `docs/architecture/voice-generator-strategy-v0.1.md`; no `voice.js` exists.
3. **Objective / problem** — Implement a reusable provider-neutral engine and prove it through the smaller Living Captain consumer.
4. **Scope and exclusions** — Add shared engine, browser provider, profiles, fallback telemetry, tests, and Living Captain migration. Do not modify Radio Console or add a cloud vendor/key.
5. **Constraints / authority** — Default behavior remains browser-local; zero voices and fallback are visible; consumers receive start/end/error/stop lifecycle; source/live copies ship together.
6. **Acceptance criteria** — Provider registry and profile APIs exist; browser provider lists/selects/speaks/stops; fallback attempts are reported; Living Captain displays active provider/voice and no longer constructs SpeechSynthesisUtterance itself; tests and syntax checks pass live.
7. **Tests / rollback** — Node unit test with fake providers/browser voices, syntax checks, drift check, live HTTPS markers. Roll back commit to restore direct Living Captain speech.
8. **Assigned actor** — Codex, authorized by the Lieutenant's 2026-07-16 instruction.
9. **Evidence and completion state** — Verified complete and recorded. Node provider/fallback tests pass; shared engine and Living Captain syntax checks pass; source/live drift reports synchronized after classifying the unit test as source-only. Live HTTPS exposes the provider-neutral engine copy, Browser Speech status, and migrated client scripts. Living Captain contains no direct `SpeechSynthesisUtterance` construction.
