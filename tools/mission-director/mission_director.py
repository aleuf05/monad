#!/usr/bin/env python3
"""Mission Director -- thin orchestration layer over FleetCore for a single
scripted mission (Quacken Transit 001). Consumes FleetCore's real events
only (vessel_events, snapshot positions) and never fabricates simulation
progress; the sim stays authoritative. This tool holds its own persisted
state machine (which phase the mission is in, evidence log, dwell timers)
but never mutates World state beyond the two real FleetCore commands it's
explicitly allowed to issue: spawn-passive-contact (the Rubber Ducky, once,
at mission start) and record-watch-event (marking real milestones on
FleetCore's own log, visible to every other instrument).

Per the tasking packet's ruling: no code churn outside this contract --
this tool never touches fleetcore/src/*, and issues no command beyond
those two.

State machine (see PACKET -- CLI -- MISSION DIRECTOR V1):

    MISSION_INITIALIZED
      -> mission start (operator action, spawns the Ducky)
    TRANSIT_UNDERWAY
      -> first real waypoint_reached event for the tracked vessel
    STRAIT_TRANSIT
      -> real route_completed event (final transit waypoint reached)
    APPROACH_QUACKEN
      -> RendezvousReached (Director-derived, from real position data:
         distance from the tracked vessel to the Ducky's fixed spawn
         position <= RENDEZVOUS_RADIUS_METERS)
    RENDEZVOUS_HOLD
      -> continuous dwell inside the radius for HOLD_DURATION_SECONDS
         (resolves the packet's open issue: an instantaneous touch isn't
         a hold; exiting the radius early resets the dwell timer to zero,
         it is not a stall by itself)
    MISSION_COMPLETE

Any active phase (everything except MISSION_COMPLETE/ABORTED/FAILED and
the halted MISSION_STALLED) can also go to:
    MISSION_STALLED   -- no relevant real-event progress *and* no real
                         vessel motion for STALL_TIMEOUT_SECONDS (a long
                         leg the vessel is still actively transiting is
                         not a stall). Not a failure; halts and
                         awaits operator review. `resume` always returns
                         to the exact phase it stalled from (never a
                         forced jump to a different phase -- that would
                         fabricate progress no real event produced), with
                         that phase's stall clock re-armed fresh.
    MISSION_ABORTED   -- explicit operator action (`abort`), from any
                         active phase, any time.
    MISSION_FAILED    -- invalid state detected (the tracked vessel or
                         the Ducky contact is missing from FleetCore's
                         own snapshot).
"""
import argparse
import json
import math
import os
import sys
import time
import urllib.error
import urllib.request

import report

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state")

MISSION_ID = "quacken-transit-001"
TRACKED_VESSEL_ID = "vessel.monad"
DUCKY_ID = "contact.rubber-ducky"
DUCKY_NAME = "Rubber Ducky"
DUCKY_CALLSIGN = "QUACKEN"
# Open water, well clear of every fleetcore/src/geography.rs land zone
# (all five cluster inside lat 24.1-27.75, lng 54.1-57.4 near the Strait of
# Hormuz) -- picked far enough east that spawn-passive-contact can never
# be rejected by the land check regardless of where MONAD currently is.
DUCKY_POSITION = {"lat": 24.80, "lng": 58.60}

RENDEZVOUS_RADIUS_METERS = 500.0
HOLD_DURATION_SECONDS = 30.0
STALL_TIMEOUT_SECONDS = 600.0
POLL_INTERVAL_SECONDS = 2.0
EARTH_RADIUS_METERS = 6371000.0

ACTIVE_PHASES = {
    "TRANSIT_UNDERWAY", "STRAIT_TRANSIT", "APPROACH_QUACKEN", "RENDEZVOUS_HOLD",
}
TERMINAL_PHASES = {"MISSION_COMPLETE", "MISSION_ABORTED", "MISSION_FAILED"}


def fleetcore_url(path):
    base = os.environ.get("FLEETCORE_URL", "http://localhost:4771")
    return f"{base.rstrip('/')}/{path.lstrip('/')}"


def get_snapshot():
    with urllib.request.urlopen(fleetcore_url("snapshot"), timeout=5) as resp:
        return json.loads(resp.read())


