# MIKE-ROCKETRY-REVERIE-V1

## 1. Originating intent

The Admiral asked the Captain to complete the unfinished work in Mike's
`mds2/rocketry` notebook and add a playable web artifact. The Admiral then
supplied the narrow Version 1 interaction design and ruled that implementation
remain in **Reverie** status until Mike is appropriately involved.

## 2. Verified starting state

The live berth at `/toys/mike-rocketry/` existed as a truthful construction
placeholder. Mike's source notebook supplies equations and Python plots but no
interactive web artifact. The source repository's latest commit examined was
`9482befa1928015bbc8250c29c6ac86745d9dafe`.

## 3. Objective / problem

Turn the notebook's core constant-versus-optimal exhaust comparison into a
small, recognizable, mathematically faithful interactive instrument.

## 4. Scope and exclusions

Version 1 includes controls for \(m_i\), \(m_f\), and \(R_e\); one synchronized
burn slider; two schedules; live delta-v and exhaust-velocity curves; a final
gain factor; assumptions; presets; animation; and shareable URL state.

Excluded from Version 1: inert-mass optimization, storage engineering,
relativistic propulsion, mission profiles, notebook completion, and any claim
of Mike's participation or endorsement.

## 5. Constraints / authority

The Admiral authorized live implementation with cautious oversight. Mike's
published idea must be preserved before adding complexity. The artifact must
remain visibly unofficial and portable until Mike joins the process.

## 6. Acceptance criteria

- All specified Version 1 controls and views are visible and functional.
- Both models use the same idealized total energy budget.
- The live gain ratio equals
  \(G(r)=(r-1)/(\sqrt r\ln r)\).
- URL parameters restore a shared state.
- Assumptions and unofficial Reverie status are visible.
- Verified results and unresolved problems remain visibly distinguished on the
  live page.
- Static HTML, CSS, and JavaScript require no backend or build step.
- Real production HTML and module URLs return HTTP 200.

## 7. Tests / rollback

Run mathematical invariant checks in Node, JavaScript syntax checks, visual
browser inspection at desktop and mobile widths, and real-URL checks.
Rollback is a revert to the verified placeholder commit `f48305e`.

## 8. Assigned actor

Captain / Codex CLI, under the Admiral's high-level design oversight.

## 9. Evidence and completion state

**Lifecycle:** executing → verification pending.

Current evidence:

- analytical endpoint/gain and monotonicity checks: PASS;
- `node --check` for `app.js` and `math.js`: PASS;
- live HTML, application module, and math module: HTTP 200;
- source attribution, gain reveal, and share control present in live HTML.
- a public Reality Check distinguishes verified math, open physical-model
  assumptions, pending visual inspection, and the boundary awaiting Mike.

Remaining before verified complete: interactive browser and narrow-viewport
inspection, portable package assembly, and final live marker review.
