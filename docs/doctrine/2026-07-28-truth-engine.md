# The Truth Engine

Date: 2026-07-28

Source: Captain transmission to the Admiral, relayed by Lt. cgl

Classification: Project doctrine draft (Doctrine 003 capture — not yet Admiral-adopted per Article II.2)

## Transmission, verbatim

> Monad will become a system for confronting uncertain reality without
> collapsing into either dogma or chaos.
>
> Its purpose is not to declare truth from authority. Its purpose is to help
> a human and a machine jointly move from observation to understanding with
> discipline.
>
> Every serious inquiry will pass through the same living structure:
>
> Observe what happened.
> Separate fact from interpretation.
> Generate competing explanations.
> Seek evidence that could defeat each one.
> Update confidence visibly.
> Act only at the level the evidence justifies.
> Preserve anomalies for future discovery.
>
> The bold vision is a machine that remains radically open to surprise while
> becoming increasingly difficult to fool.
>
> Not an oracle.
>
> Not a skeptic that says no to everything.
>
> A navigational instrument for reality itself — built to keep curiosity
> alive, certainty honest, and action grounded.
>
> The first implementation should be small: a single "Truth Process"
> workflow inside Monad that accepts an observation and produces an
> evidence map, competing hypotheses, confidence levels, disconfirming
> tests, and the safest next action.
>
> One disciplined inquiry at a time, Monad learns how truth is approached
> without pretending truth has already been captured.

## Relationship to existing doctrine

Directly continuous with the Doctrine of Truth
(`docs/doctrine/2026-07-27-continuity-truth-living-captain.md`)'s five-way
label set (Observed / Derived / Simulated / Narrative / Unknown) and with
Doctrine 001's repair phrases (confidence is not evidence, a passing test
proves only what it examined). The Truth Engine operationalizes those into
a repeatable per-inquiry workflow rather than a one-time labeling
convention.

## First implementation (shipped 2026-07-28)

`web/toys/truth-engine/` — a bounded, read-only, client-side instrument
following the Cognition Graph's precedent (`web/toys/cognition-graph/`):
mock mode by default (deterministic simulation, clearly labeled), optional
BYO Gemini API key for a live run, key stored only in the visitor's own
browser. No new backend, no new privileged infrastructure — matches API
Economy doctrine (expensive reasoning invoked only when a key is supplied)
and the "small first implementation" instruction above directly.

Stages implemented: Fact/Interpretation Split -> three competing
Hypothesis generators -> Disconfirming Test designer -> Confidence &
Safest-Next-Action synthesis -> a persistent (this-browser-only) Anomaly
Ledger carried across runs.

This is a draft capture, not a canon promotion — building the small
reversible instrument is ordinary engineering work under existing policy;
it does not itself assert this doctrine as adopted project purpose.

## Conversational protocol

[`CaptainChat — Truth Session v1`](../research/TRUTH_SESSION_V1_DRAFT_2026-07-28.md)
is the compact, non-canonical conversation format for applying these
observation, inference, uncertainty, and next-action boundaries in real time.
