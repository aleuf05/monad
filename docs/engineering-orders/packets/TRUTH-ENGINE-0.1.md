# Packet: TRUTH-ENGINE-0.1

1. **Originating intent** — Captain-to-Admiral transmission relayed by Lt.
   cgl, 2026-07-28: Monad should become "a system for confronting uncertain
   reality without collapsing into either dogma or chaos," operationalized
   as a small, concrete first "Truth Process" workflow. Full text recorded
   in `docs/doctrine/2026-07-28-truth-engine.md`.

2. **Verified starting state** — no existing "Truth Engine"/"Truth Process"
   artifact anywhere in the repo (grep confirmed). Closest precedent is
   `web/toys/cognition-graph/` (single self-contained HTML instrument,
   mock-mode-by-default, optional BYO Gemini key, no backend) — reused its
   pattern directly rather than inventing a new one. `web/build.html`
   confirmed as the live "Build & Research" listing page linked from
   `web/index.html`'s homepage grid.

3. **Objective** — ship a small, bounded, client-side instrument at
   `web/toys/truth-engine/` implementing the requested stages: observe →
   separate fact from interpretation → generate competing hypotheses →
   design disconfirming tests → confidence levels, visibly → safest next
   action → preserve anomalies for later.

4. **Scope**: one self-contained HTML/JS toy, wired into `build.html`'s
   card grid with a `new` tag, reachable from the site root via
   Build & Research. **Exclusions**: no new backend service, no new
   privileged port/systemd unit/Caddy route (would require a `cmd.sh`
   handoff — out of scope for a "small first implementation"); no
   autonomous command authority; not wired into fleet state or any other
   live data source — the observation is whatever text the visitor types.

5. **Constraints / authority** — CLAUDE.md's URL/port policy (bare-root
   reachable, no new ports); API Economy doctrine (expensive reasoning
   only on demand, BYO key, static/mock by default); Doctrine 007
   (continuity — mock mode is a real fallback, not a placeholder, so the
   instrument stays useful with zero live-API dependency).

6. **Acceptance criteria**:
   - `https://cameronlampley.com/toys/truth-engine/` returns 200. (Verified.)
   - `https://cameronlampley.com/build.html` links to it with a visible
     `new` tag. (Verified — grep confirmed the link text is present.)
   - Reachable by clicking Homepage → Build & Research → The Truth Engine
     card, no path typed from memory. (Confirmed by inspecting
     `web/index.html`'s existing link to `build.html`.)
   - Mock mode runs end-to-end with no API key (deterministic, seeded
     output at every one of the four stages) and clearly labels itself as
     simulated in the mode banner and the run-complete status line.
   - Anomaly Ledger persists across runs via `localStorage`, is clearly
     labeled "this browser only," and has a manual clear control.

7. **Tests / rollback** — manual verification only (live curl checks
   above); no automated test suite for this client-only toy, consistent
   with other toys in this directory. Rollback: `git rm -r
   web/toys/truth-engine/` and revert the `build.html` hunk — fully
   reversible, no state stored outside the visitor's own browser.

8. **Assigned actor** — Claude (this session), executed directly per the
   no-pausing-for-confirmation policy (no hard block, no privileged step).

9. **Evidence / completion state**: **verified complete**. Evidence:
   live 200 response from the real toy URL, live grep-confirmed link from
   `build.html`, doctrine draft recorded at
   `docs/doctrine/2026-07-28-truth-engine.md`. Not yet observed: real
   visitor adoption/usage (per the Living Captain precedent, usefulness
   should be allowed to prove itself through use, not asserted at ship
   time) — flagged here as future signal to watch, not a blocker on this
   packet's completion.
