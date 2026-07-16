# Shared engineering task queue

Protocol: see [`AGENTS.md`](../../AGENTS.md) at the repo root. Non-privileged,
git-only tasks only — nothing requiring `sudo` (that stays in `cmd.sh` /
`commissioning-handoff.md`).

## MISSIONBUS-01 — Generalize Mission Bus beyond the single hardcoded Kraken mission

- Status: claimed:claude@2026-07-16T20:55:00Z
- Source: Lieutenant request, 2026-07-16, following up on the GLUE-01
  through GLUE-07 design chain and the shipped Kraken Inquiry Pilot.
- Objective: `tools/mission-bus/mission_bus.py` hardcodes `MID` and `CID`
  as module-level constants for the one Kraken pilot mission. Generalize
  `create`/`execute`/`review`/`transition`/`project` to accept a mission
  ID, objective, and correlation ID as parameters instead, so a second
  mission can exist without a second hardcoded copy of this file. This is
  the blocking dependency for every other component adapter GLUE-03
  designed (Cognition Graph export, Mission Director import, Legend
  Pipeline wrap, etc.) -- none of them can land without a Mission Bus
  that supports more than one mission.
- Scope: `tools/mission-bus/mission_bus.py` and its tests only. Preserve
  the existing Kraken pilot's exact behavior and CLI surface (running it
  with no new arguments must behave identically to today). No new
  component adapters in this pass -- that's follow-up work once this
  lands.
- Exclusions: no change to the Mission Record's SQLite schema (GLUE-02's
  schema already supports multiple `mission_id` values; this is a Python
  API/CLI generalization, not a storage change). No FleetCore changes.
- Done evidence: existing Kraken pilot tests still pass unmodified; a new
  test creates and completes a second, differently-IDed mission
  independently of the Kraken one; CLI accepts `--mission-id`/`--objective`
  flags, defaulting to the Kraken pilot's values when omitted.
- Claimed by: claude

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
