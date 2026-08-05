# Queries — "Chief Resolve"

One file per open question routed to the Chief. A query is the record of
a single thing that blocks work and that only the Chief can settle.

**Trigger:** when the Admiral says **"Chief Resolve"**, do the procedure
below. Established 2026-08-05; first instance
`MSIR-M3-Q1-object-identity.md`.

## The procedure

1. **Identify the one blocking question.** Exactly one. If several
   things are open, pick the one the others resolve *behind* — usually
   the referent that later structure depends on. The Admiral's
   instruction was "resolve 1 question," and the discipline is the
   point: a bundle comes back partially answered or not at all.
2. **Write it here** as `<ID>-<slug>.md`, following the shape below.
3. **Commit it.** The Admiral carries it to the Chief.
4. **Park the dependent work.** Don't build past the blocker while the
   query is open; note the query as the reason work is parked.
5. **File the response** when it comes back, under the normal
   documentarian flow (`../../doctrine/012-documentarian-packet-scheme.md`,
   `../../doctrine/013-packet-lifecycle-and-refusal-review.md`), and
   mark this query answered.

## The shape that works

- **The question, once, in plain prose.** Not notation.
- **Why this question and not the others** — normally "the rest resolve
  once this does."
- **3-4 candidate answers in a table**, each with what it would imply
  for the build and whether the thing already exists. The Chief can
  then *pick* rather than restate.
- **What counts as a sufficient answer**, with a worked example at the
  right altitude.
- **What is not being asked**, so scope doesn't expand in transit.

Rationale, since it's easy to lose: packets from the Chief arrive in
heavy formal notation that is complete about structure and silent about
referents. A question sent back in plain prose with pickable options
comes back answerable. An open-ended one comes back as more notation.

Observations about which candidate is cheapest or riskiest are welcome
and should be labelled as observations. The choice is the Chief's.

## Status convention

Each query ends with a status line: **open**, **answered**, or
**withdrawn**. Answered queries stay here — like refusals, they are the
record of what was asked and when, and they are not rewritten once a
response arrives (`013` §3.3).

## Relationship to the other mechanisms

A fourth coordination mechanism, bounded against the existing three
described in `../packets/README.md`:

- **`cmd.sh`** — privileged execution.
- **Work queue (`../queue.md`)** — non-privileged tasks to be done.
- **`../packets/`** — records of work done or refused.
- **`queries/` (here)** — questions blocking work, routed outward to a
  person who can answer them.

The distinction from the work queue: a queue task is something *to do*.
A query is something *to find out* before there is anything to do.
