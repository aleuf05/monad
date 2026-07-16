# Voice Performance Console 0.1

1. **Originating intent** — The Lieutenant asked whether a voice-manipulation UX existed, then ordered it built.
2. **Verified starting state** — Living Captain could read/stop and display its inferred performance, but exposed no authoring controls. `MonadPerformance` accepted context and intent but no explicit axis targets.
3. **Objective / problem** — Make the performance engine directly audible and manipulable without bypassing its continuity or shared voice-provider layers.
4. **Scope and exclusions** — Add an intent selector, tension/warmth/energy/restraint controls, preview and context-reset actions to Living Captain; add bounded operator targets to the planner. Exclude text editing, provider selection, voice cloning and Fleet Radio changes.
5. **Constraints / authority** — Context remains the default; operator controls are ephemeral; targets remain clamped; preview still routes through `MonadPerformance` and `MonadVoice`.
6. **Acceptance criteria** — Controls are plainly visible live, values update while dragged, preview speaks the current report with selected direction, output identifies operator direction, and Return to Context clears manual state.
7. **Tests / rollback** — Unit-test target override, run voice/performance tests, JS syntax and drift checks, then verify live HTTPS markers. Revert this packet and associated UI/planner changes.
8. **Assigned actor** — Codex, authorized by the Lieutenant on 2026-07-16.
9. **Evidence and completion state** — Verified complete and recorded. Unit tests prove bounded operator target overrides; existing voice and continuity tests pass; JS syntax and source/live drift checks pass. Live HTTPS exposes the open `Shape performance` console, all four axes, intent selection, Preview Performance, Return to Context and the versioned client wiring.
