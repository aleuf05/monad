#!/usr/bin/env python3
"""
Thin wrapper preserving this exact file path -- the live 15-minute crontab
entry (`crontab -l`) invokes it directly by this path, and changing that
requires a crontab edit, an infrastructure change this project routes
through the Lieutenant/cmd.sh rather than an agent session touching it
directly. The real implementation now lives in tools/npr-fetch/fetch.py,
shared with tools/npr-podcasts/fetch.py -- both existed solely to work
around NPR's CORS restriction and were duplicating the same fetch
boilerplate. Do not delete this file without first updating that crontab
entry.
"""
import importlib.util
import sys
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "npr_fetch", Path(__file__).resolve().parents[1] / "npr-fetch" / "fetch.py"
)
_npr_fetch = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_npr_fetch)

if __name__ == "__main__":
    sys.exit(_npr_fetch.fetch_headlines())
