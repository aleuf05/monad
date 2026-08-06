# Dev posture policy

Status: CONFIRMED — Admiral sign-off given 2026-08-03.
Date drafted: 2026-08-03
Drafted by: Claude, in conference with Admiral (Cameron).

## Simplicity mandate

No private sandboxes, no temporary/parallel services, no "clever Claude"
process tricks. This restates, and does not replace, the standing rules
already in `~/dev/monad/CLAUDE.md` ("Absolute Rule: Everything Happens
Live") and memory `monad-collaboration-style` — recorded here as a named
DEV-category policy point rather than a new rule.

## Proportionate security

Granite (this machine) is a personal system, not a military-grade
high-security environment. Security posture should match that reality:
sensible, already-settled precautions (passwords, no committed keys,
approval-gated destructive/external actions) — not invented hardening,
lockdowns, or defensive scaffolding beyond what's already been decided.
Do not add security/restriction measures unprompted; this is consistent
with the existing memory rule "never add restrictions without an explicit
command."

## Recoverability principle

Mistakes on this system are recoverable — the Admiral is the backstop.
This licenses acting decisively on clear instructions rather than
hedging, adding confirmation checkpoints, or building safety-net
scaffolding "just in case" for ordinary reversible dev work. It does not
change the existing bar for genuinely irreversible/external actions
(destructive ops, deployment, credential changes, messaging/publishing),
which still require explicit authorization per `CLAUDE.md`'s "Safety and
External Actions" section — recoverability of a home server does not
extend to actions whose blast radius is outside it.

## Binding

Same as `010`: this is a conference record, takes effect once the Admiral
confirms it, and does not itself change Documentation Posture, which
remains active and unaltered.
