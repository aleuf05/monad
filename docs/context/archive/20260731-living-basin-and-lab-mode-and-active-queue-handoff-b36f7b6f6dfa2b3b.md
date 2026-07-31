# Current context brief

> Compact projection, not project canon. Generated `2026-07-31T05:50:24+00:00` from cited
> repository sources. Input digest: `b36f7b6f6dfa2b3b`.

## Mission

Use Beastscape as a living laboratory for comparing ways to define, chart, navigate, evaluate, and interpret a diverse structural creature space, run alongside sibling Live Captain proof-of-architecture instruments the Admiral directs in parallel.

## Active course

Two Captain sessions landed work in this same working tree back-to-back and are now merged into one clean commit history (through 9ba6d24, pushed): Beastscape Foundry, Metastable Comedown Lab, Captain Workbench Beast Image, and Context Steward from one thread; The Living Basin, Mike's rocket-notebook completion, Beastscape Lab Mode Phase 1, and the homepage Active Queue redesign from a second, concurrent thread. Nothing is blocked. Remaining work is human verification this environment cannot perform (visual/mobile checks across several new surfaces) plus deciding next steps on parallel threads listed in next_action.

## Working vocabulary

- **Beastscape** — The full high-dimensional space of possible creature structures.
- **Passage** — A particular navigable low-dimensional submanifold through Beastscape.
- **Charting strategy** — The method used to discover, construct, and decode a Passage.
- **Chart coordinates** — The three abstract bearings locating the explorer within a Passage.
- **Specimen** — The creature encountered at a chart coordinate.

## Established truth

