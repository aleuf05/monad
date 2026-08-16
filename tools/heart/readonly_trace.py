#!/usr/bin/env python3
"""Read-only extraction of Heart-style watch packets.

This tool never writes to Heart or changes source records. It deliberately
reports retest and correction-avoidance as unknown unless those observations
are explicitly supplied in the source text.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


FIELDS = ("SIGNAL", "EVIDENCE", "CHANGE", "CONFIDENCE", "SOURCE")


def extract(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    values = {}
    for index, field in enumerate(FIELDS):
        pattern = rf"\*\*{field}:\*\*\s*(.*?)(?=\n\n|\n\*\*|\Z)"
        match = re.search(pattern, text, flags=re.DOTALL)
        values[field.lower()] = " ".join(match.group(1).split()) if match else None

    # Absence is not a successful retest. Only explicit source language can
    # upgrade these states in a future, separately reviewed implementation.
    values.update(
        {
            "source_file": str(path),
            "captured": all(values[field.lower()] for field in FIELDS),
            "retrievable": True,
            "applied": bool(values["change"]),
            "retest_opportunity": "NOT_YET_RETESTED",
            "correction_outcome": "UNKNOWN",
            "promotion_eligible": False,
        }
    )
    return values


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    print(json.dumps(extract(args.source), indent=2))


if __name__ == "__main__":
    main()
