# Radio Traffic Discipline 1.0

1. **Originating intent** — The Lieutenant's first live Radio Console test found excessive Bridge traffic, likely driven by scouts, breaking the listening experience.
2. **Verified starting state** — Every fresh agent decision was narrated as high-authority `watch` traffic, every intermediate waypoint was spoken by Bridge, and startup could queue four baseline reports. Live history contains repeated scout decisions in bursts.
3. **Objective / problem** — Restore useful silence and reserve speech for meaningful changes.
4. **Scope and exclusions** — Change Radio Console narration policy only. Do not alter FleetCore, captain decision cadence, NPR audio, diagnostics, or authoritative event storage.
5. **Constraints / authority** — Preserve watch events, fuel warnings, route completion, escort-mode changes, and visible diagnostics. Source and live files must stay synchronized.
6. **Acceptance criteria** — Startup emits one consolidated Bridge call plus exceptional fuel only; routine agent decisions produce at most one status summary per minute; intermediate waypoints do not speak; decision cursors still advance so suppressed traffic cannot replay later.
7. **Tests / rollback** — JavaScript syntax check, focused source assertions, source/live drift check, and live HTTPS marker verification. Roll back by reverting the implementation commit.
8. **Assigned actor** — Codex.
9. **Evidence and completion state** — Verified complete and recorded. Source and live JavaScript pass syntax validation; the drift checker reports synchronization; live HTTPS contains the one-minute routine-autonomy gate and silent-waypoint policy. The commit isolates only traffic-discipline hunks from concurrent audio-quality work.
