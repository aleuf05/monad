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


def qdrant_health():
    request = urllib.request.Request(
        QDRANT_HEALTH_URL,
        headers={"User-Agent": "monad-watchman/1"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(
            request,
            timeout=QDRANT_TIMEOUT_SECONDS,
        ) as response:
            status_code = response.getcode()
            return {
                "state": "healthy" if 200 <= status_code < 300 else "unhealthy",
                "url": QDRANT_HEALTH_URL,
                "http_status": status_code,
                "error": None,
            }
    except urllib.error.HTTPError as error:
        return {
            "state": "unhealthy",
            "url": QDRANT_HEALTH_URL,
            "http_status": error.code,
            "error": str(error.reason),
        }
    except (urllib.error.URLError, OSError) as error:
        reason = getattr(error, "reason", error)
        return {
            "state": "unreachable",
            "url": QDRANT_HEALTH_URL,
            "http_status": None,
            "error": str(reason),
        }


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
        print(
            "{} heartbeat appended to {}".format(
                entry["timestamp"],
                os.path.relpath(log_path, root),
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
