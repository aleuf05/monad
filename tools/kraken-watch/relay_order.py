#!/usr/bin/env python3
"""Relay a Captain's standing order onto FleetCore's real watch log via
record-watch-event -- the same mechanism Mission Director uses for its own
milestone markers (tools/mission-director/mission_director.py's
post_command()), so the order shows up in the actual live watch_events
stream every instrument/toy already reads, not a separate side channel.

This never issues any command beyond record-watch-event: it cannot set
routes, change escort mode, or alter vessel state. Relaying an order here
is a log entry, not an execution of it -- FleetCore stays the only place
that actually commands the fleet.

Run:
    python3 tools/kraken-watch/relay_order.py
    python3 tools/kraken-watch/relay_order.py --dry-run
    python3 tools/kraken-watch/relay_order.py --message "custom watch note"

Set FLEETCORE_URL to point at a non-default server (defaults to
http://localhost:4771, matching Mission Director's own default).
"""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request

DEFAULT_MESSAGE = (
    "Kraken watch active. Contact K-1 (KRAKEN) under observation, "
    "unidentified. Hold course, maneuvering speed. Continuous sonar "
    "tracking, no active pinging unless contact closes aggressively. "
    "Weapons cold. Comms listen/record only. Do not mistake the unknown "
    "for the hostile; do not mistake restraint for weakness."
)


def fleetcore_url(path: str) -> str:
    base = os.environ.get("FLEETCORE_URL", "http://localhost:4771")
    return f"{base.rstrip('/')}/{path.lstrip('/')}"


def post_command(command: dict) -> dict:
    body = json.dumps(command).encode("utf-8")
    request = urllib.request.Request(
        fleetcore_url("command"),
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise SystemExit(f"error: command rejected ({error.code}): {detail}")
    except urllib.error.URLError as error:
        raise SystemExit(f"error: fleetcore unreachable at {fleetcore_url('command')}: {error.reason}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--message", default=DEFAULT_MESSAGE, help="watch-log message to relay (default: the Kraken watch standing order)")
    parser.add_argument("--dry-run", action="store_true", help="print the command instead of sending it")
    args = parser.parse_args()

    command = {"type": "record-watch-event", "message": args.message}

    if args.dry_run:
        print(json.dumps(command, indent=2))
        return 0

    snapshot = post_command(command)
    watch_events = snapshot.get("watch_events", [])
    last = watch_events[-1] if watch_events else None
    print(f"relayed at tick {snapshot.get('tick')}: {last['message'] if last else args.message}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
