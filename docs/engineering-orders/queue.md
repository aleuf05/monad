# Shared engineering task queue

Protocol: see [`AGENTS.md`](../../AGENTS.md) at the repo root. Non-privileged,
git-only tasks only — nothing requiring `sudo` (that stays in `cmd.sh` /
`commissioning-handoff.md`).

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

## HEART-01 — Provision live model-provider credentials for Track A

- Status: blocked-on-human
- Source: Heart of Monad Implementation Packet (2026-07-16), Track A
  acceptance criteria -- "Pilot only needs two adapters wired live."
- What's needed: real API credentials for at least two of
  OpenAI/Anthropic/Google (a local provider needs none) so Track A's
  model provider adapters (`providers/openai.rs` etc.) can make real
  calls, not stubs, for the pilot mission. Admiral noted the Lieutenant
  may need to help obtain these.
- Claimed by: — (needs Lieutenant/Admiral to provision)
- Evidence: —
- Note: does not block Track B (Command Console / Command Architecture
  / FleetCore reader / Mission Record) or Phase 0 (shared types) --
  Track B's own acceptance criteria explicitly allows a stub graph in
  place of a finished Track A.
