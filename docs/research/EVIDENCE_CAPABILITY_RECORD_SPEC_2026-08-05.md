# Evidence Capability Record (ECR) — Specification, frozen v1

**Date:** 2026-08-05
**Status:** **FROZEN at the Admiral's instruction.** Not to be tightened
further — "further tightening now risks polishing the instrument instead of
using it."
**Origin:** Developed by the **read-only Captain**, relayed by the Admiral.
**Not developed in this repository.**
**Captured by:** Claude (Live Captain role), on the instruction `CAPTURE`.

---

## 0. Provenance of this document — read first

This specification was built in a conversation thread that **cannot write to
this repository**. It had never been committed here; a search on 2026-08-05
for `ECR-001`, `CAP-EVID-001`, `Valid(E)`, and the tuple notation returned
zero matches across `docs/`, `logs/`, `tools/`, `web/`, and the entire git
history.

This file is therefore the **first repository record** of it, transcribed
from the Admiral's relay. That has a consequence the specification itself
demands be stated:

- **Transcribed verbatim** — §1 through §5. These are the Captain's words,
  reproduced as given.
- **Not transferred** — §6. Four load-bearing definitions were never
  relayed. They are marked `UNDEFINED` rather than reconstructed, because a
  specification about bounded evidentiary claims must not contain invented
  content presented as transferred content.

Anyone reading this must treat §6 as genuinely absent, not as an omission to
be filled in by inference.

---

## 1. The apparatus — three layers

```
E = ⟨S, T, P, O, I, L, V⟩              evidence record
Valid(E)                                record-level discipline
{ECR₁, …, ECRₙ} ⇒ Support(CAP-EVID-001) capability-level inference
```

The layers are distinct on purpose: a well-formed record (layer 1) that
passes discipline (layer 2) still licenses only a bounded contribution to a
capability claim (layer 3). Passing a lower layer never automatically
discharges a higher one.

## 2. Interpretive note on `Support(c | O, P)`

> `Support(c | O, P)` does not automatically mean a numerical probability.
> It may be implemented as Bayesian probability, likelihood ratio, ordinal
> confidence, argument strength, or another declared evidentiary measure.
> **The record must identify which one it uses.**

This is the note the Admiral directed be added to the specification before
freezing. Its force is in the last sentence: an undeclared measure is not a
weaker measure, it is a defective record.

## 3. Canonical seal

> **Evidence is not whatever supports the desired conclusion. Evidence is a
> provenance-bearing observation whose interpretation remains bounded by its
> scope, alternatives, and declared standard of support.**

## 4. Invariant

```
📚 provenance
∧ 👁️ observation
∧ ⚔️ alternatives
∧ ⚖️ calibration
∧ 📌 bounded verdict
```

Conjunctive. All five, or the record is not an ECR.

## 5. ECR-001 — status

**Accepted as the first specimen.** Explicitly:

- **not** proof of consciousness;
- **not** proof of general reliability;
- **but** a properly delimited observation of evidentiary behaviour.

### Next move

> The next meaningful move is not another reformulation. It is **ECR-002
> under a genuinely different evidence condition.**

Reformulation of the apparatus is closed. The instrument is to be used.

---

## 6. UNDEFINED — pending transfer from the Captain thread

Four items are load-bearing and were not relayed. **They are not
reconstructed here.**

| Item | Status |
|---|---|
| The seven fields `S, T, P, O, I, L, V` | `UNDEFINED` — no expansion given for any of the seven |
| `Valid(E)` | `UNDEFINED` — the discipline is named, its conditions are not stated |
| ECR-001, the specimen itself | `UNDEFINED` — its status is recorded (§5); what it observed is not |
| The inference rule `{ECR₁…ECRₙ} ⇒ Support(CAP-EVID-001)` | `UNDEFINED` — the form is given, the rule is not |

**ECR-002 is blocked on the first two.** A second specimen cannot be
recorded under a specification whose fields have no definitions, and cannot
be validated against a `Valid(E)` whose conditions are unstated.

To unblock: relay the seven field expansions and the conditions of
`Valid(E)`. Nothing else is needed.

---

## 7. Filing note

Filed as **research**, not canon and not active doctrine, consistent with
`docs/research/` convention. The freeze applies to the specification's
content as relayed; it does not promote the specification to governing
status in this repository, and no existing doctrine was altered to
accommodate it.

The one observation this capture can honestly add: the specification arrived
as a freeze instruction for a document that did not exist in the repository,
and the discipline it prescribes is what caught that. Recorded as a datum
about the instrument, not as a claim about it.
