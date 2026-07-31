# METASTABLE-COMEDOWN-LAB-0.1

1. **Originating intent** — On 2026-07-30 the Admiral supplied the Metastable
   Comedown Architecture and then directed Captain to build it as a web app.
2. **Verified starting state** — The proposal existed only as
   `docs/research/METASTABLE_COMEDOWN_ARCHITECTURE_DRAFT_2026-07-30.md`.
   `web/build.html` is the live, click-reachable home for research instruments.
   No existing Metastable Comedown implementation or route was found.
3. **Objective / problem** — Make the proposed closed-loop dynamics directly
   explorable: users must be able to see recurrence, coherence, band crossings,
   damped correction, and trajectory history rather than infer them from prose.
4. **Scope and exclusions** — A static, deterministic browser laboratory with
   seeded synthetic phrase generation, live metrics, adjustable bands,
   intervention controls, timeline, and event log. No model/provider call,
   medical claim, diagnostic claim, speech audio, backend, persistent store, or
   claim of faithfully simulating a human cognitive state.
5. **Constraints / authority** — Admiral's direct build instruction authorizes
   this bounded public-facing slice. Existing unrelated worktree changes must
   be preserved. The instrument must be reachable through the live site and
   visibly identify its draft/simulated status.
6. **Acceptance criteria** — A visitor can reach the lab from Build & Research;
   start, pause, step, and reset a deterministic run; tune recurrence and
   coherence hysteresis bands; observe state, correction strength, trace, event
   log, and generated text; and see corrections decay rather than hard-reset.
7. **Tests / rollback** — Syntax-check JavaScript, exercise the live page in a
   browser, and fetch the public URL. Rollback is removal of the added card and
   `web/toys/metastable-comedown/`; the research draft and packet remain as
   evidence.
8. **Assigned actor** — Captain / Codex.
9. **Evidence and completion state** — **Verified complete and recorded.**
   `node --check web/toys/metastable-comedown/app.js` passed. Direct HTTPS
   requests verified that the public Build & Research page contains the new
   card and that
   `https://cameronlampley.com/toys/metastable-comedown/` serves the instrument
   with its state, trajectory, and simulation labeling. No supported graphical
   browser executable was present on the host, so automated visual
   click-through remains unperformed; the visible public route and source
   delivery were verified directly.