def post_command(command):
    body = json.dumps(command).encode("utf-8")
    req = urllib.request.Request(
        fleetcore_url("command"), data=body,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"error: command rejected ({exc.code}): {detail}")


def haversine_m(p1, p2):
    lat1, lat2 = math.radians(p1["lat"]), math.radians(p2["lat"])
    dlat = math.radians(p2["lat"] - p1["lat"])
    dlng = math.radians(p2["lng"] - p1["lng"])
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return 2 * EARTH_RADIUS_METERS * math.asin(math.sqrt(a))


def state_path(mission_id):
    return os.path.join(STATE_DIR, f"{mission_id}.json")


def load_state(mission_id):
    path = state_path(mission_id)
    if not os.path.isfile(path):
        raise SystemExit(f"error: no state for mission '{mission_id}' -- run `start` first")
    with open(path) as f:
        return json.load(f)


def save_state(state):
    os.makedirs(STATE_DIR, exist_ok=True)
    path = state_path(state["mission_id"])
    with open(path, "w") as f:
        json.dump(state, f, indent=2)
        f.write("\n")


def new_state(mission_id):
    now = time.time()
    return {
        "mission_id": mission_id,
        "phase": "MISSION_INITIALIZED",
        "phase_entered_at": now,
        "last_progress_at": now,
        "last_vessel_position": None,
        "stalled_from_phase": None,
        "processed_vessel_event_count": 0,
        "rendezvous_dwell_started_at": None,
        "evidence": [],
        "captures": [],
        "next_capture_id": 1,
        "outcome": None,
        "created_at": now,
        "updated_at": now,
    }


def record_evidence(state, kind, detail, snapshot=None):
    entry = {
        "kind": kind,
        "detail": detail,
        "phase": state["phase"],
        "at": time.time(),
    }
    if snapshot is not None:
        entry["tick"] = snapshot.get("tick")
        entry["sim_time"] = snapshot.get("sim_time")
    state["evidence"].append(entry)
    return entry


def request_capture(state, event, recommended_view, caption):
    capture = {
        "id": state["next_capture_id"],
        "event": event,
        "recommended_view": recommended_view,
        "caption": caption,
        "requested_at": time.time(),
        "phase": state["phase"],
        "attachment": None,
    }
    state["next_capture_id"] += 1
    state["captures"].append(capture)
    record_evidence(state, "capture_requested", f"{event}: {caption}")
    return capture


def transition(state, new_phase, reason, snapshot=None):
    old_phase = state["phase"]
    record_evidence(state, "phase_transition", f"{old_phase} -> {new_phase}: {reason}", snapshot)
    state["phase"] = new_phase
    state["phase_entered_at"] = time.time()
    state["last_progress_at"] = time.time()
    if new_phase != "RENDEZVOUS_HOLD":
        state["rendezvous_dwell_started_at"] = None


def cmd_start(args):
    if os.path.isfile(state_path(args.mission_id)):
        raise SystemExit(
            f"error: mission '{args.mission_id}' already has state -- "
            "delete tools/mission-director/state/<id>.json first if you really want to restart"
        )
    state = new_state(args.mission_id)
    snapshot = get_snapshot()

    ducky_exists = any(v["id"] == DUCKY_ID for v in snapshot["vessels"])
    if not ducky_exists:
        post_command({
            "type": "spawn-passive-contact",
            "id": DUCKY_ID, "name": DUCKY_NAME, "callsign": DUCKY_CALLSIGN,
            "position": DUCKY_POSITION, "course": 0.0, "speed_mps": 0.0,
        })
        record_evidence(state, "command", f"spawned {DUCKY_CALLSIGN} at {DUCKY_POSITION}", snapshot)
    else:
        record_evidence(state, "note", f"{DUCKY_CALLSIGN} already present, spawn skipped", snapshot)

    post_command({
        "type": "record-watch-event",
        "message": f"Mission Director: {args.mission_id} underway. Tracking {TRACKED_VESSEL_ID} toward {DUCKY_CALLSIGN}.",
    })
    snapshot = get_snapshot()
    state["processed_vessel_event_count"] = len(snapshot.get("vessel_events", []))
    transition(state, "TRANSIT_UNDERWAY", "mission start (operator action)", snapshot)
    request_capture(
        state, "mission_start", "fleetcore-live",
        f"{args.mission_id}: mission start, {DUCKY_CALLSIGN} on station at {DUCKY_POSITION}.",
    )
    save_state(state)
    report.publish(state, DUCKY_POSITION, snapshot)
    print(f"mission '{args.mission_id}' started -- phase TRANSIT_UNDERWAY")


