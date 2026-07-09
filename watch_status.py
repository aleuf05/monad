#!/usr/bin/env python3
"""Report whether the Monad Watchman is keeping the watch."""

import datetime
import json
import os
import sys


STALE_AFTER_SECONDS = 600
LOG_RELATIVE_PATH = os.path.join("logs", "agents", "watchman")


def repo_root():
    return os.path.dirname(os.path.abspath(__file__))


def most_recent_log(root):
    log_root = os.path.join(root, LOG_RELATIVE_PATH)
    candidates = []
    for directory, _, names in os.walk(log_root):
        for name in names:
            if name.endswith("_watch.jsonl"):
                candidates.append(os.path.join(directory, name))
    if not candidates:
        return None
    return max(candidates, key=os.path.getmtime)


def reverse_lines(path, block_size=4096):
    with open(path, "rb") as stream:
        stream.seek(0, os.SEEK_END)
        position = stream.tell()
        remainder = b""

        while position > 0:
            read_size = min(block_size, position)
            position -= read_size
            stream.seek(position)
            parts = (stream.read(read_size) + remainder).split(b"\n")
            remainder = parts[0]
            for raw_line in reversed(parts[1:]):
                if raw_line.strip():
                    yield raw_line

        if remainder.strip():
            yield remainder


def latest_heartbeat(path):
    for raw_line in reverse_lines(path):
        try:
            entry = json.loads(raw_line.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if isinstance(entry, dict) and entry.get("event") == "heartbeat":
            return entry
    return None


def parse_timestamp(value):
    if not isinstance(value, str):
        raise ValueError("heartbeat timestamp is missing")
    parsed = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("heartbeat timestamp has no timezone")
    return parsed.astimezone(datetime.timezone.utc)


def format_age(seconds):
    seconds = max(0, int(seconds))
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    parts = []
    if days:
        parts.append("{}d".format(days))
    if hours or days:
        parts.append("{}h".format(hours))
    if minutes or hours or days:
        parts.append("{}m".format(minutes))
    parts.append("{}s".format(seconds))
    return " ".join(parts)


def display_timestamp(timestamp):
    return timestamp.strftime("%Y-%m-%d %H:%M UTC")


def short_commit(value):
    if isinstance(value, str) and value:
        return value[:7]
    return "UNKNOWN"


def disk_report(entry):
    disk = entry.get("disk")
    if not isinstance(disk, dict):
        return "UNKNOWN", False
    state = str(disk.get("state", "unknown")).lower()
    free_percent = disk.get("free_percent")
    percent = (
        " ({:.1f}% free)".format(free_percent)
        if isinstance(free_percent, (int, float))
        else ""
    )
    healthy = state == "ok"
    return ("OK" if healthy else state.upper()) + percent, healthy


def qdrant_report(entry):
    qdrant = entry.get("qdrant")
    if not isinstance(qdrant, dict):
        return "UNKNOWN", False
    state = str(qdrant.get("state", "unknown")).lower()
    healthy = state == "healthy"
    return "OK" if healthy else state.upper(), healthy


def print_report(
    hostname,
    watchman,
    heartbeat_time,
    age,
    commit,
    disk,
    qdrant,
    overall,
):
    print("MONAD WATCH STATUS")
    print()
    print("Host: {}".format(hostname))
    print("Watchman: {}".format(watchman))
    print("Last heartbeat: {}".format(heartbeat_time))
    print("Age: {}".format(age))
    print("Git: {}".format(commit))
    print("Disk: {}".format(disk))
    print("Qdrant: {}".format(qdrant))
    print()
    print("STATUS: {}".format(overall))


def red_report(hostname="UNKNOWN"):
    print_report(
        hostname=hostname,
        watchman="NOT ON WATCH",
        heartbeat_time="UNKNOWN",
        age="UNKNOWN",
        commit="UNKNOWN",
        disk="UNKNOWN",
        qdrant="UNKNOWN",
        overall="RED",
    )
    return 2


def main():
    log_path = most_recent_log(repo_root())
    if log_path is None:
        return red_report()

    entry = latest_heartbeat(log_path)
    if entry is None:
        return red_report()

    hostname = entry.get("hostname") or "UNKNOWN"
    try:
        heartbeat_time = parse_timestamp(entry.get("timestamp"))
    except (TypeError, ValueError):
        return red_report(hostname)

    age_seconds = (
        datetime.datetime.now(datetime.timezone.utc) - heartbeat_time
    ).total_seconds()
    disk, disk_healthy = disk_report(entry)
    qdrant, qdrant_healthy = qdrant_report(entry)
    recent = -60 <= age_seconds <= STALE_AFTER_SECONDS

    if not recent:
        overall = "RED"
        watchman = "WATCH STALE"
        exit_code = 2
    elif disk_healthy and qdrant_healthy:
        overall = "GREEN"
        watchman = "ON WATCH"
        exit_code = 0
    else:
        overall = "YELLOW"
        watchman = "ON WATCH"
        exit_code = 1

    print_report(
        hostname=hostname,
        watchman=watchman,
        heartbeat_time=display_timestamp(heartbeat_time),
        age=format_age(age_seconds),
        commit=short_commit(entry.get("git_commit")),
        disk=disk,
        qdrant=qdrant,
        overall=overall,
    )
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
