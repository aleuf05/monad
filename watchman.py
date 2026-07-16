#!/usr/bin/env python3
"""Append a five-minute operational heartbeat for the Granite watch."""

import argparse
import datetime
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request


HEARTBEAT_SECONDS = 300
QDRANT_HEALTH_URL = os.environ.get(
    "MONAD_QDRANT_HEALTH_URL",
    "http://127.0.0.1:6333/healthz",
)
QDRANT_TIMEOUT_SECONDS = 3

HTTP_TIMEOUT_SECONDS = 3
LIVING_FLEET_STATE_PATH = os.environ.get(
    "MONAD_LIVING_FLEET_STATE_PATH",
    os.path.join("data", "living-fleet", "runtime.json"),
)
LIVING_FLEET_STALE_SECONDS = int(
    os.environ.get("MONAD_LIVING_FLEET_STALE_SECONDS", "60")
)

# unit name, human key, HTTP health URL (None if the service has no HTTP endpoint)
WATCHED_SERVICES = (
    (
        "fleetcore_serve",
        "fleetcore-serve.service",
        os.environ.get("MONAD_FLEETCORE_HEALTH_URL", "http://127.0.0.1:4771/snapshot"),
    ),
    (
        "world_intake",
        "world-intake.service",
        os.environ.get(
            "MONAD_WORLD_INTAKE_HEALTH_URL",
            "http://127.0.0.1:4773/proposals?status=all",
        ),
    ),
    (
        "living_fleet_memory",
        "living-fleet-memory.service",
        os.environ.get(
            "MONAD_LIVING_FLEET_MEMORY_HEALTH_URL",
            "http://127.0.0.1:4772/captains/summary",
        ),
    ),
    (
        "living_captain_status",
        "living-captain-status.service",
        os.environ.get(
            "MONAD_LIVING_CAPTAIN_STATUS_HEALTH_URL",
            "http://127.0.0.1:4774/status",
        ),
    ),
    ("living_fleet", "living-fleet.service", None),
)


def repo_root():
    return os.path.dirname(os.path.abspath(__file__))


def timestamp_utc():
    return datetime.datetime.now(datetime.timezone.utc)


def uptime_seconds():
    try:
        with open("/proc/uptime", "r", encoding="ascii") as stream:
            return int(float(stream.read().split()[0]))
    except (OSError, ValueError, IndexError):
        return None


