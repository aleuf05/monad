# Scout Net Radio 1.0

1. **Originating intent** — Lieutenant reported that scout traffic sounded like narration of every net event rather than real radio.
2. **Verified starting state** — Captains repeatedly emit unchanged postures every 30–60 seconds; Radio summarized these through Bridge and periodically rolled up station-keeping routes.
3. **Objective / problem** — Transmit concise callsign traffic only when a scout's accepted posture actually changes.
4. **Scope and exclusions** — Add Scout Net, direct scout phrases, posture dedupe, and silence routine routes/intents. Preserve fuel, watch, and emergency traffic.
5. **Constraints / authority** — Seed current postures on connection; do not replay; newest decision per vessel wins; rejected decisions stay silent.
6. **Acceptance criteria** — Scout Net independently toggleable; repeated postures and route completions silent; changed posture speaks once as the scout, addressed to Monad, with radio brevity.
7. **Tests / rollback** — Syntax, drift, live markers, source assertions. Revert commit.
8. **Assigned actor** — Codex.
9. **Evidence and completion state** — Verified complete and recorded. Source/live syntax and drift checks pass. Live page exposes Scout Net and version 11; live code seeds current postures, speaks only accepted changes, uses direct callsign phrases, and contains no aggregate captain-decision or station-keeping rollup text.
