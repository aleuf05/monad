#!/usr/bin/env python3
"""Real conversation-ingestion entry point.

There is no live chat surface between the Lieutenant and a captain anywhere
in this repo today (Admiral Bot only drafts pre-curated public dispatches;
the radio-console transcript is scripted ambience -- confirmed by
exploration before this was built). Rather than inventing a fake UI, this
gives an operator or the Lieutenant a genuine way to get a real conversation
into memory: pipe or point it at a transcript.

    python3 tools/living-fleet/memory/log_conversation.py \\
        --captain captain.alpha --with lieutenant.cgl --file transcript.txt

    echo "some transcript text" | python3 tools/living-fleet/memory/log_conversation.py \\
        --captain captain.alpha --with lieutenant.cgl
"""

from __future__ import annotations

import argparse
import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from memory.seed_import import DEFAULT_CAPTAINS, DEFAULT_DB, _read_captains  # noqa: E402
from memory.service import MemoryService  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Record a real conversation transcript into Captain memory.")
    parser.add_argument("--captain", required=True, help="e.g. captain.alpha")
    parser.add_argument("--with", dest="with_id", default="lieutenant.cgl")
    parser.add_argument("--file", default=None, help="Transcript file; omit to read stdin.")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--captains", default=str(DEFAULT_CAPTAINS))
    parser.add_argument("--occurred-at", default=None, help="ISO timestamp; defaults to now (UTC).")
    args = parser.parse_args()

    transcript = Path(args.file).read_text() if args.file else sys.stdin.read()
    if not transcript.strip():
        print("log_conversation: empty transcript, nothing recorded", file=sys.stderr)
        return 1

    occurred_at = args.occurred_at or datetime.datetime.now(datetime.timezone.utc).isoformat()
    captains = _read_captains(Path(args.captains))
    service = MemoryService(args.db, captains)
    try:
        result = service.record_conversation(
            args.captain,
            with_id=args.with_id,
            occurred_at=occurred_at,
            transcript=transcript,
        )
    finally:
        service.close()

    print(f"Recorded: disposition={result['disposition']} salience={result['salience_score']:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