def git_commit(root):
    try:
        result = subprocess.run(
            ["git", "-C", root, "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def disk_status(root):
    usage = shutil.disk_usage(root)
    free_percent = round((usage.free / usage.total) * 100, 2)
    return {
        "state": "ok" if free_percent >= 10 else "warning",
        "total_bytes": usage.total,
        "used_bytes": usage.used,
        "free_bytes": usage.free,
        "free_percent": free_percent,
    }


def http_check(url, timeout=HTTP_TIMEOUT_SECONDS):
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "monad-watchman/1"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status_code = response.getcode()
            return {
                "state": "healthy" if 200 <= status_code < 300 else "unhealthy",
                "url": url,
                "http_status": status_code,
                "error": None,
            }
    except urllib.error.HTTPError as error:
        return {
            "state": "unhealthy",
            "url": url,
            "http_status": error.code,
            "error": str(error.reason),
        }
    except (urllib.error.URLError, OSError) as error:
        reason = getattr(error, "reason", error)
        return {
            "state": "unreachable",
            "url": url,
            "http_status": None,
            "error": str(reason),
        }


def qdrant_health():
    return http_check(QDRANT_HEALTH_URL, timeout=QDRANT_TIMEOUT_SECONDS)


def systemd_unit_status(unit):
    try:
        result = subprocess.run(
            [
                "systemctl",
                "show",
                unit,
                "-p",
                "ActiveState,SubState,NRestarts,ActiveEnterTimestamp",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError) as error:
        return {
            "unit": unit,
            "state": "unknown",
            "active_state": None,
            "sub_state": None,
            "restarts": None,
            "since": None,
            "error": str(error),
        }

    fields = {}
    for line in result.stdout.splitlines():
        if "=" in line:
            key, _, value = line.partition("=")
            fields[key] = value

    active_state = fields.get("ActiveState") or None
    sub_state = fields.get("SubState") or None
    restarts_raw = fields.get("NRestarts")
    try:
        restarts = int(restarts_raw) if restarts_raw is not None else None
    except ValueError:
        restarts = None

    if active_state == "active" and sub_state == "running":
        state = "warning" if restarts else "ok"
    elif active_state == "failed":
        state = "failed"
    elif active_state is None:
        state = "unknown"
    else:
        state = "warning"

    return {
        "unit": unit,
        "state": state,
        "active_state": active_state,
        "sub_state": sub_state,
        "restarts": restarts,
        "since": fields.get("ActiveEnterTimestamp") or None,
        "error": result.stderr.strip() or None if result.returncode != 0 else None,
    }


def living_fleet_staleness(root):
    path = os.path.join(root, LIVING_FLEET_STATE_PATH)
    try:
        with open(path, "r", encoding="utf-8") as stream:
            data = json.load(stream)
        last_cycle_at = data["last_cycle_at"]
    except (OSError, ValueError, KeyError, TypeError):
        return {"state": "unknown", "path": path, "age_seconds": None, "error": "state file unreadable"}

    age_seconds = round(time.time() - last_cycle_at, 1)
    return {
        "state": "stale" if age_seconds > LIVING_FLEET_STALE_SECONDS else "ok",
        "path": path,
        "age_seconds": age_seconds,
        "error": None,
    }


def service_status(root, key, unit, health_url):
    entry = {"process": systemd_unit_status(unit)}
    if health_url is not None:
        entry["http"] = http_check(health_url)
    if key == "living_fleet":
        entry["staleness"] = living_fleet_staleness(root)
    return key, entry


def services_status(root):
    return {
        key: entry
        for key, entry in (
            service_status(root, key, unit, health_url)
            for key, unit, health_url in WATCHED_SERVICES
        )
    }


PUBLIC_STATUS_PATH = os.path.join("web", "data", "fleet-status.json")


def derive_public_status(entry):
    """Reduce a full heartbeat to the red/amber/green summary the public
    homepage badge reads -- see web/index.html's status strip and
    docs/deployment.md's "Public Fleet Status" section."""
    red_reasons = []
    amber_reasons = []

    if entry["disk"]["state"] == "warning":
        red_reasons.append("disk space low")
    if entry["qdrant"]["state"] != "healthy":
        amber_reasons.append("qdrant " + entry["qdrant"]["state"])

    for key, service in entry["services"].items():
        label = key.replace("_", "-")
        process = service.get("process") or {}
        if process.get("state") == "failed":
            red_reasons.append(f"{label} failed")
        elif process.get("state") == "warning":
            amber_reasons.append(f"{label} restarted")
        elif process.get("state") == "unknown":
            amber_reasons.append(f"{label} state unknown")

        http = service.get("http")
        if http is not None and http["state"] != "healthy":
            amber_reasons.append(f"{label} endpoint {http['state']}")

        staleness = service.get("staleness")
        if staleness is not None and staleness["state"] != "ok":
            amber_reasons.append(f"{label} {staleness['state']}")

    if red_reasons:
        status = "red"
    elif amber_reasons:
        status = "amber"
    else:
        status = "green"

    reasons = red_reasons + amber_reasons
    summary = "All systems nominal." if not reasons else "; ".join(reasons)

    return {
        "schema_version": "monad.fleetStatus.v1",
        "status": status,
        "summary": summary,
        "checked_at": entry["timestamp"],
        "hostname": entry["hostname"],
        "git_commit": entry["git_commit"],
    }


def write_public_status(root, entry):
    status = derive_public_status(entry)
    path = os.path.join(root, PUBLIC_STATUS_PATH)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8", newline="\n") as stream:
        json.dump(status, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp_path, path)
    return path


def heartbeat(root):
    now = timestamp_utc()
    return now, {
        "timestamp": now.isoformat().replace("+00:00", "Z"),
        "event": "heartbeat",
        "hostname": socket.gethostname(),
        "uptime_seconds": uptime_seconds(),
        "git_commit": git_commit(root),
        "repo_path": root,
        "disk": disk_status(root),
        "qdrant": qdrant_health(),
        "services": services_status(root),
    }


def append_heartbeat(root, now, entry):
    log_directory = os.path.join(
        root,
        "logs",
        "agents",
        "watchman",
        now.strftime("%Y"),
    )
    os.makedirs(log_directory, exist_ok=True)
    log_path = os.path.join(
        log_directory,
        now.strftime("%Y-%m-%d") + "_watch.jsonl",
    )
    line = json.dumps(entry, ensure_ascii=False, separators=(",", ":"))
    with open(log_path, "a", encoding="utf-8", newline="\n") as stream:
        stream.write(line + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    return log_path


def stand_watch(once=False):
    root = repo_root()
    next_heartbeat = time.monotonic()

    while True:
        now, entry = heartbeat(root)
        log_path = append_heartbeat(root, now, entry)
        status_path = write_public_status(root, entry)
        print(
            "{} heartbeat appended to {} ({})".format(
                entry["timestamp"],
                os.path.relpath(log_path, root),
                os.path.relpath(status_path, root),
            ),
            flush=True,
        )
        if once:
            return 0

        next_heartbeat += HEARTBEAT_SECONDS
        time.sleep(max(0, next_heartbeat - time.monotonic()))


def parse_args():
    parser = argparse.ArgumentParser(
        description="Append Monad Watchman heartbeats every five minutes."
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="write one heartbeat and exit",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        return stand_watch(once=args.once)
    except KeyboardInterrupt:
        print("Watchman relieved.", file=sys.stderr)
        return 0
    except OSError as error:
        print("watchman.py: {}".format(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
