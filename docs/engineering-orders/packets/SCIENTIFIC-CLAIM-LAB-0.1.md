# Packet: SCIENTIFIC-CLAIM-LAB-0.1

1. **Originating intent** — The Admiral authorized aggressive implementation
   of the quiet-station scientific principle on 2026-07-28 after accepting a
   bounded prototype: one claim schema, one worked example, and one verifier.

2. **Verified starting state** — `web/build.html` links to several research
   instruments, including the Truth Engine, but no public artifact currently
   represents a scientific claim as a durable falsifiable record or verifies
   its required evidence fields. The root reaches Build & Research in one
   click.

3. **Objective / problem** — Make the principle “Monad guides the process;
   reality decides what survives” operational as a public, inspectable Claim
   Laboratory rather than leaving it as prose.

4. **Scope and exclusions** — Add one static public Claim Laboratory with a
   machine-readable schema, one worked Monad claim, and a deterministic
   verifier; add one card to Build & Research. No backend, credentials, AI
   judgment, universal scientific claim, broad redesign, or canon promotion.

5. **Constraints / authority** — Preserve human authority, traceability,
   falsifiability, uncertainty, reversible files, and visible live behavior.
   The verifier may establish record completeness and internal consistency,
   never the truth of the scientific proposition itself.

6. **Acceptance criteria** —
   - the root reaches the laboratory through Build & Research;
   - the live laboratory visibly distinguishes record validity from claim
     truth;
   - the example contains proposition, classification, falsifier, protocol,
     evidence, reproduction, criticism, verdict, history, and human authority;
   - one shared verifier runs in Node and the browser;
   - the example passes, while controlled omissions and invalid verdicts fail;
   - public HTML, JSON, and JavaScript return HTTP 200 and match committed
     bytes.

7. **Tests / rollback** — Run Node syntax and verifier checks, mutation tests,
   JSON parsing, repository link checks, and direct live byte comparisons.
   Roll back the new laboratory directory and the single Build card.

8. **Assigned actor** — Captain / Codex.

9. **Evidence / completion state** — **Verified complete.**
   - `node --check web/toys/claim-lab/verifier.mjs` passed.
   - The Node verifier reported 16 checks passed and rejected both controlled
     mutations: a missing falsifier and an invented verdict.
   - Both JSON artifacts parsed successfully.
   - Root → Build & Research → Scientific Claim Laboratory is a direct
     click path.
   - Live Build, laboratory HTML, schema, example, and verifier each returned
     HTTP 200 and matched local bytes.
   - A headless mobile-width browser rendered one shared navigation bar, no
     horizontal overflow, visible `PASS`, the truth-boundary warning, and
     `PASS` for both controlled negative tests.
   - Browser evidence: `/tmp/claim-lab-mobile.png` during verification;
     reproducible from the public URL without privileged state.
