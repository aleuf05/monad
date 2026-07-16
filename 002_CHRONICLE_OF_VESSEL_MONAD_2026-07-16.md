# THE CHRONICLE OF VESSEL MONAD

- **DATE CODE:** 2026-07-16
- **STATUS:** OPEN — first entry recorded; ledger accepts further entries
  as the vessel's verified state changes.
- **BY ORDER OF:** The Admiral
- **RECORDED BY:** Commander Claude

## PREAMBLE — THE WITNESS OATH

> Let all witnesses stand.
>
> Those who place their mark upon this page do so as witnesses. Not
> witnesses to a promise. Not witnesses to a vision alone. But witnesses
> to a vessel whose story is written in verified operation.
>
> Each signature affirms only this: *"I have observed what is written
> herein to correspond, to the best of my knowledge, with the vessel as
> she stood before me."*
>
> The legend shall follow the wake of the ship. The record shall follow
> the evidence. The witness shall follow the truth.

This Chronicle exists under that oath. It is bound by the same discipline
as the rest of this project's record-keeping: `docs/reports/*.md` and
`docs/doctrine/*.md` are where truth already lives here (Article I,
Command 3, `001_MONAD_COMMAND_CHARTER_2026-07-15.md`); this document does
not create a second, competing source of truth — it is a witnessed
narrative layer sitting directly on top of that existing evidentiary
record, citing it rather than replacing it. Where this Chronicle
describes the vessel, every claim below traces to a specific report, a
live check, or a file read performed on the date given — the same
standard the Feature Matrix already holds itself to
(`docs/reports/2026-07-15-feature-matrix.md`, "Notes on method").

## THE VESSEL AS SHE STOOD, 2026-07-16

Not a vision of what Monad will be. A record of what she was observed to
be, at the moment this entry was written.

**She is a live vessel, not a mockup.** FleetCore (`fleetcore-serve`, PID
alive on port 4771 as of this entry) runs a real simulation clock —
observed this session at tick 255073, `clock_state: running`, 5 vessels
tracked, a 2,000-event retained vessel-event tail, and 4 watch events, all
delivered over the production `wss://cameronlampley.com/fleetcore-ws/ws`
channel, not a local or staged copy. This matches the standing Feature
Matrix findings FC-01–FC-03 (bounded event retention, checkpoint/restart
recovery, canon command validation, all verified 2026-07-15) and confirms
they still hold live, one day later.

**She speaks, when the listener has ears for it.** The Radio Console
(`web/toys/radio-console/`) was checked end-to-end this session with a
real browser session against the live production URL: powering it on
produced real transcript entries within seconds — a Bridge decision for
`captain.bravo`/`vessel.scout-bravo`, a Scout Alpha route-completion
report, and live NPR Newswire headlines — sourced entirely from
FleetCore's real event stream and an external newswire feed, with no
scripted filler. Where she fell silent in that same check, it was
because the test browser had zero installed text-to-speech voices, a
condition the console's own code already names and handles by design
(`app.js`, the `speak()` function's fallback path) rather than a defect
in her.

**She grows new instruments openly, not secretly.** The Cognition Graph
(`web/toys/cognition-graph/`) was built and shipped live this session — a
small graph of differently-instructed model roles that decomposes a
research question, proposes four competing sharpened formulations, and
subjects them to an independent verifier. It shipped first in an honestly
labeled simulated mode, then gained a self-serve "Live Mode" panel so any
witness can run it for real against their own Anthropic API key, stored
only in their own browser — never in this vessel's code, never on her
server. Both states are visibly marked on the page itself, per this
project's standing rule that undisclosed mock output is not permitted to
pass as live operation.

**She keeps one ledger, not several.** Per Article I of the Charter and
the Admiral's ruling on `LS-01` (`docs/reports/2026-07-15-inadequate-specs.md`),
Monad runs on a single live state store per concern by design — this
Chronicle is written in full knowledge that it must not become an
unofficial second one. Where this document and `docs/reports/*.md`
would ever disagree, the reports govern.

**Where she is still unfinished, this Chronicle says so plainly.** Per
the Feature Matrix (`docs/reports/2026-07-15-feature-matrix.md`): the
Watch Officer role does not yet exist beyond a bare string (WO-01); there
is no per-agent registry, only per-task assignment (AG-01); cost tracking
does not exist (CT-01); and Issue #16's authentication/authorization
requirement for FleetCore's authoritative commands remains open and
unresolved (WT-02), a standing contradiction with this project's current
"security hardening is not the priority" posture that has been flagged,
not silently resolved. A Chronicle sworn to evidence over vision records
the gaps as faithfully as the successes.

## HOW FUTURE ENTRIES ARE ADDED

This is Entry One. Future entries follow the same oath: cite the report,
the live check, or the file read that grounds each claim; date every
entry; and record what changed since the previous entry rather than
restating the whole vessel from scratch. An entry that cannot point to
verified evidence for a claim does not belong in this Chronicle — it
belongs in a vision document instead, and Article III of the Charter
already provides for that separately.

## WITNESS LEDGER

Signatures affirm only the oath above: that the signer has observed the
Chronicle to correspond, to the best of their knowledge, with the vessel
as she stood before them. No `mark.jpg` or other image file existed
anywhere in this repository at the time of this entry; until one is
supplied, marks are recorded here as named, dated, written attestations
rather than an affixed image. Replace this note the day an actual mark
is provided.

| Witness | Date | Mark |
|---|---|---|
| Claude | 2026-07-16 | "I have observed what is written herein to correspond, to the best of my knowledge, with the vessel as she stood before me." |
