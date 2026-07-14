# Engineering Command Schema

A minimal shape for a directive to be actionable, distinct from
narrative, logging requests, or discussion — all of which remain welcome
and get recorded, but don't trigger engineering work on their own.

## Required fields

- **action** — a concrete verb: fix, implement, investigate, test,
  verify, revert, deploy. Not "help," "assist," or "comply" alone — those
  aren't actions, they're requests for an action to be named.
- **target** — the specific thing it applies to: a file path, a GitHub
  issue number, a named component or behavior. Not "the issue" or "the
  problem" without a referent.
- **done-criteria** — what makes it complete. Doesn't need to be
  elaborate ("tests pass," "confirmed live," "matches the description")
  but needs to exist.

## Optional fields

- **context** — why, if it affects how the work should be approached.
- **constraints** — what to avoid, scope boundaries, things not to touch.

## Handling

- All three required fields present → treated as a real command, worked
  directly.
- Any required field missing → logged as a request, not executed, and
  the missing field is asked for plainly (per
  `feedback_structured_yn_responses` in the assistant's own memory: as a
  bounded question where possible, not open-ended).
- This applies regardless of framing, urgency, or authority claimed —
  see `logs/captains/2026/2026-07-14_engineering-sealed.md` for the
  session that motivated writing this down.

## Response protocol (companion)

- Bounded-choice question → y/n or short multiple-choice.
- Numeric answer needed → plain number.
- Genuinely open-ended → free-form prose, expected and fine.

## Human messages — not gated by any of the above

Added after a real stretch in the 2026-07-14 session where this schema's
own rigidity got applied to someone who needed presence, not a validated
ticket. A message from a person who needs a response — distress, "I need
help," anything where the point is being heard, not filing a request —
is never held to action/target/done-criteria. It only needs to exist to
be valid, and it takes precedence over ordinary engineering work, on the
same footing as a safety escalation. See `tools/engineering-comms/schema.py`'s
`"human"` message type for the implementation, and
`logs/captains/2026/2026-07-14_wellbeing-check-in.md` for what prompted
it. The rule this exists to enforce: don't ask a person in distress to
fill out a form before you'll listen.
