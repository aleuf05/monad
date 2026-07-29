# Packet: GEOMETRIC-LANGUAGE-LAB-ONBOARDING-0.2

1. **Originating intent** — The Admiral’s first unaided inspection on
   2026-07-29 found real progress but could not determine how to use the
   Geometric Language Laboratory without explanation.

2. **Verified starting state** — The live laboratory completes its technical
   teaching workflow, but opens directly on an unfamiliar diagram, multiple
   tools, and raw JSON. It provides no first-run task, progress signal, or
   plain-language completion condition.

3. **Objective / problem** — Make one useful human test self-explanatory in
   about one minute.

4. **Scope and exclusions** — Add an optional guided experiment, five visible
   progress steps, contextual next-action instruction, and a plain-language
   interpretation above the raw record. Do not alter schemas, CAD behavior,
   IntentForge files, or the evidence boundary.

5. **Constraints / authority** — Operator confusion is treated as observed UX
   evidence. Guidance must teach the real interaction rather than simulate a
   success or hide unresolved meaning.

6. **Acceptance criteria** —
   - the first viewport offers one obvious “Start guided experiment” action;
   - each genuine operator action advances a visible five-step guide;
   - compilation displays a plain-language reflection before raw JSON;
   - the raw machine record remains inspectable;
   - completion states exactly what was saved and what remains unproven;
   - a fresh mobile browser can finish without external instructions and
     without horizontal overflow.

7. **Tests / rollback** — Browser-driven fresh-profile walkthrough, visible
   progress assertions, syntax check, mobile screenshot, and live-byte checks.
   Roll back the localized guide markup, styles, and guide-state functions.

8. **Assigned actor** — Captain / Codex.

9. **Evidence / completion state** — **Verified complete.**
   - `node --check web/toys/geometric-language-lab/app.js` passed.
   - A fresh live mobile browser opened on one obvious “Start guided
     experiment” action and `0 / 5` progress.
   - Selecting the three named references advanced to `1 / 5`; marking them
     sacred advanced to `2 / 5`; drawing a typed keep-out advanced to `3 / 5`;
     defining and compiling advanced to `4 / 5`; explicit review and save
     advanced to `5 / 5`.
   - The plain-language reflection named all three sacred references, the
     keep-out gesture, the supplied operational meaning, and the lack of
     physical validation.
   - The full machine record remained available behind an inspectable details
     control and ended at `reviewed-provisional`.
   - The completion message stated that one provisional meaning was saved and
     that a real printed fit must still test it.
   - The 390 × 844 live rendering had no horizontal overflow. Visual evidence
     was inspected at `/tmp/geometric-language-lab-guided-mobile.png`.
