# Rich Voice Studio 0.1

1. **Originating intent** — Continue through the usable rich-engine path while keeping API spend explicit and small.
2. **Verified starting state** — Studio supported free browser rehearsal; rich API supported status, estimate, cache-first render and artifact playback but had no frontend consumer.
3. **Objective / problem** — Make free versus paid rendering unmistakable and require a separate estimate followed by an explicit final-generation action.
4. **Scope and exclusions** — Studio API status, free rehearsal rename, estimate, rich generation, cached/generated cost display and audio playback. Exclude automatic generation, variants and Radio use.
5. **Constraints / authority** — Slider/input changes make no API calls; estimate makes no Gemini call; Generate remains disabled without a valid estimate and either a cache hit or configured backend; failure preserves free rehearsal.
6. **Acceptance criteria** — Live UI exposes both tiers, exact estimate/cost/cache state, explicit Generate and artifact player; scripts pass syntax/drift checks.
7. **Tests / rollback** — JS syntax, drift, live markers and commissioned API smoke checks. Revert Studio files.
8. **Assigned actor** — Codex.
9. **Evidence and completion state** — Verification pending. Frontend implementation, syntax, drift and live static markers are complete. Privileged service/Caddy commissioning, backend key presence, one generated artifact, cache-hit proof and live audio playback remain outstanding.