def check_stall(state, snapshot):
    if state["phase"] not in ACTIVE_PHASES:
        return False
    elapsed = time.time() - state.get("last_progress_at", state["phase_entered_at"])
    if elapsed < STALL_TIMEOUT_SECONDS:
        return False
    state["stalled_from_phase"] = state["phase"]
    record_evidence(
        state, "stall",
        f"no progress in {state['phase']} for {elapsed:.0f}s (threshold {STALL_TIMEOUT_SECONDS:.0f}s)",
        snapshot,
    )
    state["phase"] = "MISSION_STALLED"
    return True


def check_invalid_state(state, snapshot):
    vessel_ids = {v["id"] for v in snapshot["vessels"]}
    missing = [vid for vid in (TRACKED_VESSEL_ID, DUCKY_ID) if vid not in vessel_ids]
    if missing:
        record_evidence(state, "invalid_state", f"missing from FleetCore snapshot: {missing}", snapshot)
        state["phase"] = "MISSION_FAILED"
        state["outcome"] = "failed"
        return True
    return False


def advance(state, snapshot):
    """One real-event-driven step of the state machine. Returns True if the
    phase changed (caller re-publishes the report when it does)."""
    phase_before = state["phase"]

    if check_invalid_state(state, snapshot):
        return state["phase"] != phase_before

    vessel_events = snapshot.get("vessel_events", [])
    new_events = vessel_events[state["processed_vessel_event_count"]:]
    state["processed_vessel_event_count"] = len(vessel_events)
    tracked_new = [e for e in new_events if e.get("vessel_id") == TRACKED_VESSEL_ID]

    # A single poll can contain more than one relevant event for the same
    # vessel -- e.g. after any gap in polling, or a large fast-forward --
    # so re-scan this same batch against the *current* phase after each
    # transition instead of only reacting to the first hit. Without this,
    # a route_completed landing in the same batch as the waypoint_reached
    # that triggered TRANSIT_UNDERWAY -> STRAIT_TRANSIT would get marked
    # "already processed" (processed_vessel_event_count already advanced
    # past it) without ever being evaluated against STRAIT_TRANSIT's own
    # check, silently losing a real transition.
    advanced = True
    while advanced:
        advanced = False
        if state["phase"] == "TRANSIT_UNDERWAY":
            reached = next((e for e in tracked_new if e["type"] == "waypoint_reached"), None)
            if reached:
                transition(state, "STRAIT_TRANSIT", f"waypoint_reached (leg {reached['remaining_leg_count']} remaining)", snapshot)
                advanced = True

        elif state["phase"] == "STRAIT_TRANSIT":
            completed = next((e for e in tracked_new if e["type"] == "route_completed"), None)
            if completed:
                transition(state, "APPROACH_QUACKEN", "route_completed (final transit waypoint reached)", snapshot)
                advanced = True
            else:
                reached = next((e for e in tracked_new if e["type"] == "waypoint_reached"), None)
                if reached:
                    record_evidence(state, "progress", f"waypoint_reached (leg {reached['remaining_leg_count']} remaining)", snapshot)

    if state["phase"] == "APPROACH_QUACKEN":
        vessel = next((v for v in snapshot["vessels"] if v["id"] == TRACKED_VESSEL_ID), None)
        if vessel is not None:
            distance = haversine_m(vessel["position"], DUCKY_POSITION)
            if distance <= RENDEZVOUS_RADIUS_METERS:
                transition(
                    state, "RENDEZVOUS_HOLD",
                    f"RendezvousReached (Director-derived: {distance:.0f}m <= {RENDEZVOUS_RADIUS_METERS:.0f}m radius)",
                    snapshot,
                )
                state["rendezvous_dwell_started_at"] = time.time()
                request_capture(
                    state, "rendezvous_reached", "fleetcore-live",
                    f"MONAD entered rendezvous radius with {DUCKY_CALLSIGN} at tick {snapshot.get('tick')}.",
                )

    elif state["phase"] == "RENDEZVOUS_HOLD":
        vessel = next((v for v in snapshot["vessels"] if v["id"] == TRACKED_VESSEL_ID), None)
        if vessel is not None:
            distance = haversine_m(vessel["position"], DUCKY_POSITION)
            if distance <= RENDEZVOUS_RADIUS_METERS:
                if state["rendezvous_dwell_started_at"] is None:
                    state["rendezvous_dwell_started_at"] = time.time()
                dwell = time.time() - state["rendezvous_dwell_started_at"]
                if dwell >= HOLD_DURATION_SECONDS:
                    transition(
                        state, "MISSION_COMPLETE",
                        f"hold criteria satisfied ({dwell:.0f}s continuous dwell inside radius)",
                        snapshot,
                    )
                    state["outcome"] = "success"
                    request_capture(
                        state, "mission_complete", "bridge-station-3.0",
                        f"{state['mission_id']}: rendezvous hold complete, mission success.",
                    )
                    post_command({
                        "type": "record-watch-event",
                        "message": f"Mission Director: {state['mission_id']} complete. Rendezvous hold satisfied.",
                    })
            else:
                # Left the radius before the hold duration elapsed -- this is
                # unmet progress, not a stall by itself (see module
                # docstring's resolution of the packet's open issue). Reset
                # the dwell timer; only STALL_TIMEOUT_SECONDS of this
                # repeating without ever completing escalates to a stall.
                if state["rendezvous_dwell_started_at"] is not None:
                    record_evidence(state, "note", f"left rendezvous radius ({distance:.0f}m), dwell timer reset", snapshot)
                state["rendezvous_dwell_started_at"] = None

    # A long leg between waypoints can legitimately take longer than
    # STALL_TIMEOUT_SECONDS in real time -- that's not a stall, the vessel
    # is just still underway. Real motion (a changed position, straight from
    # FleetCore's own snapshot) counts as progress just as much as a
    # discrete event does, so it re-arms the stall clock too.
    if state["phase"] in ACTIVE_PHASES:
        vessel = next((v for v in snapshot["vessels"] if v["id"] == TRACKED_VESSEL_ID), None)
        if vessel is not None and vessel["position"] != state.get("last_vessel_position"):
            state["last_vessel_position"] = vessel["position"]
            state["last_progress_at"] = time.time()

    if state["phase"] not in TERMINAL_PHASES and state["phase"] != "MISSION_STALLED":
        check_stall(state, snapshot)

    return state["phase"] != phase_before


