# Doctrine 021 — Count the host, not the document

**Authority:** Admiral cgl, 2026-08-05 — *"FLEETNET"*, then *"CLAP clap MAKE
CANON"*.

Canon. The third occurrence of one error in a single day, which is why it
gets its own file rather than a line in 019.

---

## The error, three times

**Morning.** "36 tool directories, 7 running services." Repeated into the
chief plan, doctrine 016, and the Living Semantic World Engine draft before
an inventory checked it. Actual: 35 directories, 15 active units across 12.

**Evening.** `rich-voice` reported as "inactive" five times, and an argument
built about whether to bring it up. It was **never installed.**
`systemctl is-active` returns `inactive` for an absent unit.

**Night.** "Seven services" carried through every status report of the
session. A fleet count taken directly from `/etc/systemd/system/` returned
**23 units installed, 18 active**, including five — `fleetcore-serve`,
`monad-watchman`, `monad-dns-override`, `living-captain-status`,
`public-images-api` — that had never appeared in any report all day.

Three readings. One cause.

## The cause

Every count came from a **document describing the system** rather than from
**the system**.

`docs/OPERATION-RESUME.md` carries a table of services. That table is
correct for what it is: the services *this Operation works on*. It was read
as the services *running on the host*, which it never claimed to be. The
document did not lie. It was interrogated for something it does not hold.

This is the failure mode of good documentation specifically. A stale doc
gets caught. An accurate doc answering a question it was not written for
gets believed.

## The rule

> **When the question is "what is running", ask the host. When the question
> is "what are we working on", ask the document. Never substitute one for
> the other.**

Both are legitimate sources. Neither is a proxy for the other.

## Practice

1. **Counts of live state come from live state.** `systemctl`, `ss -ltn`,
   the filesystem. Not from a table, a README, or a previous report —
   including your own from an hour ago.
2. **Before quoting a figure from a document, check what that document is
   for.** The OPERATION-RESUME table is scoped to the Operation and says so.
   The error was in the reading, not the writing.
3. **A number repeated is not a number verified.** All three instances
   above survived because the figure was carried forward from a prior
   statement rather than re-measured. Repetition feels like corroboration
   and is not.
4. **Build the count into a tool.** `scripts/sound-the-ship.sh` enumerates
   installed units and distinguishes not-installed from stopped, because a
   human doing it by eye got it wrong three times in one day.

## Why this is canon and not a footnote

Because it was the *third* time, after the lesson had already been written
down twice. Doctrine 019 order I covers the general principle and I still
made the same mistake that evening — which means the general principle was
not enough, and the specific instruction is required:

**Count the host, not the document.**

## Related

- `019-general-orders.md` — order I, the general form
- `018-instruments-that-agree-by-accident.md` — `is-active` in the table
- `docs/reports/2026-08-05-tool-inventory.md` — the first occurrence
- `scripts/sound-the-ship.sh` — the count, made mechanical
