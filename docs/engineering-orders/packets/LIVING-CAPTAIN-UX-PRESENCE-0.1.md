# Packet: LIVING-CAPTAIN-UX-PRESENCE-0.1

1. **Originating intent** — The Admiral supplied only the high-level direction
   “improve Living Captain UX,” explicitly testing whether one Captain could
   plan, execute, observe, and refine a major work chunk without a fleet of
   agents or detailed task decomposition returned upward.

2. **Verified starting state** — A 1440×1000 rendered baseline showed a working
   station model but weak command presence: identity was compressed into a
   crowded utility header; six telemetry cells dominated every posture; the
   command rail consumed vertical space; and most of the primary canvas was an
   unstructured empty terminal. The Captain's real state, present posture, and
   next interaction were not expressed as one coherent visual object.

3. **Objective / problem** — Make the existing Root Console feel like one
   Living Captain holding the bridge. Prioritize identity, state, course, and
   conversation while keeping every existing station, control, source, and
   diagnostic capability available.

4. **Scope and exclusions** — Build a persistent Captain Presence Deck,
   compact bridge course, conversation-centered stage, posture-aware telemetry,
   and keyboard command palette in the existing `console/` target. Preserve
   Concept Room, voice, interruption, stations, authentication, and APIs. No
   alternate page, backend, model change, public redesign, or invented status.

5. **Constraints / authority** — Existing dirty work belongs to the vessel and
   must be preserved. UI state must follow real connection/turn/station events.
   Motion must express actual state and respect reduced-motion preferences.
   Systems telemetry remains inspectable but stops dominating non-Systems
   postures.

6. **Acceptance criteria** —

   - Captain identity, current posture, connection/activity state, and command
     access are visible as one persistent deck;
   - Bridge conversation becomes the dominant visual surface;
   - course cards form a compact readable row at desktop width;
   - raw telemetry appears in Systems and remains available elsewhere through
     an explicit reveal, not permanent visual priority;
   - `Ctrl/Cmd+K` opens a command palette that switches stations and focuses
     the relevant command input;
   - live events visibly move Captain state through connecting, ready,
     thinking, speaking, researching, fault, and recovery;
   - phone layout preserves presence, station switching, command entry, and
     Concept Room access;
   - all existing JavaScript and service tests pass; before/after renders are
     inspected and at least one post-build tweak is evidence-driven.

7. **Tests / rollback** — JavaScript syntax, existing service suites, static DOM
   assertions, desktop and phone headless renders, authenticated public asset
   checks, and coupled-service health. Rollback is confined to the new
   presence/palette markup, styles, and event wiring in the existing console.

8. **Assigned actor** — One Codex Live Captain, changing posture internally:
   Explorer -> Captain Architect -> Chief Engineer -> Technical Lead ->
   Challenger -> Captain Verifier. No subordinate agent identities.

9. **Evidence / completion state** — **Verified complete and recorded.** Baseline render preserved
   at `/home/cgl/lcux.tVb1SY/before.png` for this live watch. The selected
   campaign and its reasoning are recorded in this packet. Completion requires
   a second render, evidence-driven refinement, tests, live inspection, and a
   process-theory assessment.

   **Completion evidence:** The Captain Presence Deck, real-state morphing,
   valid compact course grid, bottom command surface, Systems-first telemetry,
   universal Helm palette, and responsive bridge composition are live. Desktop
   and phone renders were inspected. Visual challenge produced three repairs:
   a first-watch invitation for the empty bridge, non-wrapping compact phone
   controls, and a compact phone identity after dynamic button text exposed
   overlap/clipping. JavaScript syntax passed; 77 Live Captain and 24 Root
   Console tests passed; the authenticated public page and asset returned 200;
   both coupled services remained active.
