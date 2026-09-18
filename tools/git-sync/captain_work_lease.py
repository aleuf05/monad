#!/usr/bin/env python3
"""Create, inspect, or release the Captain's expiring auto-sync work lease."""

import argparse
import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from auto_sync import LEASE_FILE, load_active_lease


def write_lease(paths: list[str], minutes: int) -> None:
    if not 1 <= minutes <= 60:
        raise SystemExit("minutes must be between 1 and 60")
    payload = {
        "paths": [path.strip("/") or "." for path in paths],
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat().replace("+00:00", "Z"),
    }
    LEASE_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix="captain-work-lease-", dir=LEASE_FILE.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")
        os.replace(tmp_name, LEASE_FILE)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
    print(f"LEASE: active until {payload['expires_at']} for {', '.join(payload['paths'])}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    start = subcommands.add_parser("start")
    start.add_argument("paths", nargs="+", help="repository-relative paths to hold")
    start.add_argument("--minutes", type=int, default=15)
    subcommands.add_parser("status")
    subcommands.add_parser("release")
    args = parser.parse_args()
    if args.command == "start":
        write_lease(args.paths, args.minutes)
    elif args.command == "status":
        lease = load_active_lease()
        print("LEASE: none" if not lease else f"LEASE: active until {lease['expires_at'].isoformat()} for {', '.join(lease['paths'])}")
    elif args.command == "release":
        LEASE_FILE.unlink(missing_ok=True)
        print("LEASE: released")


if __name__ == "__main__":
    main()
