# Doctrine 020 — Authority is permission, not correctness

**Authority:** Admiral cgl, 2026-08-05 — *"ADMIRAL is SUPERUSER"*, then
*"canonically obv"*.

Canon. Short, because it is one idea and the idea is obvious right up until
the moment it is load-bearing.

---

## The standing fact

The Admiral holds full administrative authority on this host. This is
recorded, not asserted: `docs/commissioning-handoff.md` states that `cgl`
has passwordless administrative execution authority, and that **sudo is no
longer itself a human handoff boundary.**

That delegation extends to Captain and to Claude in the course of the work.
On 2026-08-05 it was exercised repeatedly without staging — units installed,
`daemon-reload` run, services restarted, files written into
`/etc/systemd/system/`. None of it required a handoff and none of it was
paused for one.

## The distinction that matters

**Root would not have caught a single error made on 2026-08-05.**

- `systemctl is-active` returns `inactive` for an absent unit to root
  exactly as it does to anyone else.
- Bounding-box extent picks the wrong spine at every privilege level.
- A grep that misses `sys.path` imports misses them as superuser.
- A green test suite reading the operator's live pause flag is green for
  root too.

Eight wrong readings, none of them a permissions problem, none of them
fixable by a higher authority level. Doctrine 019 is entirely untouched by
who is asking.

## Practice

1. **Never let authority stand in for verification.** "I can do this"
   answers a different question from "this is right." The first is settled
   here; the second never is.
2. **Distinguish blocked-on-permission from blocked-on-decision.** Nothing
   in this repo is currently blocked on permission. Several things are
   blocked on a decision, and a decision is the one thing delegated
   authority cannot manufacture — see the four units the repo defines that
   the host never installed.
3. **Do not offer the Admiral authority as a solution to an evidence
   problem.** If a reading is ambiguous, escalating who is reading it
   changes nothing.

## Why it is worth a doctrine at all

Because the failure mode is quiet. A system where authority is broad and
verification is cheap will drift toward acting first, and the acting will
usually work — which is precisely the condition under which an unexamined
instrument stays unexamined. Broad authority *raises* the value of
Doctrine 019, it does not reduce it.

The two go together:

> **Permission removes the need to ask. It does not remove the need to
> check.**

## Related

- `019-general-orders.md` — the six orders, untouched by privilege
- `018-instruments-that-agree-by-accident.md` — the eight readings root
  would also have got wrong
- `docs/commissioning-handoff.md` — the authority itself, and the one
  remaining handoff case
