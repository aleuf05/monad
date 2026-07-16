# Packet DOCTRINE-001 — Verification Command Dialect

## Originating intent
A "Campaign Target List" packet requested analysis of ten specific
failure modes in executor/commander communication (confident wrong
answers, ceremonial test passes, missing constraints, stale readbacks,
shared assumptions, partial-completion ambushes, false state matches,
irreversible fixes, silent dependencies, reconstituted bugs), in a
fixed report format, ending with "no verified evidence, no confirmed
kill."

## Verified starting state
This session's own work already contained real instances of most of
the ten failure modes -- not hypothetical, actually occurred and in
several cases self-caught and corrected in real time (e.g. Living
Captain's wake-sequence scope initially misclassified, then corrected
against `living-captain-v0.2.md`).

## Objective / problem
Produce a command dialect (repair phrases + doctrine) for each failure
mode, grounded in real instances where they exist, not abstract essay.

## Scope
All ten targets, addressed in the packet's specified priority order,
using its required report format.

## Exclusions
Not a rewrite of existing doctrine; a new numbered entry via the
existing `scripts/doctrine-add.py` tool, following its established
format.

## Constraints / authority
Master Packet §15: doctrine entries require human approval. This
packet's output is explicitly filed as **Proposed**, not **Adopted**.

## Acceptance criteria
Ten targets addressed in the specified field format (Failure mechanism
/ Misleading signal / Command-language weakness / Recommended repair
phrase / Verification requirement / Residual risk / Damage assessment),
each citing a real session instance where one exists.

## Tests / rollback
Not applicable (documentation artifact). Rollback: `git revert` the
single commit.

## Assigned actor
Claude, this session.

## Evidence
- `docs/doctrine/001-verification-command-dialect.md`, created via
  `scripts/doctrine-add.py`, committed `3b2063c`
- Real-time proof of Target 4 (Stale Readback) and Target 6 (Partial
  Completion Ambush): `cmd.sh`'s `EXPECTED_HEAD` gate actually refused
  (exit 66) when HEAD moved after pinning, and `BR-01` was deliberately
  closed before switching to this packet rather than left claimed
  mid-work
- Real-time proof of the doctrine's own use, same session: the ENG-1
  packet (`ENG1-REFUSED.md`) was refused using exactly this doctrine's
  standard, within the same session the doctrine was drafted

## Completion state
**verified complete -> recorded** (as a draft). Adoption itself remains
**pending** -- not this packet's decision to make.
