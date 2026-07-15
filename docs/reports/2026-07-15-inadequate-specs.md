# Inadequate Specifications — Findings

Date: 2026-07-15

Prepared for: Captain / Lieutenant / Admiral

Scope: specs encountered this session that are not executable as
written -- missing a required input (not merely under-detailed), or
evaluative language with no checkable form. Distinct from a confirmed
absence (`WO-01`, `CT-01`, etc.), where the spec was clear and the
thing simply doesn't exist. This report is about the spec itself, not
what it describes.

Related: `docs/doctrine/001-verification-command-dialect.md`, Target 3
(Missing Constraint) and Target 9 (Silent Dependency).

## 1. LS-01, PROV-01, DRIFT-01 -- missing a required input, not just under-detailed

These three queue entries (from the Admiral's 2026-07-15 order) each
omit one fact that Engineering cannot infer safely:

- **LS-01 (Litestream):** does not name which database to replicate.
  `data/world-intake.sqlite3` was inferred as the only sqlite database
  in the repo, but the order never said so -- an inference is currently
  standing in for a spec.
- **PROV-01 (provision.sh):** "a disposable node" has no referent -- no
  hostname, no environment. This is the same underspecification pattern
  as the ENG-1 packet's fabricated hosts, minus the fabrication: the
  target is simply missing, not false.
- **DRIFT-01 (drift detection):** "drift" is undefined -- could mean
  config drift, the `toys/`-vs-`web/toys/` deploy drift already handled
  manually this session (`TOY-01`), or something else. The order names
  a technique (report-only, false-positive measurement) without naming
  its object.

None of these three are ready to execute as written. Each needs one
missing fact supplied before Engineering can start, not just before it
can finish.

## 2. Master Packet §6 -- a name list, not a spec

"Orbit, follow, intercept, maintain sector, return" are given as words
with no defined acceptance behavior. `EP-01` could only map existing
FleetCore `EscortPosture` variants to names that already matched
structurally (`AdvanceScreen` -> screen, `InvestigateContact` ->
investigate); the unmapped names are unfalsifiable as written -- there
is no way to say "intercept is implemented" or "intercept is missing"
in a checkable sense, because the spec never states what intercept
should actually do.

## 3. Master Packet §16 (GOLDEN HULL) -- categories without thresholds

"SI scale, collision envelopes, orientation, validation" are named
without a tolerance, a reference definition, or a pass/fail line.
`GH-01` could only report presence/absence of *any* mechanism (none
exists for scale/collision/orientation), not whether a mechanism would
actually satisfy the spec, because the spec never defines what
satisfying it would look like.

## 4. Master Packet §19 (UX principles) -- evaluative language, not a spec

"Disciplined playfulness," "useful dramatic framing," "minimal
ambiguity" have no checkable form as written. `UX-01` had to explicitly
narrow its own scope to only what's objectively observable (e.g.
whether the live site visibly distinguishes verified data from
narrative content) rather than attempt to grade the whole section.

## Recommendation

Before queuing further design work off verbal orders, require the
one-line minimum this session already learned the hard way: name the
target explicitly, or the spec isn't a spec yet, it's an intention.
Concretely, `LS-01`/`PROV-01`/`DRIFT-01` should not be claimed until
their missing inputs (database, node, drift definition) are supplied.
