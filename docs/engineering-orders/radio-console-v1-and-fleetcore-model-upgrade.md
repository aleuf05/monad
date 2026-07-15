# Radio Console v1 — Full Feature Upgrade (FleetCore + Radio Console, one job)

**Status:** In progress — single unified build, no phase gates
**Source:** Admiral's technical packet (Radio Console v1 decision-layer spec) + this session's verification that its assumed event surface does not exist in FleetCore today

## Governing principle (unchanged from the original spec)

> Do not generate chatter. Simulate the conditions under which someone would decide to speak.

## Scope

One feature, spanning two codebases because the data has to exist before the decision layer can score it — not a phase gate, just the order code has to be written in. `fleetcore/` (Rust) gains the event types the decision layer needs; `toys/radio-console/` (JS) gains the 5-system decision layer that reacts to them. Built and shipped together.

## FleetCore event model — verified against the real codebase, not assumed

The spec's Priority Queue scores 8 assumed event categories. Checked against `fleetcore/src/vessel.rs`'s real `VesselEvent` enum: only 4 existed before this feature (`WaypointReached`, `RouteReplaced`, `RouteCompleted`, `Holding`), plus `WatchEvent` (free-text, human-recorded, rare).

| Spec's assumed event | Real FleetCore mapping |
|---|---|
| arrival | `RouteCompleted` (pre-existing) |
| command message | `WatchEvent` (pre-existing, human-recorded) |
| course change | **Not built.** Checked: `vessel.course` is only ever assigned outside continuous motion at reset-fleet's initial-conditions (`world.rs` ~line 740). Every other write is the per-tick bearing-to-target recalculation the codebase's own doc comment already warns against turning into an event ("would spam constantly"). No safe, meaningful trigger exists. |
| speed change | **Not built.** Same finding — `vessel.speed_mps` is only ever set at reset-fleet; no "set speed" command exists anywhere. Tying an event to reset-fleet would be a fleet-reset event, not a speed-change event. |
| contact detected | **New:** `ContactDetected`, fires once on entering passive-detection range, reusing the proximity check behind `passive_contacts()` |
| service degraded | **Not built.** No FleetCore concept of vessel/service health exists at all — a missing concept, not a missing event. Flagged for a separate design decision. |
| alarm raised / cleared | **Not built.** Same reason as above. |

**Net new vocabulary: 6 events, not 8** — `WaypointReached`, `RouteReplaced`, `RouteCompleted`, `Holding`, `WatchEvent` (5 pre-existing) + `ContactDetected` (1 new). Course/speed-change cut for a verified reason, not dropped quietly.

**What this does NOT touch:** `EscortPosture`'s missing `orbit`/`follow`/`intercept`/`return` variants (`EP-01`, already logged separately) — richer autonomous behavior increases how *often* these events fire, not whether the event *types* exist. Separate, already-tracked gap; not required for this feature to work, just for it to have more to say.

## Radio Console v1 — five systems, against the real event vocabulary (7 types: 4 pre-existing + 3 new)

1. **Priority Queue + Interruption Rules** — scores every candidate transmission (from `WaypointReached`, `RouteReplaced`, `RouteCompleted`, `Holding`, `WatchEvent`, `CourseChanged`, `SpeedChanged`, `ContactDetected`) on urgency/relevance/source authority/freshness/interruption permission/expiry.
2. **Station Knowledge Scoping** — per-station filter predicate over the event stream (e.g. lookout-equivalent station sees `ContactDetected` before others).
3. **Request → Acknowledge → Response Threading** — `pending → acked → completed / timeout → escalated` per exchange.
4. **Channel Pressure (single scalar)** — derived from real FleetCore event rate + unacknowledged-request count. Drives line length, suppression threshold, interruption odds. One number, no parallel mood system.
5. **Short-Term Transmission Memory** — ring buffer, last N transmissions per station, enables "no change since last report."

**Minimum v1 UX:**
```
QUIET WATCH · 3 ACTIVE STATIONS · 1 PENDING REQUEST · TRAFFIC LOW
```
Full dashboard is v2.

**Acceptance test:** the console goes silent when nothing matters, interrupts itself when something does, and can say "no change since last report" — all three emergent from the five systems, none hardcoded per-scenario.

**Deferred (derived from the five systems once built, not new machinery):** delayed/batched/missed reactions, station "character," escalation/recovery arc, uncertainty vocabulary. **Cut:** full station-relationship graph — collapsed into jurisdiction/authority fields the queue already needs.

## Explicitly not decided by this doc

- Whether `service degraded` / `alarm raised` / `alarm cleared` ever get built, and what they'd even mean.
- Whether `EP-01`'s missing patrol behaviors get built alongside this to increase real event frequency.
