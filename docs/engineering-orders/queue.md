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

## HUMAN-05 — Wire a live Anthropic key into The Cognition Graph

- Status: resolved 2026-07-16
- Source: `web/toys/cognition-graph/index.html`, shipped 2026-07-16.
- Resolution: no code change needed. Added a "Live Mode" panel on the
  page itself where the Lieutenant pastes his own Anthropic API key;
  it's saved to that browser's `localStorage` only (never written into
  the page's source, never touches the repo or any server), and
  `callModel()` reads it at call time. No key saved => simulated mode
  (unchanged mock behavior). This sidesteps the original concern (a
  hardcoded key visible to any visitor) entirely — each visitor
  supplies their own key, kept only in their own browser.
- Claimed by: claude
- Evidence: `web/toys/cognition-graph/index.html` (`#modeBanner`,
  `.key-panel`, `getStoredKey`/`setStoredKey`/`isLive`)
