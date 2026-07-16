#!/usr/bin/env python3
"""Watch Officer -- a read-only observer over fleet/narrative state.

Not infrastructure health (that's watchman.py: disk, Qdrant, systemd units).
Watch Officer observes the *fleet* and *narrative* layer instead: FleetCore's
live vessel snapshot, World Intake's review backlog, and Mission Bus's
projections. It has no command authority and never mutates canon -- same
posture as Living Captain's "sight" adapters (tools/living-captain/sight.py),
just watching a different set of things and reporting them publicly.

See docs/engineering-orders/watch-officer-v0.1.md for scope.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
import time
import urllib.error
import urllib.request


HEARTBEAT_SECONDS = 600
HTTP_TIMEOUT_SECONDS = 5

FLEETCORE_SNAPSHOT_URL = os.environ.get(
    "MONAD_FLEETCORE_SNAPSHOT_URL", "http://127.0.0.1:4771/snapshot"
)
WORLD_INTAKE_PENDING_URL = os.environ.get(
    "MONAD_WORLD_INTAKE_PENDING_URL", "http://127.0.0.1:4773/proposals?status=pending"
)
INTAKE_BACKLOG_WARN_COUNT = int(os.environ.get("MONAD_INTAKE_BACKLOG_WARN_COUNT", "10"))
INTAKE_BACKLOG_WARN_AGE_HOURS = float(os.environ.get("MONAD_INTAKE_BACKLOG_WARN_AGE_HOURS", "24"))

MISSION_OPS_PATH = os.path.join("web", "data", "mission-ops.json")
MISSION_REVIEWS_PATH = os.path.join("web", "data", "mission-reviews.json")

LOG_DIR_NAME = os.path.join("logs", "agents", "watch-officer")
PUBLIC_STATUS_PATH = os.path.join("web", "data", "watch-officer-status.json")


def repo_root():
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(os.path.dirname(here))


def timestamp_utc():
    return datetime.datetime.now(datetime.timezone.utc)


def _http_get_json(url, timeout=HTTP_TIMEOUT_SECONDS):
    request = urllib.request.Request(url, headers={"User-Agent": "monad-watch-officer/1"}, method="GET")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def observe_fleetcore():
    try:
        snapshot = _http_get_json(FLEETCORE_SNAPSHOT_URL)
        vessels = snapshot.get("vessels", [])
        by_status = {}
        for vessel in vessels:
            status = vessel.get("status", "unknown")
            by_status[status] = by_status.get(status, 0) + 1
        flagship = next((v for v in vessels if v.get("kind") == "flagship"), None)
        return {
            "state": "observed",
            "vessel_count": len(vessels),
            "vessels_by_status": by_status,
            "flagship_status": flagship.get("status") if flagship else None,
            "clock_state": snapshot.get("clock_state"),
            "tick": snapshot.get("tick"),
            "error": None,
        }
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError) as error:
        return {
            "state": "unreachable",
            "vessel_count": None,
            "vessels_by_status": {},
            "flagship_status": None,
            "clock_state": None,
            "tick": None,
            "error": str(error),
        }


def observe_world_intake():
    try:
        payload = _http_get_json(WORLD_INTAKE_PENDING_URL)
        proposals = payload.get("proposals", [])
        oldest_age_hours = None
        if proposals:
            now = time.time()
            oldest_seconds = None
            for proposal in proposals:
                raw_ts = (proposal.get("provenance") or {}).get("source_timestamp")
                if not raw_ts:
                    continue
                try:
                    parsed = datetime.datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
                except ValueError:
                    continue
                age = now - parsed.timestamp()
                if oldest_seconds is None or age > oldest_seconds:
                    oldest_seconds = age
            if oldest_seconds is not None:
                oldest_age_hours = round(oldest_seconds / 3600, 1)
        return {
            "state": "observed",
            "pending_count": len(proposals),
            "oldest_pending_age_hours": oldest_age_hours,
            "error": None,
        }
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError) as error:
        return {
            "state": "unreachable",
            "pending_count": None,
            "oldest_pending_age_hours": None,
            "error": str(error),
        }


def observe_mission_bus(root):
    ops_path = os.path.join(root, MISSION_OPS_PATH)
    reviews_path = os.path.join(root, MISSION_REVIEWS_PATH)
    result = {
        "state": "unavailable",
        "mission_id": None,
        "mission_status": None,
        "pending_reviews": None,
        "error": None,
    }
    try:
        with open(ops_path, "r", encoding="utf-8") as stream:
            mission = json.load(stream)
        result["mission_id"] = mission["mission"]["mission_id"]
        result["mission_status"] = mission["mission"]["status"]
        result["state"] = "observed"
    except (OSError, ValueError, KeyError) as error:
        result["error"] = f"mission-ops: {error}"

    try:
        with open(reviews_path, "r", encoding="utf-8") as stream:
            reviews = json.load(stream)
        result["pending_reviews"] = reviews.get("pending_count")
        if result["state"] == "unavailable":
            result["state"] = "observed"
    except (OSError, ValueError, KeyError) as error:
        result["error"] = ((result["error"] + "; ") if result["error"] else "") + f"mission-reviews: {error}"

    return result


def build_notes(fleetcore, world_intake, mission_bus):
    notes = []
    if fleetcore["state"] != "observed":
        notes.append("FleetCore snapshot unreachable.")
    if world_intake["state"] != "observed":
        notes.append("World Intake unreachable.")
    else:
        count = world_intake["pending_count"]
        age = world_intake["oldest_pending_age_hours"]
        if count and count >= INTAKE_BACKLOG_WARN_COUNT:
            notes.append(f"World Intake backlog: {count} pending proposals.")
        if age is not None and age >= INTAKE_BACKLOG_WARN_AGE_HOURS:
            notes.append(f"Oldest pending proposal is {age:.1f}h old.")
    if mission_bus["state"] != "observed":
        notes.append("Mission Bus projections unavailable (may not have been regenerated recently).")
    if not notes:
        notes.append("Nothing flagged.")
    return notes


def observe(root):
    now = timestamp_utc()
    fleetcore = observe_fleetcore()
    world_intake = observe_world_intake()
    mission_bus = observe_mission_bus(root)
    entry = {
        "timestamp": now.isoformat().replace("+00:00", "Z"),
        "event": "observation",
        "fleetcore": fleetcore,
        "world_intake": world_intake,
        "mission_bus": mission_bus,
        "notes": build_notes(fleetcore, world_intake, mission_bus),
    }
    return now, entry


def append_observation(root, now, entry):
    log_directory = os.path.join(root, LOG_DIR_NAME, now.strftime("%Y"))
    os.makedirs(log_directory, exist_ok=True)
    log_path = os.path.join(log_directory, now.strftime("%Y-%m-%d") + "_watch.jsonl")
    line = json.dumps(entry, ensure_ascii=False, separators=(",", ":"))
    with open(log_path, "a", encoding="utf-8", newline="\n") as stream:
        stream.write(line + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    return log_path


def write_public_status(root, entry):
    public = {
        "schema_version": "monad.watchOfficerStatus.v1",
        "checked_at": entry["timestamp"],
        "fleet": {
            "vessel_count": entry["fleetcore"]["vessel_count"],
            "vessels_by_status": entry["fleetcore"]["vessels_by_status"],
            "clock_state": entry["fleetcore"]["clock_state"],
        },
        "world_intake": {
            "pending_count": entry["world_intake"]["pending_count"],
            "oldest_pending_age_hours": entry["world_intake"]["oldest_pending_age_hours"],
        },
        "mission": {
            "mission_id": entry["mission_bus"]["mission_id"],
            "status": entry["mission_bus"]["mission_status"],
            "pending_reviews": entry["mission_bus"]["pending_reviews"],
        },
        "notes": entry["notes"],
    }
    path = os.path.join(root, PUBLIC_STATUS_PATH)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8", newline="\n") as stream:
        json.dump(public, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp_path, path)
    return path


def stand_watch(once=False):
    root = repo_root()
    next_observation = time.monotonic()

    while True:
        now, entry = observe(root)
        log_path = append_observation(root, now, entry)
        status_path = write_public_status(root, entry)
        print(
            "{} observation appended to {} ({})".format(
                entry["timestamp"],
                os.path.relpath(log_path, root),
                os.path.relpath(status_path, root),
            ),
            flush=True,
        )
        if once:
            return 0

        next_observation += HEARTBEAT_SECONDS
        time.sleep(max(0, next_observation - time.monotonic()))


def parse_args():
    parser = argparse.ArgumentParser(description="Run Watch Officer observations every ten minutes.")
    parser.add_argument("--once", action="store_true", help="write one observation and exit")
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        return stand_watch(once=args.once)
    except KeyboardInterrupt:
        print("Watch Officer relieved.", file=sys.stderr)
        return 0
    except OSError as error:
        print("watch_officer.py: {}".format(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
