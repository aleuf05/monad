# Agent Registry

Generated: 2026-07-17T13:26:51.085887+00:00

Built from `docs/engineering-orders/packets/*.md`'s own self-declared `Assigned actor` / `Evidence and completion state` fields (Master Packet §13) -- **not** from git authorship, which cannot distinguish agents in this repo (every commit shares one local git identity regardless of which agent made it, confirmed by inspection). See `docs/architecture/agent-registry-v0.1.md` for the full design and what's deliberately not attempted here (cost tracking, tool-access enforcement, memory rules -- none of these have a real, non-fabricated data source yet).

**33 packets on record.**

## Claude

5 packet(s) — 2 complete, 0 in progress, 0 queued, 1 refused, 2 unknown status.

| Packet | Status | First recorded | Last touched |
|---|---|---|---|
| Radio Traffic Evaluation 0.1 | complete | 2026-07-16 | 2026-07-16 |
| Packet DOCTRINE-001 — Verification Command Dialect | unknown | 2026-07-15 | 2026-07-15 |
| Packet ENG1-REFUSED — Living Fleet deployment matrix cutover [REFUSED] | refused | 2026-07-15 | 2026-07-15 |
| Packet FC-LIVE-01 — fleetcore-live vessel-event cursor fix | complete | 2026-07-15 | 2026-07-15 |
| Packet LC-STATUS-01 — Living Captain status API install | unknown | 2026-07-15 | 2026-07-15 |

## Codex

27 packet(s) — 25 complete, 1 in progress, 0 queued, 0 refused, 1 unknown status.

| Packet | Status | First recorded | Last touched |
|---|---|---|---|
| Radio Editorial Gate 0.1 | complete | 2026-07-16 | 2026-07-17 |
| NPR Unchanged Snapshot No-Write 0.1 | complete | 2026-07-16 | 2026-07-16 |
| Rich Voice Studio 0.1 | in-progress | 2026-07-16 | 2026-07-16 |
| Voice Listening Evaluation 0.1 | complete | 2026-07-16 | 2026-07-16 |
| Rich Voice API 0.1 | complete | 2026-07-16 | 2026-07-16 |
| Rich Voice Core 0.1 | complete | 2026-07-16 | 2026-07-16 |
| Distinct Character Rehearsal 0.1 | complete | 2026-07-16 | 2026-07-16 |
| General Character Voice Model 0.1 | complete | 2026-07-16 | 2026-07-16 |
| Voice Performance Console 0.1 | complete | 2026-07-16 | 2026-07-16 |
| Voice Performance Layer 0.1 | complete | 2026-07-16 | 2026-07-16 |
| Living Captain Voice Enumeration 1.0 | complete | 2026-07-16 | 2026-07-16 |
| libfive Shape Foundry Console 1.0 | complete | 2026-07-16 | 2026-07-16 |
| Mission Radio Projection 1.0 | complete | 2026-07-16 | 2026-07-16 |
| Mission Review Projection 1.0 | unknown | 2026-07-16 | 2026-07-16 |
| Mission Artifact Registry 1.0 | complete | 2026-07-16 | 2026-07-16 |
| Scout Net Radio 1.0 | complete | 2026-07-16 | 2026-07-16 |
| Living Captain Radio Channel 1.0 | complete | 2026-07-16 | 2026-07-16 |
| libfive Headless Pipeline 1.0 | complete | 2026-07-16 | 2026-07-16 |
| Abstract Voice Engine 1.0 | complete | 2026-07-16 | 2026-07-16 |
| Kraken Inquiry Pilot 1.0 | complete | 2026-07-16 | 2026-07-16 |
| QUacken Mission Archive 1.0 | complete | 2026-07-16 | 2026-07-16 |
| Radio Traffic Discipline 1.0 | complete | 2026-07-16 | 2026-07-16 |
| Legend Pipeline 1.0 — Component One | complete | 2026-07-16 | 2026-07-16 |
| NPR Headline Reader 1.0 | complete | 2026-07-16 | 2026-07-16 |
| Radio Topic Selector 1.0 | complete | 2026-07-16 | 2026-07-16 |
| Radio Console Source Sync 1.0 | complete | 2026-07-16 | 2026-07-16 |
| Toy Drift Check 1.0 | complete | 2026-07-16 | 2026-07-16 |

## Lieutenant

10 packet(s) — 9 complete, 0 in progress, 0 queued, 0 refused, 1 unknown status.

| Packet | Status | First recorded | Last touched |
|---|---|---|---|
| Rich Voice Core 0.1 | complete | 2026-07-16 | 2026-07-16 |
| Distinct Character Rehearsal 0.1 | complete | 2026-07-16 | 2026-07-16 |
| General Character Voice Model 0.1 | complete | 2026-07-16 | 2026-07-16 |
| Voice Performance Console 0.1 | complete | 2026-07-16 | 2026-07-16 |
| Voice Performance Layer 0.1 | complete | 2026-07-16 | 2026-07-16 |
| libfive Shape Foundry Console 1.0 | complete | 2026-07-16 | 2026-07-16 |
| libfive Headless Pipeline 1.0 | complete | 2026-07-16 | 2026-07-16 |
| Abstract Voice Engine 1.0 | complete | 2026-07-16 | 2026-07-16 |
| Kraken Inquiry Pilot 1.0 | complete | 2026-07-16 | 2026-07-16 |
| Packet LC-STATUS-01 — Living Captain status API install | unknown | 2026-07-15 | 2026-07-15 |

## unspecified

1 packet(s) — 0 complete, 0 in progress, 0 queued, 0 refused, 1 unknown status.

| Packet | Status | First recorded | Last touched |
|---|---|---|---|
| Architecture Engine 1.0 — Assignment One: System Inventory | unknown | 2026-07-16 | 2026-07-16 |

## What this registry does not cover

- **Cost/spend per agent.** No cross-system ledger exists (see `docs/reports/2026-07-15-feature-matrix.md`'s `CT-01` row, still true). The one real spend ledger in this repo, `data/voice-engine/voice.sqlite3`'s `spend` table, is scoped to voice generation specifically, not per-agent, and empty at last check.
- **Enforced tool-access / authority envelopes.** Packets document scope and exclusions in prose (e.g. "Bot 1 owns radio-console files"), which humans and agents are expected to honor -- there's no runtime mechanism that actually prevents a violation.
- **Memory rules.** Doesn't apply the way it does to in-fiction Living Fleet captains; not attempted here.
- **Work-queue-only tasks** (`docs/engineering-orders/queue.md`) that never became a full packet -- by design, per `packets/README.md`'s own distinction between the two ("synthesis, verification, or documentation with no runtime/repository-state change" doesn't need a packet).
