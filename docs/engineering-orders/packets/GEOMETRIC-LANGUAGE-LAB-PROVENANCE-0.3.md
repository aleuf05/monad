# Packet: GEOMETRIC-LANGUAGE-LAB-PROVENANCE-0.3

1. **Originating intent** — The Admiral directed continued aggressive
   development of the living private-language process on 2026-07-29.

2. **Verified starting state** — A reviewed lexicon version persisted its
   phrase, meaning, contexts, and `source_episode` identifier, but not the
   teaching episode itself. Reloading the browser destroyed the only complete
   copy of the words, reference flags, gesture samples, interpretation, and
   review state behind that identifier.

3. **Objective / problem** — Make every saved meaning independently
   inspectable by preserving its complete reviewed source episode.

4. **Scope and exclusions** — Embed a snapshot of the reviewed teaching
   episode in each new lexicon version, retain a separate source ID, expose a
   concise trace summary, and include the snapshot in JSON export. Do not add a
   backend, cloud synchronization, CAD behavior, or migrate/alter existing
   browser records.

5. **Constraints / authority** — Private records remain browser-local,
   inspectable, exportable, and clearable. Historical entries without embedded
   episodes remain readable and honestly report the older trace boundary.

6. **Acceptance criteria** —
   - new entries retain a full source episode after reload;
   - the embedded episode is `reviewed-provisional` and names its source ID;
   - explicit references, sacred flags, gesture samples, interpretation, and
     evidence survive;
   - the lexicon card visibly reports preserved trace scope;
   - JSON export contains the same episode without relying on in-memory state;
   - existing entries containing only a source ID continue rendering.

7. **Tests / rollback** — Fresh-browser guided save, reload, storage
   inspection, export inspection, legacy-entry render test, syntax check,
   live-byte comparison, and mobile overflow check. Roll back the localized
   entry-construction and card-summary changes.

8. **Assigned actor** — Captain / Codex.

9. **Evidence / completion state** — **Verified complete.**
   - `node --check web/toys/geometric-language-lab/app.js` passed.
   - A fresh live guided episode saved with `reviewed-provisional` status,
     matching source ID, three references, three sacred flags, eleven gesture
     samples, explicit human review, interpretation, and evidence counts.
   - Reloading the page restored the entry and visibly reported “Trace
     preserved.”
   - Exported JSON contained the same complete source episode and identifier.
   - An injected historical ID-only record rendered successfully and visibly
     reported “Legacy trace · source ID only.”
   - The live mobile browser retained zero horizontal overflow.
