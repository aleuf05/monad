# Shared engineering task queue

Protocol: see [`AGENTS.md`](../../AGENTS.md) at the repo root. Non-privileged,
git-only tasks only — nothing requiring `sudo` (that stays in `cmd.sh` /
`commissioning-handoff.md`).

## HUMAN-01 — Rule on issue #16 vs. CLAUDE.md contradiction

- Status: resolved 2026-07-15
- Source: `GA-01` finding, `docs/reports/2026-07-15-phase1-sweep-and-corrections.md`
- Resolution: `docs/deployment.md` governs. Issue #16 remains a real
  hardening concern, but it does not block working-feature delivery in
  this repo. Security hardening stays deferred unless a later directive
  explicitly reclassifies it as a release gate.
- Claimed by: claude
- Evidence: `docs/deployment.md`, `docs/reports/2026-07-15-feature-matrix.md`

## HUMAN-02 — Authorize or decline worktree archival

- Status: resolved 2026-07-15
- Source: `GA-01` finding
- Resolution: archive/remove authorized and executed for
  `monad-issue17-slice-a`, `monad-issue18-slice-b`, and
  `monad-history-integration`.
- Claimed by: claude
- Evidence: filesystem removal of the three directories

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

- Status: resolved 2026-07-15
- Source: `docs/doctrine/001-verification-command-dialect.md`
- Resolution: adopted.
- Claimed by: claude
- Evidence: `docs/doctrine/001-verification-command-dialect.md`
