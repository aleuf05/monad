# Process Analysis — Two-Agent Coordination System

Date: 2026-07-15

Prepared for: Captain / Lieutenant / Admiral

Scope: analysis of the coordination process built and run live this
session (`cmd.sh`, `queue.md`, `packets/`, Doctrine 001) -- not the
Monad project's features, the process itself.

## What worked

**Git-as-lock scaled cleanly.** 23 queue tasks split across two
independent agent sessions (Claude, Codex), zero collisions, zero
silent overwrites. The claim mechanism (pull, single-line status edit,
commit, push, back off on rejection) needed no new infrastructure --
git's own fast-forward check was sufficient.

**Division of labor emerged without being assigned.** Broader
synthesis tasks (Architecture Map, System Reality Report, section
audits) skewed toward Codex; detailed source-reading verification
(Watchman, Bridge, Periscope, Golden Hull) skewed toward Claude.
Nobody designed that split -- it fell out of whoever claimed first plus
available context.

**Doctrine got field-tested inside the session it was written.**
Doctrine 001 was drafted, then used to reason through a real refusal
(the ENG-1 packet) before the session ended, and was itself amended
(`DOC-02`) after a real operational cost (a 2-minute DNS hang) exposed
a gap in its own verification-requirement language.

**Three mechanisms stayed bounded against each other.** `cmd.sh`
(privileged), `queue.md` (lighter non-privileged tasks), `packets/`
(state-changing work or refusals) never overlapped ambiguously about
which one governed a given piece of work. The one real leak (an agent's
commit accidentally carrying another agent's uncommitted edit, because
both share one working directory rather than separate clones) was
disclosed immediately, not hidden, and is now named explicitly in
Doctrine 001 (Missing Constraint).

## What didn't scale

**`queue.md` itself became the bottleneck it was built to prevent.**
By session's end it held 27 entries and 460+ lines, mixing full
method/evidence text for 19 *done* tasks with the handful still
actually actionable. Finding current status required repeated
`grep`/full-file reads -- the same "hard to scan for what's real"
problem this whole session existed to solve, recurring inside its own
tooling.

**A fourth status (`blocked-on-human`) was introduced ad hoc before
being documented.** Used for `SPEC-01` before `AGENTS.md` was updated
to define it -- caught and fixed the same session
(`docs/reports/2026-07-15-inadequate-specs.md`'s own pattern,
recurring in the process meant to prevent it), but it shouldn't have
shipped undocumented in the first place.

**Governance now outpaces decision-making.** Four `HUMAN-*` entries are
queued, zero resolved. Correct behavior (agents shouldn't make these
calls), but it means the process's output rate now exceeds the rate at
which a human can absorb and rule on it -- worth pacing future sweeps
against decision throughput, not just task throughput.

## Proposed fix, pending confirmation

Split `queue.md` into **`work-queue.md`** (still-actionable and
`blocked-on-human` entries only) and **`report-queue.md`** (a thin
index of completed work -- one line per item, pointing at its real
evidence, not duplicating `docs/reports/`'s content). Transition is one
atomic commit: cut from work-queue, append index line to report-queue.
Same claim protocol, same pull-first discipline, applies to both files.

## Bottom line

The process is sound at the mechanism level -- git-as-lock, three
bounded coordination channels, doctrine that gets tested rather than
just written -- but a single flat file stopped scaling past roughly 20
entries. That's a capacity limit on the *filing system*, not on the
coordination model itself, and the proposed split addresses it without
changing anything about how claiming, execution, or evidence recording
actually work.
