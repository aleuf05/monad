#!/usr/bin/env python3
"""Keep web/command-deck.html an exact mirror of web/index.html (title excepted).

docs/deployment.md requires these two files stay byte-identical except
their <title>, so old bookmarked URLs to command-deck.html keep working.
Hand-copying that invariant has drifted twice in one session (see
BRIDGE-RETIRE-01, CMDDECK-SYNC-01) -- this script makes it structural
instead of remembered.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "web" / "index.html"
COMMAND_DECK = ROOT / "web" / "command-deck.html"
INDEX_TITLE = "<title>Fleet Monad</title>"
COMMAND_DECK_TITLE = "<title>Fleet Monad — Command Deck</title>"


def derive_command_deck(index_html: str) -> str:
    if INDEX_TITLE not in index_html:
        raise SystemExit(f"error: {INDEX} does not contain the expected title tag {INDEX_TITLE!r}")
    return index_html.replace(INDEX_TITLE, COMMAND_DECK_TITLE, 1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write", action="store_true",
        help="regenerate web/command-deck.html from web/index.html (default: check only)",
    )
    args = parser.parse_args()

    index_html = INDEX.read_text(encoding="utf-8")
    expected = derive_command_deck(index_html)

    if args.write:
        COMMAND_DECK.write_text(expected, encoding="utf-8")
        print(f"Wrote {COMMAND_DECK} from {INDEX}.")
        return 0

    actual = COMMAND_DECK.read_text(encoding="utf-8") if COMMAND_DECK.exists() else None
    if actual == expected:
        print("web/command-deck.html matches web/index.html (title excepted).")
        return 0

    print("web/command-deck.html has drifted from web/index.html -- run with --write to resync.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
