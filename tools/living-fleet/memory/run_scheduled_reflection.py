#!/usr/bin/env python3
"""Entry point for the scheduled-reflection systemd timer
(scripts/living-fleet-memory-reflect.timer). Calls trigger_reflection with
reason="scheduled" for every configured captain -- the concrete
implementation of the packet's 'scheduled' reflection trigger reason.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from memory.seed_import import DEFAULT_CAPTAINS, DEFAULT_DB, _read_captains  # noqa: E402
from memory.service import MemoryService  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run scheduled reflection for every captain once.")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--captains", default=str(DEFAULT_CAPTAINS))
    args = parser.parse_args()

    captains = _read_captains(Path(args.captains))
    service = MemoryService(args.db, captains)
    try:
        for captain in captains:
            result = service.trigger_reflection(captain["captain_id"], reason="scheduled")
            print(f"{captain['captain_id']}: {result['summary']}")
    finally:
        service.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
