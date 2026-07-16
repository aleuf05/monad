# Engineering Order: Watch Officer V0.1

Priority: Medium

Scope: Minimum spine only — observe, log, publish. No command authority, no
canon mutation, no persistent identity.

Doctrine: Watchman watches infrastructure (disk, Qdrant, systemd units).
Watch Officer watches the fleet and narrative layer instead — vessel state,
World Intake's review backlog, Mission Bus's projections — and reports what
it sees. It does not decide anything and does not act on anything.

Source: `docs/reports/2026-07-15-feature-matrix.md`'s `WO-01` row (Master
Packet §10), confirmed absent — "the only 'Watch Officer' occurrence anywhere
is a bare role-name string in `world_intake.py`'s `assign_role` check." No
separate charter section for §10 exists in this repo; this document is the
working design, written against that one-line requirement plus the "read-only
observer agent" framing already present in the Feature Matrix itself.

## Why this isn't Living Captain or Watchman

Three read-only observers can look redundant on the surface, so the
boundary is explicit:

- **Watchman** (`watchman.py`) — infrastructure health. Disk, Qdrant,
  systemd process/endpoint state for the 5 backend services. Nothing about
  the fleet or the narrative.
- **Living Captain** (`tools/living-captain/`) — a persistent, *identity-bearing*
  command presence. Survives restart with continuity of self. Has (bounded)
  action authority in later versions. About being someone, not just reporting.
- **Watch Officer** (this order) — no persistent identity, no restart-continuity
  requirement, no action authority ever. A stateless poll-and-report loop over
  fleet/narrative signals: is the vessel roster doing anything unusual, is
  World Intake's review queue backing up, is the last Mission Bus projection
  stale or flagging pending reviews. Closer to Watchman's shape than Living
  Captain's, just watching a different layer.

## V0.1 decomposition

### 1. Observation sources (read-only, no write path to any of them)

- FleetCore: `GET /snapshot` (`fleetcore-serve`, already public/unauthenticated
  for reads) — vessel count, vessels grouped by status, flagship status,
  clock state.
- World Intake: `GET /proposals?status=pending` (`world-intake.service`) —
  pending count, oldest pending proposal's age (from each proposal's
  `provenance.source_timestamp`).
- Mission Bus: `web/data/mission-ops.json` / `web/data/mission-reviews.json`
  (whatever `tools/mission-bus/mission_bus.py`'s projections last wrote —
  Watch Officer does not trigger a re-projection itself, same as Bridge
  Station 3.0's Mission Record rail).

### 2. Notes / flagging

A pending-proposal backlog past `MONAD_INTAKE_BACKLOG_WARN_COUNT` (default
10) or `MONAD_INTAKE_BACKLOG_WARN_AGE_HOURS` (default 24h) gets an explicit
note. Any unreachable source gets its own note rather than silently omitting
that section. No note at all only when literally nothing was flagged.

### 3. Record

Append-only JSONL log, same shape/precedent as Watchman's:
`logs/agents/watch-officer/YYYY/YYYY-MM-DD_watch.jsonl`, one JSON object per
observation.

### 4. Public surface

`web/data/watch-officer-status.json`, written every observation — the
reduced public-safe summary (no raw proposal content, just counts/ages/notes).
`toys/watch-officer/` is a small static page (no build step, no backend of
its own) that fetches and renders it, linked from the homepage's
"Autonomous Fleet" section. Per this project's own "if the Lt. can't see it,
it doesn't exist" policy — an invisible backend-only observer would not
satisfy this order even if the Python were perfect.

### 5. Refresh cadence

No systemd unit installed by this order (that's privileged, the Lieutenant's
domain). A non-privileged user crontab entry runs `watch_officer.py --once`
every 10 minutes — same precedent as `tools/npr-headlines/fetch.py`'s
existing crontab entry (`crontab -l`, no `sudo`, documented in
`docs/deployment.md`). A privileged systemd unit can replace it later the
same way `scripts/npr-headlines-fetch.service`/`.timer` is staged to replace
NPR's cron entry once someone with `sudo` installs it.

## Deferred (not in V0.1)

- Any action/command authority. Watch Officer never becomes a write path.
- Persistent identity or memory across restarts — every observation is
  independent; there is no "Watch Officer" character with continuity.
- Feeding Radio Console's existing "Watch Officer" speaker label (currently
  just narrates raw watch_events) with real commentary from this tool.
  Radio Console's voice wiring is active, fast-moving work by another agent
  as of this order; wiring the two together is a natural follow-up once that
  settles, not part of this scope.
- Alerting/notification (email, Slack, etc.) on flagged backlogs — the badge
  is passive, someone has to look at it.

## Done evidence

`watch_officer.py --once` run against the real live `fleetcore-serve` and
`world-intake.service` on this host (not fixtures): real vessel counts,
real World Intake backlog (39 pending, oldest 66.5h old at time of writing —
a genuine finding this tool surfaced for the first time), real Mission Bus
projection data. Graceful degradation verified by pointing both HTTP sources
at an unreachable port and confirming each failure produces its own note
rather than a crash or a silently-omitted section. Public page verified live
at `https://cameronlampley.com/toys/watch-officer/`.
