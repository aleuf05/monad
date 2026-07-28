# Packet: LEGEND-SHAPER-0.1

1. **Originating intent** — Admiral request, 2026-07-28: create a myth/legend
   generator that does not claim to emit true legend, but instead acts as a
   controlled nonsense generator with the linguistic shape of legend.

2. **Verified starting state** — Monad has a completed local Legend Pipeline
   that validates evidence-bound lore candidates, but no public exploratory
   instrument for studying mythic linguistic form. `web/build.html` is the
   live, click-reachable research-instrument listing.

3. **Objective / problem** — Ship a small public instrument that makes
   legend-shaped language available for playful study while keeping simulated
   output unmistakably separate from fact, history, fleet state, and canon.

4. **Scope and exclusions** — Add one self-contained static HTML/CSS/JS toy and
   one Build & Research card. No model API, backend, persistence, FleetCore
   input, real-person material, canon mutation, lore publication pipeline, or
   operational authority.

5. **Constraints / authority** — Admiral authorized the bounded implementation
   in live Captain-space. `web/` is production; the artifact must be visible
   from the homepage path, truth-labeled on the page and copied output, usable
   without external services, and fully reversible.

6. **Acceptance criteria** —
   - reachable by Homepage → Build & Research → Legend Shaper;
   - visible `NEW` and `SIMULATED NONSENSE — NOT A TRUE ACCOUNT` markers;
   - deterministic result for identical controls and seed;
   - selectable domain, voice, shape, strangeness, and seed;
   - copied output retains the warning label and recipe;
   - page remains usable at narrow viewport width;
   - live URL returns HTTP 200.

7. **Tests / rollback** — Syntax/static checks, deterministic browser-function
   check, narrow-width inspection, link inspection, and live HTTP verification.
   Roll back by deleting `web/toys/legend-shaper/` and reverting its
   `web/build.html` card.

8. **Assigned actor** — Captain / Codex.

9. **Evidence / completion state** — **Verified complete.**
   - `git diff --check` passed for the page, listing card, and packet.
   - The inline JavaScript passed `node --check`.
   - A DOM-stub execution produced identical output twice for the same controls
     and `MONAD-001` seed; the recipe retained that seed.
   - Source inspection confirmed the narrow layout collapses to one column at
     720px and below, and the shared Monad breadcrumb is present.
   - `https://cameronlampley.com/toys/legend-shaper/` returned HTTP 200 and
     contained the visible title and simulated-nonsense warning.
   - `https://cameronlampley.com/build.html` returned HTTP 200 and contained
     the Legend Shaper card.
   - Browser screenshot/interaction was not available in this session; the
     visual conclusion is limited to responsive source inspection and live
     content retrieval.
