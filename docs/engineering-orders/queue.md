# Shared engineering task queue

Protocol: see [`AGENTS.md`](../../AGENTS.md) at the repo root. Non-privileged,
git-only tasks only — nothing requiring `sudo` (that stays in `cmd.sh` /
`commissioning-handoff.md`).

## HUMAN-01 — Rule on issue #16 vs. CLAUDE.md contradiction

- Status: blocked-on-human
- Source: `GA-01` finding, `docs/reports/2026-07-15-phase1-sweep-and-corrections.md`
- What's needed: a ruling on which document currently governs --
  GitHub issue #16 (still OPEN, self-declared release blocker for
  FleetCore command auth) or `CLAUDE.md`'s current stated policy
  ("security hardening is not the priority here"). `monad-slice-g` has
  real unmerged work toward #16; nothing proceeds on it until this is
  ruled on.
- Claimed by: — (Admiral's decision only)
- Evidence: —

## HUMAN-02 — Authorize or decline worktree archival

- Status: blocked-on-human
- Source: `GA-01` finding
- What's needed: explicit sign-off to archive/remove
  `monad-issue17-slice-a`, `monad-issue18-slice-b`,
  `monad-history-integration` -- confirmed safe (issues #17/#18 closed,
  superseded by the bounded-retention approach that shipped to main, no
  open PRs), but removal was deliberately left for authorization, not
  done unilaterally.
- Claimed by: — (Lieutenant's call)
- Evidence: —

## HUMAN-03 — Restore access to scout-screen-mode worktree

- Status: blocked-on-human
- Source: `GA-01` finding
- What's needed: someone with host permissions to resolve the "dubious
  ownership" git error on `.claude/worktrees/scout-screen-mode`, or
  confirm whether the locked worktree (`worktree-scout-screen-mode`) is
  still active work or safe to release. No agent this session could
  inspect it.
- Claimed by: — (needs host-level access)
- Evidence: —

## HUMAN-04 — Adopt or reject Doctrine 001

- Status: blocked-on-human
- Source: `docs/doctrine/001-verification-command-dialect.md`
- What's needed: a decision on Status -- currently "Proposed," already
  load-bearing in practice (it's what the ENG-1 refusal was reasoned
  from), but never formally adopted per Master Packet §15's
  human-approval requirement.
- Claimed by: — (Admiral's decision only)
- Evidence: —

