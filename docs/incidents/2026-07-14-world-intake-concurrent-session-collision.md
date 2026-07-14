# Incident: concurrent-session collision during Living World Intake V0.1

**Date:** 2026-07-14
**Severity:** No data lost, no production impact. Real workspace corruption
risk realized once (caught and reverted); temporary content divergence between
two branches, reconciled before the next commissioning run.

## Summary

Two independent `claude` CLI processes operated against the same shared,
non-isolated working directory (`~/dev/monad`) at overlapping times while
both were, in effect, working the same engineering order
(`docs/engineering-orders/living-world-intake-v0.1.md`). Neither process
had any signal that the other existed. One process (this one) made a live
edit that landed mid-write from the other, producing a duplicate-definition
bug that was caught and reverted before commit. Separately, and with no
edit conflict at all, the working directory's checked-out branch changed
underneath this session multiple times via plain `git checkout`, which is
the mechanism that actually caused the most consequential, silent damage:
`docs/commissioning-handoff.md`'s original, detailed content (written on
`agent/living-fleet-v0-1`) is entirely absent from the branch this session
ended up on (`agent/living-world-intake-v0-1`), so the other process
authored a thinner replacement from scratch, unaware a fuller version
existed one branch away.

## Timeline (reconstructed from `git reflog`, timestamps UTC)

This reflog spans more history than either agent session individually
performed — it reflects **every checkout and commit made against this one
working directory**, by at least two processes, interleaved:

| reflog entry | action |
|---|---|
| ... `f57aa5f` | `agent/living-fleet-v0-1` reaches its final state: "Document the /home/cgl/cmd.sh commissioning handoff protocol" (the full, detailed version of `docs/commissioning-handoff.md`) |
| `HEAD@{9}` | checkout `agent/living-fleet-v0-1` → **new branch** `agent/archive-legacy-files`, based at `f57aa5f` |
| `HEAD@{8}` | commit "Archive legacy prototypes and sprint briefs" (`c758db6`) on `agent/archive-legacy-files` — this is the archive-move this session observed as already-staged at conversation start |
| `HEAD@{7}`–`{6}` | checkout to `main`; fast-forward merge of `origin/main`, which already contained "Merge pull request #2 from aleuf05/agent/living-fleet-v0-1" (`654eebb`) — **but that PR was merged from an *earlier* point in `agent/living-fleet-v0-1`'s history, before `f57aa5f` existed locally**, so `f57aa5f` was never part of what got merged to `main` |
| `HEAD@{5}`–`{4}` | checkout back to `agent/archive-legacy-files`, then to a new branch `agent/memory-api-latency` |
| `HEAD@{3}` | commit "Keep memory API within latency budget" (`686bc91`) on `agent/memory-api-latency` |
| `HEAD@{2}` | checkout `agent/memory-api-latency` → **new branch** `agent/living-world-intake-v0-1`, based at `686bc91` (a descendant of the `main` fast-forward, *not* of `agent/living-fleet-v0-1`'s `f57aa5f`) |
| `HEAD@{1}` | commit "Build Living World Intake V0.1" (`c5228a2`) — the other session's integrated feature commit, including a **freshly-authored** `docs/commissioning-handoff.md` (git shows it as a new file on this branch, 36 lines, materially shorter than `agent/living-fleet-v0-1`'s version) |
| `HEAD@{0}` | commit "Record post-sprint system verification" (`0426f88`) — the other session committing this session's own report file, found sitting untracked in the shared working directory |

This session (mine) began reading the repository partway through this
sequence, on `agent/living-fleet-v0-1` per the conversation's initial
`gitStatus`, and later found itself on `agent/living-world-intake-v0-1`
without ever running a `git checkout` itself — the branch moved out from
under it.

## What actually collided

1. **Direct file-edit collision (caught).** At 03:02:40 this session added a
   `slug()` helper to `tools/world-intake/world_intake.py` via the `Edit`
   tool. The other session was writing to the same file in the same window
   (its own edits span roughly 02:59–03:02). The tool reported the file had
   "been modified on disk since last read"; re-reading showed two conflicting
   `slug()` definitions. Reverted immediately, before any test run or commit
   saw the broken state. No lasting effect.

2. **Silent branch substitution (not caught until forensic review).** This
   session never issued a `git checkout`. The working directory's checked-out
   branch nonetheless changed at least three times during the session's
   lifetime (per the reflog above), each time performed by whatever process
   was driving the other `claude` PID. This session had no way to detect
   "the ground moved" other than noticing inconsistent state under manual
   investigation — which is what actually surfaced this incident (a
   `git diff` showing `docs/commissioning-handoff.md` as a brand-new file
   contradicted this session's own earlier reading of that file's fuller
   content).

3. **Content divergence (subsequently reconciled).**
   `docs/commissioning-handoff.md` now exists in two materially different
   versions on two live branches:
   - `agent/living-fleet-v0-1` (`f57aa5f`): the original, with a numbered
     "what a real handoff script looks like" checklist and specific
     precedent entries (`/home/cgl/commissioning/living-fleet-v0.1-...`).
   - `agent/living-world-intake-v0-1` (`c5228a2`): a shorter, generic
     rewrite covering the same rules in less detail, with no precedent
     section, authored because the authoring session's branch genuinely
     never had the file (`git log --follow` on this branch shows exactly
     one commit for this path).

   Nothing was lost: `agent/living-fleet-v0-1` retained the original. During
   integration, the commander restored its missing operational detail and
   precedent into the mainline commissioning document before repinning the
   next sudo handoff.

## Root cause

**No workspace isolation between concurrently active agent sessions.** This
repo already has the tooling to avoid this — `git worktree` is in active use
elsewhere (`.claude/worktrees/scout-screen-mode`, a locked worktree on branch
`worktree-scout-screen-mode`) — but neither this session nor the other one
was given, or claimed, an isolated worktree. Both operated directly on the
single primary checkout at `~/dev/monad`, which is also the one Caddy serves
`web/` from live (see `docs/deployment.md`) and the one every systemd unit
in this repo points at by absolute path — so it isn't just a git problem,
it's the one shared filesystem location multiple independent things treat
as canonical simultaneously.

Contributing factor: nothing in `docs/engineering-orders/living-world-intake-v0.1.md`
or `docs/workflows/split-delegated-engineering.md` (as it existed before this
incident) said anything about what happens if the *same order* is picked up
by more than one top-level session, or required a workspace claim/lock before
a session starts checking out branches and committing.

## Status update (same day, later)

The commissioning-protocol divergence was reconciled and committed in
`b1966f4`; the integration findings were resolved in `df850f2`. Both changes
were merged to `main` through follow-up PRs. The live `/home/cgl/cmd.sh`
package must be repinned to the final clean integration commit before the
Lieutenant runs it; its dirty-tree and exact-HEAD guards correctly prevent a
stale package from commissioning moving source.

## Recommendation

See the "Known failure mode" section added to
`docs/workflows/split-delegated-engineering.md` for the durable rule. In
short: a session beginning delegated or commander work should get an
isolated `git worktree` (this repo's own `EnterWorktree` tooling / the
`isolation: "worktree"` Agent option already exist for exactly this), not
the shared primary checkout — and if it must use the shared checkout, it
should check for and refuse to proceed against evidence of another active
session (a running process against the same repo, an unexpected branch
change, uncommitted work not its own) rather than plowing ahead.
