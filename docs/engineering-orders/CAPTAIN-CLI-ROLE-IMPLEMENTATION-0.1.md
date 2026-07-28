# Captain CLI Assignment — Role/Implementation Independence

**Status:** working context accepted; friction recorded; smallest reversible
step proposed. No broad redesign performed (per instruction 3).

**Source handoff (recorded verbatim, 2026-07-28):**

> Operational roles and model implementations are independent axes. Roles
> such as Captain, Engineer, Operator, Planner, Reviewer, and Archivist
> describe responsibilities. GPT, Claude, Codex, Gemini, local agents,
> tools, and humans are possible implementations of those responsibilities.
> The mapping is fluid and many-to-many: one implementation may perform
> several roles; several implementations may share one role; assignments
> may change during execution; separation is introduced only when it
> provides a concrete operational benefit.
>
> Governing doctrine: stable accountability; fluid allocation of cognition.
> Define invariants, not occupants. Keep obligations stable. Keep occupants
> fluid. Let evidence determine the mapping.
>
> Protected invariants: human authority; truthful reporting; scope control;
> traceability; reversibility; recoverable state; appropriate escalation.

## 1. Working context — accepted

Treated as current working context for this response. Not filed as an
adopted numbered doctrine (Article II.2 reserves adoption to the Admiral
office) — this document is the friction/proposal response to the
assignment, not a canon claim.

## 2/4. Friction observed — role bound to a specific occupant where the role itself doesn't require it

Concrete instances, each with file:line evidence, not assumption:

**a. Living Captain inference — already decoupled in code, pinned by policy.**
`tools/living-captain/model_provider.py:1` is explicitly titled
*"Provider-neutral inference contract for Live Captain Version 1"* and
defines a `ModelProvider` `Protocol` (`model_provider.py:34-46`). The
abstraction already exists. But `web_service.py:build_engine()`
(`web_service.py:272-278`) hardcodes `GeminiProvider(api_key)` directly on
line 278 — no config point
selects the implementation, because `docs/doctrine/model-api-routing.md`
makes Gemini the only commissioned vendor project-wide. **This is not
broken** — the interface exists precisely so a second provider could be
added later without disturbing the Captain role's contract — but the role
("produce the Captain's next utterance") and its current sole occupant
(Gemini) are nowhere named as separate things. The friction is a missing
registry entry, not a missing abstraction.

**b. `tools/voice-engine/rich_voice.py:57`** — same pattern: a `Provider`
`Protocol` exists, `GeminiTTSProvider` (line 97) is the only implementation
wired in. Same shape as (a).

**c. `tools/legend-pipeline/legend_pipeline.py:160`** — tighter binding
than (a)/(b): the Gemini endpoint URL is inlined directly into the
generation function, with no `Provider` interface at all. If this role
("expand a legend seed into prose") ever needed a second implementation,
that would require an actual code change, not a config change. Worth
knowing as the one case where the binding is real, not just policy.

**d. `tools/cloud-image-demo/generate_image.py`** — same shape as (c);
direct call, no seam.

**e. Narrative/doctrine layer — the many-to-many pattern already exists
informally.** `000_HIGHEST_PRIORITY_MONAD_CHARTER_2026-07-14.md` is
"TRANSCRIBED BY: Commander Codex"; `001_MONAD_COMMAND_CHARTER_2026-07-15.md`
is "TRANSCRIBED BY: Commander Claude." The "Commander"/"Captain" role has
already been filled by more than one model implementation across sessions
— exactly the pattern this handoff names — but it was never recorded as a
deliberate mapping, only as an incidental byline. This is evidence the
principle is already true in practice, not a novel proposal.

**f. `AGENTS.md`'s work-queue claim protocol** binds a claimed task to a
named occupant string (`claimed:<agent-name>@<timestamp>`, e.g. Claude or
Codex) for the duration of that claim. Flagging this explicitly as
**intentional, not friction** — it exists for traceability and to prevent
two occupants editing the same files concurrently (AGENTS.md's own "What
this does not solve" section), which is one of the protected invariants
(traceability) named in the handoff. Not a candidate for removal.

**g. `cmd.sh` / `docs/commissioning-handoff.md`** binds all privileged
execution to a single human occupant (the Lieutenant) with no
implementation flexibility at all. **Also intentional, not friction** —
this is the human-authority invariant itself, the one binding the handoff
explicitly protects rather than asks to loosen.

## 5. Proposed smallest reversible step

A pure documentation registry, zero code or runtime change, fully
reversible by deleting one file:

**`docs/architecture/role-registry.md`** — one row per role already
operating in Monad (Captain-inference, Captain-voice, Legend-generation,
Privileged-execution, Task-claimant, Commander/narrative-voice, …), naming:
current occupant(s), whether the binding is *technical* (no seam exists,
like legend-pipeline) or *policy* (a seam exists but is pinned by standing
doctrine, like Living Captain/Gemini), and which protected invariant (if
any) makes that binding deliberate rather than incidental.

This does two things without redesigning anything: (1) it makes the
existing many-to-many reality (item e above) visible instead of implicit,
and (2) it gives future work a place to record *why* a binding exists
before anyone "fixes" a binding that was actually a safety invariant in
disguise (item f, g). No provider code changes, no new vendor
credentials, no change to `model-api-routing.md`'s Gemini-only policy —
that policy is itself a protected-for-now constraint (single-vendor cost
and audit surface), not something this step second-guesses.

Not built yet pending confirmation this is the right shape before
spending the write.

## 6. Invariant preservation check

- Human authority — untouched; `cmd.sh` binding (item g) explicitly
  preserved, not loosened.
- Truthful reporting — this document distinguishes *technical* seams
  from *policy* pins rather than implying every binding is equally easy
  to change.
- Scope control — no code changed; registry is additive documentation.
- Traceability — AGENTS.md claim-identity binding (item f) explicitly
  preserved.
- Reversibility — proposed step is a single new file; rollback is `git rm`.
- Recoverable state — nothing stateful touched.
- Appropriate escalation — `model-api-routing.md`'s vendor policy is
  flagged as a standing constraint, not silently overridden; any actual
  change to it would need the same doctrine-adoption path as any other
  policy change (Article II.2).
