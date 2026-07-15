# Engineering Packets

One file per packet, following Master Packet §13's shape exactly. A
packet is the record of a single bounded piece of work, from intent
through verified consequence.

## When a packet is required vs. a lighter work queue task

Use a **packet** when the work changes the repository or a live service
in a way with real acceptance criteria and a rollback path: shipping a
code fix, installing a service, modifying live configuration. The nine
fields below are mandatory.

Use a **work queue task** (`../queue.md`, protocol in
`../../../AGENTS.md`) when the work is synthesis, verification, or
documentation with no runtime/repository-state change beyond the report
itself -- the kind of thing this session's Feature Matrix rows came
from. Lighter claim/done tracking is enough; a full nine-field packet
would be ceremony without content. When such a task completes, its
work queue entry is deleted (not marked done in place) once its
finding lives in the report queue (`docs/reports/*.md`,
`docs/doctrine/*.md`) -- see `../../../AGENTS.md`'s work queue / report
queue policy.

If a piece of work is refused rather than executed, it still gets a
packet -- see `template-refused.md`. A refusal is a real outcome with
its own evidence trail, not an absence of one.

## Fields (Master Packet §13)

1. **Originating intent** -- why this work exists
2. **Verified starting state** -- what was actually checked before
   acting, not assumed
3. **Objective / problem**
4. **Scope** and **exclusions** -- what's in, what's deliberately out
5. **Constraints / authority**
6. **Acceptance criteria** -- checkable, not vague
7. **Tests / rollback**
8. **Assigned actor**
9. **Evidence** and **completion state** -- using §13's lifecycle:
   drafted -> reviewed -> authorized -> assigned -> acknowledged ->
   executing -> verification pending -> verified complete -> recorded.
   Terminal alternatives: blocked, rejected, superseded, rolled back,
   failed safely.

## Relationship to the other two mechanisms

Three coordination mechanisms exist in this repo now, deliberately
bounded against each other:

- **`cmd.sh` / `docs/commissioning-handoff.md`** -- privileged (`sudo`)
  execution only. Single-slot, pinned to an exact commit, run by the
  Lieutenant.
- **Work queue (`queue.md`) / `AGENTS.md`** -- non-privileged, lighter
  synthesis and verification tasks. Multiple tasks queued at once,
  claimed via git's own fast-forward check. Completed entries are
  deleted, not marked done; their findings live in the report queue
  (`docs/reports/*.md`, `docs/doctrine/*.md`).
- **`packets/` (this directory)** -- non-privileged, repository/service-
  state-changing work with real acceptance criteria, or a refusal of
  such work. One packet per unit of work, filed here after the fact as
  a durable record.

A packet's *execution* may still route through `cmd.sh` if it needs
`sudo` -- the packet records the intent/evidence/completion; `cmd.sh`
is how the privileged step actually runs. They are not competing
mechanisms, they cover different layers of the same piece of work.
