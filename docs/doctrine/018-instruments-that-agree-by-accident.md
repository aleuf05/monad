# Doctrine 018 — Instruments that agree by accident

**Authority:** Admiral cgl, 2026-08-05 — *"MAKE CANON"*, following a
carpenter's sounding and the Chief's read on it.

Canon. This one is uncomfortable and that is why it is written down.

---

## The finding

On 2026-08-05, a full day of engineering produced roughly eight incorrect
claims. Every one was caught. **Not one of them was a logic error, a crash,
or a failing test.** Every single one was an instrument returning a
plausible value that meant something other than what was read into it.

The complete list, because the pattern only shows at volume:

| Instrument | Read as | Actually meant |
|---|---|---|
| `systemctl is-active` → `inactive` | service deliberately stopped | **unit never installed** |
| new bounding-box contact under pose | collision | mostly legitimate articulation (median 8% overlap) |
| `MemoryCurrent` → 356 MB | process leaking memory | cgroup total incl. page cache; RSS was 27 MB |
| grep for `tools/<dir>` | directory unreferenced | missed `sys.path` imports — flagged live code as orphan |
| bounding-box extent | the object's spine | the arm span of a robot holding its arms out |
| `OPERATION-RESUME` service table | services on the host | services *this Operation* works on |
| 0 inverted faces | true of the corpus | true of gasket |
| tests passing | pause flag isolated | suite was reading the operator's real flag |

Eight instruments. Eight plausible readings. Eight wrong.

## The principle

> **An instrument that can return the same value for two different
> conditions is not measuring what you think it is.**

`inactive` for both *stopped* and *absent*. A contact count for both
*articulation* and *clipping*. A green suite for both *isolated* and
*accidentally agreeing with operator state*.

The danger is not that these fail. It is that they **succeed
convincingly**, and the reader supplies the interpretation without noticing
they supplied anything.

## Practice

1. **When reading any status, ask what else produces this value.** If a
   second condition produces it, the reading is ambiguous and must be
   disambiguated before it is reported. `systemctl is-active` needed a
   companion check for whether the unit file exists; that is now in
   `scripts/sound-the-ship.sh`.

2. **Measure severity, not incidence.** Counting *how many* is nearly
   always weaker than measuring *how badly*. Grading contact by overlap
   depth turned 334 "collisions" into 28 real ones.

3. **Gate the premise before instrumenting the output.** Elaborate
   measurement downstream of an unchecked assumption produces confident,
   precise, wrong numbers. See the fit gate in `pipeline.authorize`.

4. **A claim measured on one member is a hypothesis about the class.**
   Four of the eight came from generalising gasket to the corpus. The
   corpus runner exists; use it before claiming.

5. **Verify the machine agrees with the repository.** Config drift is
   invisible unless diffed. `fleetcore-serve` ran for weeks with an
   installed unit older than the repo copy — no functional difference, but
   the host carried a stale account of its own configuration, describing a
   retired LAN setup and the dead `/monad/` prefix as current.

## Why this is canon rather than a lessons-learned note

Because the corrective is not "be more careful." Every one of those eight
readings was made carefully. Care is what produced the confidence.

The corrective is **structural**: build the disambiguating check into the
tool, so the ambiguity cannot be resolved by a reader's assumption.
`sound-the-ship.sh` exists for that reason and found the
`is-active` ambiguity on its first run — after a human had misread it five
times in one session.

## Related

- `scripts/sound-the-ship.sh` — the structural checks, repeatable
- `docs/doctrine/017-scope-gaps-surface-when-asked-to-delegate.md` — same
  shape, applied to boundaries
- `docs/reports/2026-08-05-tool-inventory.md` — the orphan scan that would
  have recommended deleting running code