- The master live instrument is https://cameronlampley.com/toys/beastscape/.
- The authored Passage and Continuous UMAP Passage share the current Beastscape instrument.
- The UMAP atlas contains 1,200 deterministic soundings represented by 24 structural descriptors and embedded into three chart dimensions.
- The Continuous UMAP Passage uses a 12-anchor local kernel decoder rather than nearest-specimen replacement.
- The Beastscape Foundry compares Open Ocean, Metameric Forge, and Symbiotic Reef; each candidate has an explicit developmental grammar, 720 structural soundings, and an independently learned UMAP Passage; it is implemented in web/toys/beastscape/app.js and confirmed live.
- Gemini direct and GPT Live Captain enhancement paths remain available; GPT uses saved ChatGPT authentication through codex app-server without an OpenAI API key.
- Context Steward is standard Captain operating policy at meaningful milestones and active-course changes, now codified in AGENTS.md; the human opens any recommended fresh product thread.
- Captain enhancement activity is represented as durable observed events and terminal artifact facts; the interface does not invent a completion percentage.
- Lt. cgl granted Captain passwordless privileged execution authority on 2026-07-29 (docs/commissioning-handoff.md); sudo is no longer itself a human-handoff boundary, only genuine human-only testing or an inadequate/ambiguous course is.
- Metastable Comedown Lab (docs/research/METASTABLE_COMEDOWN_ARCHITECTURE_DRAFT_2026-07-30.md) is built and verified live at https://cameronlampley.com/toys/metastable-comedown/, linked from Build & Research.
- Captain Workbench Beast Image (beast.image.enhance, one bounded Gemini call per job) is staged and installed; living-captain-workbench.service is confirmed active on the host.
- Monadic Beast Lab was removed from the worktree as an orphaned/superseded instrument (web/toys/monadic-beast-lab deleted).
- This session's accumulated work (Foundry, Metastable Comedown Lab, Captain Workbench Beast Image, Context Steward, authority-bootstrap doc rewrites, IntentForge translation bench updates, BeastSpec design draft, Voice Mode Confusion recovery artifacts) is now committed as agent/living-world-intake-v0-1 commit a6498a7; the working tree is clean.
- The homepage Active Queue (web/assets/js/active-queue.js) is a localStorage-only, manually-ordered active-project tracker on the homepage with an injected "+ Queue" affordance on build.html/command.html/observe.html/story.html cards; verified live on all five pages.
- data/living-captain-workbench/ and data/mike-rocketry-intake/ were added to .gitignore as runtime state, matching the rest of data/ -- caught before being committed as generated binaries.
- The Living Basin (tools/living-basin/ Python reference engine, 26/26 unittest tests passing; web/toys/living-basin/engine.js a hand-ported live JS engine ticking client-side with no server) is built and live at https://cameronlampley.com/toys/living-basin/, linked from the homepage (below the notebook card) and Build & Research. The JS port has no automated test suite of its own (checked only via a one-off Node dry-run) and its canvas render has not been visually confirmed in a real browser -- flagged as the top known limitation in tools/living-basin/README.md.
- Mike's rocket-equations notebook: the relativistic-analog section was completed in a sibling ~/dev/rocketry checkout (a separate repo, not this one) and pushed to a personal fork at https://github.com/aleuf05/rocketry (branch captain/complete-rocketry-lab). In this repo, the rocket-lab reverie (web/toys/mike-rocketry/) was parked -- unlinked from the homepage but not deleted -- and the verbatim notebook render (web/toys/mike-rocketry-notebook/) was promoted to the homepage's top card; the site's GitHub attribution link now points at the fork, not Mike's untouched upstream.
- Beastscape Lab Mode Phase 1 (experiment branching, a beast inspector showing real generated specimen data plus editable identity/notes, a neighbor list that reuses the engine's own chart-distance k-NN math, three operator rating sliders, localStorage save/load) was added to web/toys/beastscape/{app.js,index.html,views.css} this session -- purely additive, Explorer Mode unchanged when Lab Mode is off. Verified via a Node dry-run against the real engine and the real 720-specimen atlas (deterministic, acyclic, correct neighbors, correct dedup-by-atlasId). This is Phase 1 of the Admiral's instrumented-mode architecture and is distinct from -- does not implement -- the separate BeastSpec identity-preservation design (docs/architecture/beastspec-design-v0.1.md), which remains proposed and unapproved for implementation.
- Monad top-level site redesign (web/assets/js/active-queue.js) landed alongside Lab Mode: a flat, manually-ordered, localStorage-only Active Queue on the homepage (pin-to-hold, reorder, edit note/next-action) sitting above the unchanged hierarchical category-page archive, plus a generically-injected "+ Queue" button on every a.card across build.html/command.html/observe.html/story.html. Verified with a real jsdom-driven browser-engine test (add-from-archive, reorder, pin-blocks-removal, cross-page consistency all passed against the live pages over local HTTP) -- not a hand-stubbed test, but still not an actual browser, and mobile layout has not been visually confirmed.
- No headless or graphical browser is available anywhere in this environment. Every 'verified live' claim across all of this session's new surfaces (Living Basin, Beastscape Lab Mode, the Active Queue redesign) rests on HTTP status checks, Node/jsdom logic dry-runs, and source inspection -- never an actual rendered screenshot or click-through. This is the single most important thing for whoever picks this up next to know before trusting any 'it works' claim about visual layout.

## Decisions

- Beastscape is a research apparatus rather than a user product: its interface exposes methods, observations, unknowns, artifacts, and comparative evidence.
- The Beastscape pre-exists any chart; a charting strategy is a navigational device, not the territory.
- Atlas soundings define learned geography but are not the only creatures allowed to exist.
- Human-adaptive embeddings remain deferred until static charting strategies provide comparative evidence.
- The next Beastscape sprint is the first observation period for Context Steward; evidence must precede any firm allowance-multiplier claim.
- Context Steward checkpoints are taken at meaningful milestones and active-course changes, not every turn, per the codified AGENTS.md operating policy.

## Live and changed surfaces

- web/toys/beastscape/ — live master instrument, continuous UMAP Passage, and the new Foundry candidate selector.

## Verification

- None recorded.

## Known defects

- None recorded.

## Next action

No single next action -- several independent threads are ready for the Admiral's direction: (1) human-test whether the Foundry's candidate Beastscapes differ meaningfully; (2) visually verify Living Basin, Beastscape Lab Mode, and the Active Queue redesign in an actual browser, including mobile, since none of that has been possible in this environment; (3) decide whether/when to approve BeastSpec for implementation, and separately whether to continue Beastscape Lab Mode into Phase 2 (navigation-policy comparison); (4) Lt. cgl's correct/complete Voice Mode Confusion transcript (GitHub issue #27) is still pending before its draft protocol packets can be adopted.

## Deferred ideas

- None recorded.

## Source paths

- `000_HIGHEST_PRIORITY_MONAD_CHARTER_2026-07-14.md`
- `docs/research/BEAST_STRUCTURAL_LATENT_SPACE_DRAFT_2026-07-29.md`
- `docs/research/METASTABLE_COMEDOWN_ARCHITECTURE_DRAFT_2026-07-30.md`
- `docs/architecture/live-captain-workbench-v0.1.md`
- `docs/engineering-orders/packets/CONTEXT-STEWARD-0.1.md`
- `docs/engineering-orders/packets/METASTABLE-COMEDOWN-LAB-0.1.md`
- `docs/engineering-orders/packets/CAPTAIN-WORKBENCH-BEAST-IMAGE-0.1.md`
- `docs/commissioning-handoff.md`
- `AGENTS.md`
- `CLAUDE.md`
- `tools/beastscape-umap/README.md`
- `web/toys/beastscape/app.js`
- `docs/architecture/beastspec-design-v0.1.md`
- `tools/living-basin/README.md`
- `tools/living-basin/ARCHITECTURE.md`

## Omissions

- deferred_ideas
- defects
- verification
- changed_surfaces
