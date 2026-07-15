# Radio Console v1 + FleetCore Event Model Upgrade

**Status:** Design Required — not started
**Source:** Admiral's technical packet (Radio Console v1 decision-layer spec) + this session's verification that its assumed event surface does not exist in FleetCore today

## Governing principle (unchanged from the original spec)

> Do not generate chatter. Simulate the conditions under which someone would decide to speak.

## Why this is one job, not two

The spec's System 1 (Priority Queue) scores every candidate transmission against 8 assumed event categories. Checked against `fleetcore/src/vessel.rs`'s real `VesselEvent` enum: **only 4 exist** (`WaypointReached`, `RouteReplaced`, `RouteCompleted`, `Holding`), plus `WatchEvent` (free-text, human-recorded, rare). None of `course change`, `speed change`, `contact detected`, `service degraded`, `alarm raised`, `alarm cleared` exist as real FleetCore events. Building the radio's decision layer without resolving this first means building the load-bearing piece on a surface that isn't there — so the FleetCore side is Phase A, not a separate later project.

---

## Phase A — FleetCore event model upgrade (Rust, `fleetcore/src/vessel.rs` + `world.rs`)

Verified against the current codebase, not assumed:

| Spec's assumed event | Real FleetCore mapping | Verdict |
|---|---|---|
| arrival | `RouteCompleted` (already exists) | **No change needed** |
| command message | `WatchEvent` (already exists, human-recorded) | **No change needed** |
| course change | No equivalent. `advance_vessel` in `world.rs` updates heading but never emits an event on change. | **New variant, addable** — instrument the same spot `WaypointReached`/`RouteCompleted` are emitted from, threshold-gated (don't fire on every tick's floating-point drift) |
| speed change | No equivalent, same location as course change. | **New variant, addable**, same pattern |
| contact detected | No equivalent. Contacts are spawned via the `spawn-passive-contact` *command*, not represented as a detection *event*. | **New variant, addable** — emit once when a contact enters a vessel's passive-detection range, reusing whatever proximity check already backs `passive_contacts()` (seen in `agent.rs`) |
| service degraded | **No FleetCore concept of vessel/service health exists at all.** Not a missing event — a missing concept. | **Deferred, out of scope for this pass** — needs its own design decision (what does "degraded" mean for a vessel or for `fleetcore-serve` itself?), not a quick addition |
| alarm raised / cleared | Same as above — no alarm concept exists anywhere in `World`/`Vessel`. | **Deferred, out of scope** |

**Phase A acceptance criteria:**
- `CourseChanged` and `SpeedChanged` variants added to `VesselEvent`, following the exact pattern of the existing four (mutually exclusive per tick per vessel, `event_seq`-cursored, retention-bounded — same discipline as issue #6's fix)
- `ContactDetected` variant added, emitted once per contact-enters-range, not per tick
- Rust tests added covering all three new variants (threshold-gating for course/speed so it doesn't fire on floating-point noise; contact detection firing exactly once, not per tick while in range)
- `service degraded` / `alarm raised` / `alarm cleared` explicitly **not** built this pass — tracked as a follow-on design question, not silently dropped

**What this does NOT touch:** `EscortPosture` (verified current variants: `HoldStation`, `AdvanceScreen`, `WidenFlank`, `CoverRear`, `InvestigateContact`, `RecoverFormation`, `EmergencySeparation` — no `orbit`/`follow`/`intercept`/`return`). That's Section 6's separate, already-logged gap (`EP-01`) — richer autonomous behavior is what would make vessels generate these events more often, but it's not required for the event *types* to exist. Sequencing note: Phase A gives the radio real event types to react to; it doesn't fix event *frequency* (still gated by how often FleetCore or Mission Director actually moves vessels) — that's the `EP-01` follow-on, not this job.

---

## Phase B — Radio Console v1 (JS, `toys/radio-console/`), against the real (post-Phase-A) event vocabulary

Five systems, dependency order per the original spec, remapped to the 7 real event types (4 existing + 3 new from Phase A) instead of the assumed 8:

1. **Priority Queue + Interruption Rules** — score each real event (`WaypointReached`, `RouteReplaced`, `RouteCompleted`, `Holding`, `WatchEvent`, `CourseChanged`, `SpeedChanged`, `ContactDetected`) on urgency/relevance/source authority/freshness/interruption permission/expiry. Build and tune first; nothing else works without it.
2. **Station Knowledge Scoping** — per-station filter predicate over the same 7-8 event types (e.g. a lookout-equivalent station sees `ContactDetected` before others; not every station needs every event type).
3. **Request → Acknowledge → Response Threading** — `pending → acked → completed / timeout → escalated` state machine per exchange.
4. **Channel Pressure (single scalar)** — derived from real FleetCore event rate (now richer post-Phase-A) + unacknowledged-request count. Drives line length, suppression threshold, interruption odds — one number, no parallel mood system.
5. **Short-Term Transmission Memory** — ring buffer, last N transmissions per station, enables "no change since last report."

**Minimum v1 UX (unchanged from spec):** one status line —
```
QUIET WATCH · 3 ACTIVE STATIONS · 1 PENDING REQUEST · TRAFFIC LOW
```
Full dashboard is v2, after the state underneath is verified correct.

**Phase B acceptance test (unchanged from spec):** the console goes silent when nothing matters, interrupts itself when something does, and can say "no change since last report" — all three emergent from the five systems, none hardcoded per-scenario.

**Explicitly deferred/cut (unchanged from spec):** delayed/batched/missed reactions, station "character," escalation/recovery arc, uncertainty vocabulary — all derived from the five systems above once built, not new machinery. Full station-relationship graph cut; collapse into jurisdiction/authority fields the queue already needs.

---

## Sequencing

Phase A must land and be tested before Phase B's System 1 is built against it — building the priority queue against events that don't exist yet would just recreate the exact mismatch this doc exists to prevent. Phase A is a FleetCore change (Rust, `fleetcore/`); Phase B is a Radio Console change (JS, `toys/radio-console/`) — different codebases, same job, sequenced, not parallel.

## Explicitly not decided by this doc

- Whether `service degraded` / `alarm raised` / `alarm cleared` ever get built, and what they'd even mean — flagged, not resolved.
- Whether Section 6's missing patrol behaviors (`EP-01`) get built alongside this to increase real event frequency, or left for later.
