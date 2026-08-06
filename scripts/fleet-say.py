#!/usr/bin/env python3
"""Put a message on the FleetNet wire, to be spoken by the live stream.

    python3 scripts/fleet-say.py claude 4 "Rigging pass complete."
    python3 scripts/fleet-say.py --captain          # relay the Captain's channel

Two sources, and they reach the wire differently on purpose:

**Claude** writes directly. It holds the only write path to production
anyway, so a script is honest about what is already true.

**The Captain** does not write here at all. Its scope forbids `web/`, and
that boundary is not worth eroding for a broadcast feature. Instead it
writes the one file it IS permitted to write — `context/captain-channel.md`,
its own channel — and this relays it. The Captain broadcasts by doing the
thing it was already allowed to do.

The wire is append-only with a cap. Old entries fall off the end rather than
being edited, so what was said stays said.
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
WIRE = REPO / "web" / "data" / "fleetnet-wire.json"
CAPTAIN_CHANNEL = REPO / "tools" / "live-captain" / "context" / "captain-channel.md"
MAX_ENTRIES = 40


def load() -> list:
    try:
        return json.loads(WIRE.read_text())["entries"]
    except (OSError, ValueError, KeyError):
        return []


def say(source: str, priority: int, text: str) -> dict:
    text = " ".join(text.split())
    if not text:
        raise SystemExit("nothing to say")
    entries = load()
    # id from content, so relaying the same Captain message twice does not
    # make the stream repeat itself
    entry_id = hashlib.sha256(f"{source}|{text}".encode()).hexdigest()[:12]
    if any(e["id"] == entry_id for e in entries):
        return {"skipped": "already on the wire", "id": entry_id}
    entries.append({
        "id": entry_id,
        "from": source,
        "priority": max(0, min(10, int(priority))),
        "text": text,
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    })
    WIRE.parent.mkdir(parents=True, exist_ok=True)
    WIRE.write_text(json.dumps({"entries": entries[-MAX_ENTRIES:]}, indent=2))
    return {"id": entry_id, "from": source, "text": text}


def relay_captain() -> dict:
    """Read the Captain's own channel and put its latest word on the wire."""
    try:
        raw = CAPTAIN_CHANNEL.read_text(encoding="utf-8")
    except OSError as error:
        raise SystemExit(f"cannot read the Captain's channel: {error}")
    # Its last substantive paragraph — headers and fences are not speech.
    paras = [p.strip().replace("\n", " ") for p in raw.split("\n\n")]
    body = [p for p in paras
            if p and not p.startswith("#") and not p.startswith("```")
            and len(p) > 40]
    if not body:
        raise SystemExit("the Captain's channel has nothing to say")
    return say("captain", 5, body[-1][:400])


def main(argv: list[str]) -> int:
    if len(argv) > 1 and argv[1] == "--captain":
        print(json.dumps(relay_captain(), indent=2))
        return 0
    if len(argv) < 4:
        print(__doc__)
        return 2
    print(json.dumps(say(argv[1], argv[2], " ".join(argv[3:])), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