def cmd_run(args):
    state = load_state(args.mission_id)
    if state["phase"] in TERMINAL_PHASES:
        print(f"mission '{args.mission_id}' already in terminal phase {state['phase']}, nothing to do")
        return

    if args.once:
        snapshot = get_snapshot()
        changed = advance(state, snapshot)
        state["updated_at"] = time.time()
        save_state(state)
        if changed:
            report.publish(state, DUCKY_POSITION, snapshot)
        print(f"phase: {state['phase']}" + (" (changed)" if changed else ""))
        return

    print(f"mission '{args.mission_id}': watching (Ctrl+C to stop) ...")
    try:
        while state["phase"] not in TERMINAL_PHASES and state["phase"] != "MISSION_STALLED":
            snapshot = get_snapshot()
            changed = advance(state, snapshot)
            state["updated_at"] = time.time()
            save_state(state)
            if changed:
                report.publish(state, DUCKY_POSITION, snapshot)
                print(f"  -> {state['phase']}")
            time.sleep(POLL_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("\nstopped (state saved, resume with `run` again)")
        return
    print(f"mission '{args.mission_id}' reached {state['phase']}")


def cmd_abort(args):
    state = load_state(args.mission_id)
    if state["phase"] in TERMINAL_PHASES:
        raise SystemExit(f"error: mission already in terminal phase {state['phase']}")
    snapshot = get_snapshot()
    record_evidence(state, "abort", args.reason or "no reason given", snapshot)
    state["phase"] = "MISSION_ABORTED"
    state["outcome"] = "aborted"
    save_state(state)
    report.publish(state, DUCKY_POSITION, snapshot)
    print(f"mission '{args.mission_id}' aborted: {args.reason or '(no reason given)'}")


def cmd_resume(args):
    state = load_state(args.mission_id)
    if state["phase"] != "MISSION_STALLED":
        raise SystemExit(f"error: mission is in {state['phase']}, not MISSION_STALLED -- nothing to resume")
    resumed_phase = state["stalled_from_phase"]
    if not resumed_phase:
        raise SystemExit("error: no recorded stalled_from_phase -- cannot resume safely")
    snapshot = get_snapshot()
    record_evidence(state, "resume", f"operator resumed into {resumed_phase}, stall clock re-armed", snapshot)
    state["phase"] = resumed_phase
    state["phase_entered_at"] = time.time()
    state["last_progress_at"] = time.time()
    state["stalled_from_phase"] = None
    save_state(state)
    report.publish(state, DUCKY_POSITION, snapshot)
    print(f"mission '{args.mission_id}' resumed -- phase {resumed_phase}, stall clock re-armed")


def cmd_request_capture(args):
    state = load_state(args.mission_id)
    capture = request_capture(state, "manual", args.view, args.caption)
    save_state(state)
    print(f"capture #{capture['id']} requested: {args.caption}")


def cmd_attach_capture(args):
    state = load_state(args.mission_id)
    capture = next((c for c in state["captures"] if c["id"] == args.capture_id), None)
    if capture is None:
        raise SystemExit(f"error: no capture #{args.capture_id} for mission '{args.mission_id}'")
    capture["attachment"] = args.path_or_url
    capture["attached_at"] = time.time()
    save_state(state)
    snapshot = get_snapshot()
    report.publish(state, DUCKY_POSITION, snapshot)
    print(f"capture #{args.capture_id} attached: {args.path_or_url}")


def cmd_status(args):
    state = load_state(args.mission_id)
    print(f"mission:  {state['mission_id']}")
    print(f"phase:    {state['phase']}")
    if state["stalled_from_phase"]:
        print(f"stalled from: {state['stalled_from_phase']}")
    print(f"outcome:  {state['outcome'] or '(in progress)'}")
    print(f"evidence: {len(state['evidence'])} entries")
    print(f"captures: {len(state['captures'])} requested, "
          f"{sum(1 for c in state['captures'] if c['attachment'])} attached")
    print()
    for entry in state["evidence"][-10:]:
        print(f"  [{entry['kind']}] {entry['detail']}")


def cmd_publish(args):
    state = load_state(args.mission_id)
    snapshot = get_snapshot()
    report.publish(state, DUCKY_POSITION, snapshot)
    print(f"published mission '{args.mission_id}' report")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--mission-id", default=MISSION_ID)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("start", help="spawn the Ducky, begin tracking, transition to TRANSIT_UNDERWAY")

    p_run = sub.add_parser("run", help="watch real FleetCore events and advance the state machine")
    p_run.add_argument("--once", action="store_true", help="single poll-and-check instead of a continuous loop")

    p_abort = sub.add_parser("abort", help="operator abort from any active phase")
    p_abort.add_argument("reason", nargs="?", default=None)

    sub.add_parser("resume", help="resume from MISSION_STALLED into the exact phase it stalled from")

    p_cap = sub.add_parser("request-capture", help="manually request a screenshot capture")
    p_cap.add_argument("--view", required=True, help="recommended instrument, e.g. fleetcore-live")
    p_cap.add_argument("--caption", required=True)

    p_attach = sub.add_parser("attach-capture", help="attach a real screenshot path/URL to a requested capture")
    p_attach.add_argument("capture_id", type=int)
    p_attach.add_argument("path_or_url")

    sub.add_parser("status", help="print current phase and recent evidence")
    sub.add_parser("publish", help="regenerate the JSON/Markdown/HTML report from current state")

    args = parser.parse_args()
    {
        "start": cmd_start,
        "run": cmd_run,
        "abort": cmd_abort,
        "resume": cmd_resume,
        "request-capture": cmd_request_capture,
        "attach-capture": cmd_attach_capture,
        "status": cmd_status,
        "publish": cmd_publish,
    }[args.command](args)


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    main()
