"""Durable, operator-issued evidence for the full Live Captain speech loop."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_PATH = Path("/home/cgl/dev/monad/data/root-console/speech-acceptance.json")
OUTCOMES = {"passed", "fault"}


def path() -> Path:
    return Path(os.environ.get("MONAD_SPEECH_ACCEPTANCE_PATH", DEFAULT_PATH))


def read() -> dict:
    try:
        value = json.loads(path().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"outcome": "pending"}
    return value if value.get("outcome") in OUTCOMES else {"outcome": "pending"}


def record(outcome: str, note: str = "") -> dict:
    if outcome not in OUTCOMES:
        raise ValueError("outcome must be passed or fault")
    if not isinstance(note, str) or len(note) > 500:
        raise ValueError("note must be at most 500 characters")
    target = path()
    target.parent.mkdir(parents=True, exist_ok=True)
    value = {
        "outcome": outcome,
        "note": note.strip(),
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "authority": "authenticated operator",
        "test": "Admiral speech -> recognition -> Captain turn -> spoken reply",
    }
    fd, temporary = tempfile.mkstemp(prefix=".speech-acceptance-", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2)
            handle.write("\n")
        os.replace(temporary, target)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
    return value
