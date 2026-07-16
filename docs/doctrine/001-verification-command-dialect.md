# Doctrine 001 — Verification Command Dialect

**Status:** Adopted
**Author:** Claude (this session, from Commander's Campaign Target List packet)
**Adopted:** 2026-07-15

## Principle

No verified evidence, no confirmed kill. Uncertainty must stay visible: confidence is not evidence, consensus is not independence, a passing test proves only what it examined, and completion must name what remains undone.

## Rationale

Issued as a Campaign Target List against ten specific failure modes in
executor/commander communication (confident wrong answers, ceremonial
test passes, missing constraints, stale readbacks, shared assumptions,
partial-completion ambushes, false state matches, irreversible fixes,
silent dependencies, and reconstituted bugs). Each is grounded in a real
instance from this session's own work, not a hypothetical -- several
were self-caught and corrected in real time, which is the intended
proof standard: a failure mode is worth codifying only once it has
actually occurred and been observed, not merely imagined.

## Operating Guidance

Ten repair phrases, in the packet's stated priority order:

1. **Successful Test That Proves Nothing** -- "Tests pass *for* X; they
   do not exercise Y." Name the property under test and what remains
   unexercised. *(Real instance: Living Captain's 9/9-passing tests said
   nothing about covering only 2 of Section 9's 8 named inspection
   dimensions.)*
2. **Shared Assumption** -- "Consensus does not validate a common source
   of error." State each confirmation's independent origin before
   counting it as separate evidence. *(Near-miss: a binary-mtime vs.
   commit-time discrepancy was outweighed by, not reconciled with, a
   stronger agreeing signal.)*
3. **False State Match** -- "Two matching reports are not independent if
   they share one source of failure." Require genuinely distinct
   measurement layers before calling something double-verified.
   *(Done correctly: the issues #6/#13 correction used three
   independent mechanisms -- live HTTP snapshot, binary `strings`
   inspection, `journalctl` restart timestamps.)*
4. **Confident Wrong Answer** -- "Confidence must never substitute for
   evidence." Every classification carries a "confirmed against:
   `<source>`" suffix, or downgrades to "appears." *(Real instance:
   Living Captain's wake-sequence scope was called "a gap" confidently,
   then self-corrected against `living-captain-v0.2.md`.)*
5. **Partial Completion Ambush** -- "Completion reports must name what
   remains undone." Four buckets -- complete / partial / blocked /
   deferred -- every sub-item in exactly one. *(Done correctly: `BR-01`
   was split into two separate verdicts, Command Center absent vs.
   mission-control-unification present, rather than one blended status.)*
6. **Missing Constraint** -- "Critical boundaries belong in the order,
   not merely in the commander's mind." Every capability grant pairs
   with an explicit "must not" list. *(Real instance: the queue
   protocol never named "shared working directory can bundle another
   agent's uncommitted edit into your commit" as a boundary -- it
   happened once, was disclosed, not yet patched.)*
7. **Stale Readback** -- "A correct readback of an obsolete order is
   still incorrect execution." Every executable order states its
   validity condition and refuses rather than proceeds if unmet. When
   an order requires external lookup, the lookup itself must be
   bounded and explicit, e.g. `timeout 5 getent hosts <host>` or
   `dig +time=2 +tries=1 <host>`, so a stale or unreachable dependency
   fails visibly instead of hanging the caller.
   *(Done correctly: `cmd.sh`'s `EXPECTED_HEAD` gate refused, exit 66,
   exactly when HEAD moved after pinning -- caught, not executed wrong.)*
8. **Silent Dependency** -- "Unknown dependencies are part of the target,
   not background noise." Every packet names non-obvious prerequisites
   (human presence, process state, cache freshness) explicitly.
   Bounded probes belong here too: if a dependency check can block
   indefinitely, it is not explicit enough yet.
   *(Real instance: sudo requiring a password was discovered by testing,
   not by design, after one aborted `cmd.sh` run.)*
9. **Irreversible Fix** -- "A change is not fully controlled until
   recovery has been demonstrated." Default status is "rollback
   documented, not exercised" until actually run once. *(Gap this
   session: every fix had a written rollback; none were ever executed
   to confirm they work.)*
10. **Reconstituted Bug** -- "A target is not neutralized until it
    survives relevant recurrence conditions." State neutralized-under
    vs. not-yet-tested-under explicitly. *(Partial: `fleetcore-live`'s
    fix was tested against the exact recurrence condition -- array
    rotation past retention -- at the unit level, but never
    re-confirmed against the live server under real production
    rotation post-deploy.)*

## Related Artifacts

- `docs/reports/2026-07-15-phase1-sweep-and-corrections.md` -- source of
  targets 1, 3, 7's real instances
- `docs/reports/2026-07-15-feature-matrix.md` -- source of targets 1, 5's
  real instances (Living Captain scope, `BR-01` split verdict)
- `docs/engineering-orders/queue.md` / `AGENTS.md` -- source of target
  6's real instance (the `AM-01` claim-bundling incident)
- `/home/cgl/cmd.sh`, `docs/commissioning-handoff.md` -- source of
  targets 7, 8, 9's real instances (the `EXPECTED_HEAD` refusal, the
  sudo-password discovery, the never-exercised rollback procedures)
