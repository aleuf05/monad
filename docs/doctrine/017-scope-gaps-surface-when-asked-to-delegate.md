# Doctrine 017 — Scope gaps surface when you ask who else could do it

**Authority:** Admiral cgl, 2026-08-05 — *"Can live captain handle?"*, then
*"Very Good Document that Interaction Make Canon."*

Canon. This records a specific interaction because the mechanism in it is
reusable, not because the outcome was dramatic.

---

## What happened

The Admiral asked whether the Live Captain could take on the root console
layout work. Answering required reading `tools/live-captain/scope.json` —
the declaration written earlier the same day listing what the Captain may
never do.

The `never` list named `web/`, `tools/`, `scripts/`, and
`docs/doctrine/`. It did not name **`console/`**.

`console/` is served directly by Caddy at `cameronlampley.com/root` with no
build step. Editing it is editing production, exactly as `web/` is. The
declaration that existed specifically to bound a semi-autonomous agent had a
hole in it precisely where the work in question lived.

The gap was closed immediately, with a note in the file recording how it was
found.

## The mechanism worth keeping

**Asking "could someone else do this?" is a scope audit that costs nothing.**

The gap had been sitting in the file for hours. It was not found by reading
the file, by testing, or by review — all of which had happened. It was found
because a delegation question forced the file to be read *against a specific
task* rather than in the abstract.

A boundary reads as complete until you check it against a concrete job. The
question "can X handle this?" does that automatically, because it makes you
enumerate what X would have to touch.

## Practice

- When considering delegating work to any bounded agent, **read its scope
  declaration against that specific task before answering.** The answer is
  secondary; the reading is the point.
- Record how a gap was found in the declaration itself, not only in a
  commit message. `scope.json` now carries that note inline.
- A gap found this way is a **fact about the declaration**, not a fault of
  the agent. Nothing had violated the boundary. It simply was not there.

## Why this is canon rather than a report

The generalisation is not about the Live Captain or about `console/`. It is
that **an untested boundary is an assumption wearing a boundary's clothes**,
and delegation questions are the cheapest available test. This repo already
holds the same lesson in three other forms — a metric that was wrong until
something was measured against it, an orphan scan that was wrong until run
against a known-live directory, a claim about the corpus that was true only
of one asset. Same shape each time: the artefact looked finished until it
met a specific case.

## Related

- `tools/live-captain/scope.json` — the declaration, and the inline note
- `docs/doctrine/016-chief-conference.md` — the same discipline applied to
  architectural claims: check the numbers before leaning on them
- `docs/reports/2026-08-05-tool-inventory.md` — the orphan scan that would
  have recommended deleting live code
