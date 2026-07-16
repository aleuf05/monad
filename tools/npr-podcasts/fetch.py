#!/usr/bin/env python3
"""
Thin wrapper preserving this exact file path for anyone/anything that still
invokes it directly. The real implementation now lives in
tools/npr-fetch/fetch.py, shared with tools/npr-headlines/fetch.py -- both
existed solely to work around NPR's CORS restriction (feeds only grant CORS
to apps.npr.org) and were duplicating the same fetch boilerplate.
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
    sys.exit(_npr_fetch.fetch_podcasts())
