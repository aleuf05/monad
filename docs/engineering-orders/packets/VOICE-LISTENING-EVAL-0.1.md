# Voice Listening Evaluation 0.1

1. **Originating intent** — Continue finishable voice work and ensure perceptual character progress is measured rather than inferred from plumbing.
2. **Verified starting state** — Architecture named blind-listening thresholds but no manifest builder or scorer existed; rich generation is not yet commissioned.
3. **Objective / problem** — Provide a deterministic blinded six-line evaluation across characters with an objective pass gate.
4. **Scope and exclusions** — Randomized private/public manifests, response scoring, character/intent/caricature/transcript metrics and tests. Exclude generating audio or collecting human responses.
5. **Constraints / authority** — Public manifest never exposes answers; repeated seed yields identical order/IDs; pass requires character >=75%, intent >=80%, caricature <10%, transcript errors zero.
6. **Acceptance criteria** — Six fixtures cover routine, warning, recovery, private, ceremonial and humor; perfect responses pass; caricature/transcript-error responses fail; scorer reports bias counts.
7. **Tests / rollback** — Network-free Python unit tests. Remove evaluation module/tests/packet.
8. **Assigned actor** — Codex.
9. **Evidence and completion state** — Verified complete and recorded. Nine total voice-engine tests pass, including deterministic blinded manifests, answer removal, perfect-score acceptance and caricature/transcript-error rejection. Python compilation and diff checks pass; no audio generation or API spend occurred.
