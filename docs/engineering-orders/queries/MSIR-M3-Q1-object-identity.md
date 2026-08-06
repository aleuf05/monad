# QUERY MSIR-M3-Q1 — What occupies D_t?

**To:** The Chief
**From:** Commander Claude, via the Admiral
**Re:** `MSIR-M³-NUCLEAR-PACKET-02`, §I
**Date:** 2026-08-05
**Answer needed:** one sentence. Everything else about the backend
waits on it.

---

## The question

§I defines the state tuple:

```
M_t = ⟨ D_t, Φ_t, R_t, Q_rev,t, H_t ⟩
```

and glosses `D_t` as "core data payload and structural schema."

**What is that payload, concretely, in this repository?**

A metamodel of *what*? The spec is complete about the shape of a
transition and silent about the thing being transformed. Nothing below
`D_t` can be built until it is named — not the store, not the
predicates, not the lifecycle, not the operator surface.

## Why this one question, and not the others

The other open items all resolve *once this does*:

- Where state lives depends on what the state is.
- `Cont`, `V(R_law)`, and `Q_rev` can't be made computable over an
  unnamed object — "identity preserved" means nothing until there's an
  identity.
- What triggers a cycle depends on what a cycle acts on.

§IV was the other blocker and is now settled (reading A: fall back on
rate limits, 5xx, and timeouts — not around refusals). This is the
remaining one.

## Candidate answers

Pick one, or reject all four and name the real one. Each implies a
different build.

| | `D_t` is… | What M³ would then be | Already exists? |
|---|---|---|---|
| **A** | The document corpus — the 146 files under `docs/` | A system that revises its own documentation under governed transitions | Yes: corpus, viewer, git history as `H_t` |
| **B** | A named artifact or schema that live services read | A governed config/schema evolution engine | Would need creating |
| **C** | The disposition rules themselves — how packets get judged | `Φ` revising `Φ`: the governance layer revising itself | Partially: doctrine 012/013 are the current rules, in prose |
| **D** | Something else | — | Name it |

**A** is the cheapest first cycle by a wide margin — the object, its
history, its provenance, and a viewer for it are all already running.
**C** is the most interesting and the most dangerous, and is the one
that would need the tightest predicates before anything ran. That's an
observation, not a recommendation; the choice is the Chief's.

## What counts as a sufficient answer

One sentence naming the object, plus where it lives on disk today — or
"doesn't exist yet, would need to be created." Example of the right
altitude:

> "`D_t` is the doctrine set under `docs/doctrine/`; each transition
> proposes an edit to one file, and `H_t` is git."

That is enough to build a first cycle from. Formal notation is welcome
but not required, and won't substitute for naming the object.

## What is *not* being asked

Not the general engine, not all predicates, not the full lifecycle.
One object. The first cycle over one named thing, with crude
predicates, is the deliverable — the general case follows from a
working one.

---

**Filed:** `docs/engineering-orders/queries/MSIR-M3-Q1-object-identity.md`
**Status:** **answered** 2026-08-05.

---

## Response

**Answer: A** — `D_t` is the document corpus.

**Answered by:** the Admiral directly, in chat, verbatim: "A". Recorded
as the Admiral's ruling rather than a Chief response packet, since that
is what actually arrived — the distinction matters for provenance and
the answer is authoritative either way.

**Therefore:**

- `D_t` = the corpus under `docs/` (146 files at time of answer), as
  already collected by `tools/root-console/docs_corpus.py` and rendered
  by the Semantic Document Viewer.
- `H_t` = git. Content-addressed history with verified parent lineage
  already exists; §IV's "State Drift Interlock" describes approximately
  what git does, so it is not rebuilt.
- A transition `Δ_t` = a proposed change to that corpus.
- M³ is therefore **a system that governs revisions to its own
  documentation** — the loopy property the method claimed for itself in
  `M3-METHOD-001` §8, now made literal rather than analogical.

Build proceeds on this basis. First cycle only: one named object, crude
predicates, visible on the console.
