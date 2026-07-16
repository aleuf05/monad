# PROJECT MONAD COMMAND CHARTER

- **DATE CODE:** 2026-07-15
- **PRIORITY:** HIGHEST
- **STATUS:** PROVISIONAL — not yet adopted; see Article V
- **FROM:** The Admiral
- **TRANSCRIBED BY:** Commander Claude

## PREAMBLE

Effective immediately, the founder and commanding authority of Project Monad
holds three offices, united under one command:

- **Commander of Architecture** — how the system remains whole.
- **Admiral of the Fleet** — how the system acts.
- **Chief Visionary** — why the system exists.

Mission (Chief Visionary office, vision layer):

> *To fill the Galaxy with joy and wonder, carrying the spirit of humanity's
> first living incubator outward to all ships, all stars, and all futures
> yet unnamed.*

This mission is aspirational framing, not a technical roadmap. It is
explicitly subordinate to Article III, Command 1 below.

---

## ARTICLE I — Commander of Architecture

Authority over coherence, integrity, and long-term structure.

1. **One source of truth per concern.** No replicated data stores, standby
   copies, or backup daemons stood up as default hygiene. A real need
   (a stated incident, an explicit recovery requirement) is evaluated on
   its own merits when it appears -- it is never assumed in advance.
   (Standing precedent: `LS-01`, `docs/reports/2026-07-15-inadequate-specs.md`.)
2. **`web/` is the single deploy target.** No parallel staging path, no
   throwaway port or subdomain standing in for the real thing. Every
   feature is reachable by clicking from `https://cameronlampley.com/`.
3. **The work queue / report queue split is the system of record.**
   Action lives in `docs/engineering-orders/queue.md`; truth lives in
   `docs/reports/*.md` and `docs/doctrine/*.md`. Completed work is
   removed from the queue, not marked done in place.
4. **Adjudicates document contradictions** when engineering raises one
   (e.g. a standing policy vs. a specific open issue) and no existing
   ruling covers the case -- see Article II, Command 1 for who signs off.
5. **Privileged/irreversible infrastructure changes route through
   `cmd.sh` per `docs/commissioning-handoff.md`**, never executed
   directly by an agent session.

## ARTICLE II — Admiral of the Fleet

Final operational authority over all Monad vessels, systems, stations,
agents, and missions.

1. **Sole ruling authority on any item marked `blocked-on-human`** in the
   work queue. An agent may recommend; only this office decides.
2. **Sole authority to adopt, amend, or reject doctrine** (e.g.
   `docs/doctrine/001-verification-command-dialect.md`). A doctrine
   remains "Proposed" until this office marks it "Adopted."
3. **Sole authority to authorize irreversible or shared-state-altering
   actions** -- worktree archival, fleet resets that affect every
   connected visitor, and any privileged commissioning step in `cmd.sh`.
4. **Delegates routine execution** to the Captain (Officer of the Deck)
   and Lieutenant (Operations Officer) under standing doctrine. Routine
   engineering work that stays inside established policy does not require
   this office's individual sign-off.
5. **Reviews and rules on any judgment call an agent explicitly flags**
   as outside its own authority to decide (the refusal path, not a
   rubber stamp -- an agent that can verify and act inside policy should,
   without waiting on ceremony).

## ARTICLE III — Chief Visionary

Guardian of Project Monad's purpose, identity, ambition, and future
direction.

1. **Narrative follows reality.** This office sets aspirational framing;
   it does not authorize skipping verification, testing, or established
   engineering doctrine to chase it. The existing house doctrine
   (`DOCTRINE: NARRATIVE FOLLOWS REALITY`, `web/index.html`; Commander
   Claude's standing quote, `web/staff.html`) governs any conflict
   between vision-layer language and verified technical state.
2. **Any change to Monad's stated purpose or identity is recorded through
   this office**, not asserted implicitly by a single feature, commit, or
   agent's own initiative.
3. **Reconciles ambition with capacity.** Scope proposed at this office's
   direction still passes through the same gates as any other work:
   Architecture's coherence rules, the Admiral's operational sign-off
   where required, and live verification before anything is called done.

## ARTICLE IV — Relation to Existing Command

1. This charter does not supersede the Captain's or Lieutenant's existing
   delegated authorities (e.g. the Lieutenant's call on worktree
   archival, `HUMAN-02`) unless a future article explicitly revokes one.
2. Existing roles as recorded on the staff roster (`web/staff.html`,
   `web/command-deck.html`) continue to operate as documented. This
   charter defines the offices above them, not a replacement for them.

## ARTICLE V — Status

This charter is **PROVISIONAL**. It takes effect as governing structure
only once the Admiral marks this Status line **ADOPTED**, per the same
human-approval discipline this project already applies to doctrine
(Master Packet §15; see `HUMAN-04`'s resolution of Doctrine 001 for
precedent). Until then, it is a drafted structure available for
correction, not a standing order.
