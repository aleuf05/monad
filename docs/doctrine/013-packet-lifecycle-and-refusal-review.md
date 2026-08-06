# Doctrine 013 — Packet Lifecycle and Refusal Review

**Status:** Active, provisional — v0.1, effective 2026-08-05.
**Explicitly revisable.** See §6 before treating anything here as fixed.

Complements `012-documentarian-packet-scheme.md`; does not replace it.
012 settles *whether* packets get read before filing. This describes
*how* they move through the system once they arrive, and — new here —
what happens to a packet that was refused.

---

## 1. Why this exists

Two gaps showed up in practice, both worth closing:

1. Packets had a way in (chat, now also the Root Console drop box) and a
   way to be filed, but no described path between those states. It
   worked because one session held it in its head. That doesn't survive
   a new session.
2. **Refusal had no exit.** 18 refused packets currently sit in
   `docs/engineering-orders/packets/`, 19 of which carry a "What would
   change the answer" section — a stated condition for reconsideration
   that nothing was ever going to check. A refusal that can only ever
   stay refused is a dead end, not a decision.

## 2. The lifecycle, as it actually runs

```
  arrival          staging            evaluation          disposition
  ───────          ───────            ──────────          ───────────
  chat paste  ─┐
               ├─→  docs/incoming/  ─→  read in full  ─→  filed
  .docx drop  ─┘    (staged, not         (doctrine 012)    or refused
   (Root Console)    yet judged)                           or research-split
```

- **Arrival** — pasted into chat, or dropped on the Root Console's
  Packet Drop panel (`tools/docx-intake/`). Both are transport. Neither
  is filing.
- **Staging** — `.docx` drops land in `docs/incoming/` carrying an
  explicit "staged, awaiting evaluation" header, and render in the
  Semantic Document Viewer under a distinct `staged` status. Staged
  material is visibly *not* a filed document.
- **Evaluation** — the packet is read. This is doctrine 012's item 3 and
  is the one part of this pipeline that isn't a matter of convenience.
- **Disposition** — one of:
  - **filed** — `logs/captains/`, `docs/reports/`, or `docs/doctrine/`,
    with source, epistemic label, and (per this session's standing ask)
    a separate, clearly-labelled section carrying the reader's own
    assessment. Verbatim content and opinion never blend.
  - **refused** — `docs/engineering-orders/packets/<ID>-REFUSED.md`,
    per `template-refused.md`, with evidence. A refusal is an outcome
    with a trail, not an absence of one.
  - **research-split** — 012's carve-out: a packet can fail as an
    infrastructure claim and still contain real research. The two are
    evaluated separately; a REFUSED filing is never retracted, and the
    research answer lives separately in `docs/reports/`.

## 3. Refusal review — the new part

A refusal is a decision about *what was submitted, when it was
submitted*. It is not a permanent verdict on the underlying question.
Those are different things, and conflating them is what made refusal
feel like a dead end.

### 3.1 What triggers a review

Any of:

- The Admiral asks for one, on any packet, at any time. No justification
  needed and no waiting period.
- The packet's own "What would change the answer" condition looks met.
- Something in the world changed — a service now exists that didn't, a
  doctrine was revisited, a claim became checkable.

### 3.2 What a review does

Re-read the original packet and its stated reconsideration condition,
then check the condition against current reality — with evidence, the
same bar the refusal itself had to clear. Land on one of:

| Outcome | Meaning | What gets written |
|---|---|---|
| **resolved** | The condition was met. The work can proceed. | A `## Review` section appended to the original, dated, naming the evidence; the new work filed normally as its own packet/report. |
| **standing** | Reviewed; condition not met. | A `## Review` section, dated, one or two lines. Cheap on purpose — a review that costs a lot won't get run. |
| **moot** | Circumstances changed enough that the question no longer applies. | A `## Review` section saying so. |
| **partial** | Part of it clears, part doesn't. | Split it: the clearing part proceeds as new work, the rest stays refused. This is the research-split pattern generalised. |

### 3.3 The one hard rule

**The original refusal is never rewritten, retracted, or deleted.** It
stays as the accurate record of what was submitted and how it was read
at the time. A review *appends*; it never edits history. This already
happened once organically and correctly —
`VENNA-SPEECH-TO-INTENT-REFUSED.md` was reviewed, its research content
carried out and filed separately, and the refusal left standing (012's
research carve-out records this). That precedent is the model.

The reason this rule is hard while the rest is soft: a record that can
be revised under pressure stops being a record. Everything else in this
document is mechanics and can move.

### 3.4 Not a re-litigation channel

Review checks a *stated condition against evidence*. It is not a route
for re-asking the same question in new words — several refusals on file
are already repeat submissions, and 012's confirmed baseline covers
that. Repetition or urgency isn't new evidence. Genuinely new terms,
or a changed world, are.

## 4. What "canon" means here

Filing something as canon means: this is the current best record, it is
citable, and it doesn't quietly change. It does **not** mean settled
forever, and it does not mean a document's own self-declared status is
binding. Several packets in this corpus label themselves "Canonical
Core Record" or "Approved" in their own text. Those are the document's
claims about itself; filing preserves them verbatim as such and grants
nothing further. Canon status comes from being filed, not from asking.

## 5. Room deliberately left

Things this doctrine intentionally does **not** decide, because they
should be decided by use rather than in advance:

- Whether reviews should batch (a periodic sweep of all 18 refusals) or
  stay one-at-a-time. Currently one-at-a-time; a sweep would be easy to
  add.
- Whether the Root Console should grow a review surface — a "refused"
  filter in the viewer, a review button per packet. Plausible, unbuilt.
  The viewer already knows each document's status, so most of the
  machinery is there.
- Whether outcome vocabulary beyond resolved/standing/moot/partial is
  needed. Add terms when a real case doesn't fit, not before.
- Whether staged material should auto-expire, and after how long.
- Anything about privileged work — `cmd.sh` and
  `docs/commissioning-handoff.md` still own that, untouched here.

## 6. How to change this document

Say so. That's the whole process — no packet required, no ceremony.
Amend it in place, bump the version line, note what changed and why.
This is v0.1 and expected to move; it was written after roughly one day
of the pipeline actually running, which is enough to describe what
happens and not nearly enough to be confident about what *should*.

Two things that don't move by casual revision, stated plainly so the
rest can be genuinely open:

- Doctrine 012's read-before-filing step (§2, "Evaluation").
- §3.3, the no-rewriting-refusals rule.

Both have been tested repeatedly and both are load-bearing for
everything else being trustworthy. Everything else here — the staging
directory, the outcome vocabulary, the review triggers, the file layout,
the pipeline diagram — is mechanics, and mechanics should improve.
