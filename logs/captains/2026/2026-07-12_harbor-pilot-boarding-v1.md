# Harbor Pilot Boarding v1 Watch Log

Date: 2026-07-12
Operator: Lt. cgl
Objective: enact `Harbor.md`, Captain T's mission packet for a multi-instrument, radio-gated "Harbor Pilot Boarding" scenario — Monad's proposed first flagship demonstration.

## Scope decision

The full packet asks for a lot in one mission: FleetCore-authoritative phase state, genuine proximity/radio-triggered progression, Radio Console voice integration, and a rendered boarding event. Building all of that faithfully means real Rust work in FleetCore (a phase/scenario state machine, at minimum) plus changes to Radio Console — both explicitly out of bounds for a single watch (no unilateral FleetCore `Command` additions, per this toy's own established constraint and the separate Command Center brief's Hard Rule; no changes to Radio Console, per that same brief's boundary list).

Built a v1 that is honest about the gap rather than pretending to close it: every *content* beat of the scenario (the pilot boat existing, moving, boarding, the flagship's real course change under "pilot control," the watch-log narrative) is a genuine FleetCore state change any connected instrument observes — but phase *sequencing* (which step comes next, gating on "acknowledge the pilot," "grant the conn") lives in this one browser tab's JavaScript, not in FleetCore itself. Documented plainly in `toys/fleetcore-control/README.md`'s new "Harbor Pilot Boarding" section rather than left implicit.

## Build

Added a stateful "Harbor Pilot Boarding" panel to `toys/fleetcore-control/` (not a new toy — this mission packet is squarely a scenario for the scenario-launcher that already exists):

- Six-click phase machine (`harbor` state object, `HARBOR_STEPS` in `app.js`) covering the packet's seven phases (phases 5–6, conn transfer and harbor transit, merged into one click since the packet has the pilot issue helm orders immediately after taking the conn).
- Phase 1 spawns a pilot boat and two harbor traffic contacts at a synthetic harbor point, routes the pilot boat toward the flagship.
- Phase 3 (Acknowledge) shows the pilot's hail text before the operator can advance, matching the packet's "communication is the trigger" requirement, then re-routes the pilot boat to the flagship's current position.
- Phase 5 (Grant the Conn) is the real centerpiece: a single `set-route` command targeting the **flagship's own vessel id** — a four-leg staged path toward the harbor point — with each leg's `record-watch-event` named after the packet's own helm orders ("Port five," "Dead slow ahead," "Midships," "Ease to starboard"). This is what makes "the pilot takes the helm" a real state change rather than a UI fiction: FleetCore's `set-route` command already works on any vessel id, including the flagship, so no new FleetCore capability was needed.
- Phase 6 records completion and routes the pilot boat back to the harbor point, departing.
- Reset only clears this toy's local phase tracker for a fresh run (new id suffix) — does not despawn anything, consistent with the toy's existing no-despawn limitation.

## Verification

Playwright against the real `fleetcore-serve` on this box, driving all six clicks in sequence:

- Confirmed the phase label and action-button text advance correctly through all seven phase labels, and the pilot's two hail lines display at the correct phases with the correct dynamically-generated callsign.
- After the full run, fetched a fresh `GET /snapshot` independently (not just reading UI state) and confirmed: flagship's `route` held the exact four staged waypoints and `status` had flipped to `"underway"`; the pilot boat and both harbor traffic contacts existed with the expected callsigns; all eight expected watch-log messages were present in the correct order with the exact narrative text, including all four named helm orders.
- Reset correctly returned the UI to "Not started" with a fresh id suffix ready for the next run.
- Zero console/page errors across the entire run.

## Acceptance criteria, checked against `Harbor.md`'s own list

- ✓ FleetCore drives all world state that this scenario touches (spawns, routes, watch events all persist server-side, observable by any connected instrument).
- ✓ Fleet Motion/Periscope would display the pilot boat's and flagship's real movement (not independently re-verified this watch — inherited from existing, already-verified live-mode behavior).
- ✓ Radio communication is mandatory to advance (the Acknowledge and Grant-the-Conn phases are gated behind an explicit operator action representing the radio response).
- ✓ Bridge state changes after "Pilot aboard" (a real `record-watch-event`, though see the gap below on where that's actually visible).
- ✓ Conn transfer visibly occurs (the flagship's own route and status genuinely change).
- ✗ Not automatic detection/proximity-triggered — manual click stands in, documented as a known simplification.
- ✗ Not replayable as a FleetCore-side sequence — this run's phase state lived in one browser tab.

## Known gap worth flagging

Bridge Station does not currently display FleetCore's `watch_events` at all — it derives its status rail from `MonadFleetState` (Fleet Motion's local canonical state), not from FleetCore's own watch log. `toys/fleetcore-live/` and `toys/fleetcore-control/` are the only two toys that surface `watch_events` today. So "Bridge reports: Harbor Pilot ETA 12 minutes" (Phase 1's watch event) is real and observable — just not from Bridge Station's own screen. Worth a follow-up if the mission packet's acceptance criteria are meant to be checked from Bridge Station specifically.

## Not done

- No FleetCore-side scenario/phase state machine (would need new `Command`/`World` support — a shared-core change, out of scope here).
- No Radio Console voice integration.
- No rendered boarding animation/event in Fleet Motion or Periscope.
- Not deployed to `web/` or `web-lan/` — local verification only. Ask before deploying, same gate as prior watches.

## Updated

- `toys/fleetcore-control/index.html`
- `toys/fleetcore-control/app.js`
- `toys/fleetcore-control/style.css`
- `toys/fleetcore-control/README.md`
