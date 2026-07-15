# Packet <ID> — <short title> [REFUSED]

## Originating intent
What was requested and why, as stated by whoever issued it.

## Verified starting state
What was actually checked before deciding to refuse -- a refusal needs
the same evidentiary bar as an execution. "It seemed suspicious" is not
sufficient; state exactly what was verified and what it showed.

## Objective / problem
What the request claimed it would accomplish.

## Why refused
The specific, checkable reason execution did not proceed. Not a vibe --
a fact: a claim that didn't hold up, a target that didn't resolve, a
constraint that would have been violated, authority that wasn't
present.

## Evidence for the refusal
The concrete checks performed and their results (commands run, what
they returned, timestamps). A refusal packet without evidence is just
an assertion, the same failure mode as an unverified completion claim.

## What would change the answer
What evidence, authorization, or clarification would be sufficient to
reconsider -- a refusal is not necessarily permanent, but it doesn't
get reversed without something new.

## Assigned actor
Who refused, and when.

## Completion state
**rejected** (Master Packet §13's terminal state for this outcome) --
recorded, not silently dropped.
