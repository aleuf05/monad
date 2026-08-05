#!/usr/bin/env python3
"""Public, unauthenticated, always-on live read of the ship's log.

No sync step, no manifest file, no cron job, no cache of any kind. Every
GET /api/docs call runs ship_log.collect() fresh against the real files on
disk at that exact instant and returns the result directly. This exists
because the public document viewer must show what's on disk right now, not
a periodic snapshot -- see docs/logs for context if this comment is ever
questioned again.

Deliberately restricted to the "ship-log" source (docs/logs/*.md) only.
ship_log.collect() also returns the continuity ledger, current bearing, and
two internal JSONL telemetry logs -- those are the Captain's internal
operating state, not public-facing documentation, and stay authenticated-
only on root-console's /api/ship-log panel. Do not widen this filter
without an explicit decision to make more of that state public.
"""

from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
REPO_ROOT = ROOT_DIR.parent.parent
sys.path.insert(0, str(ROOT_DIR))
import ship_log  # noqa: E402

HOST = "127.0.0.1"
PORT = 4794


class PublicDocsHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:  # noqa: A002
        sys.stderr.write("%s - %s\n" % (self.address_string(), format % args))

    def do_GET(self) -> None:  # noqa: N802
        if self.path != "/api/docs":
            self.send_error(404)
            return
        entries = [entry for entry in ship_log.collect(REPO_ROOT) if entry["source"] == "ship-log"]
        body = json.dumps({"entries": entries}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), PublicDocsHandler)
    print(f"public-docs-api listening on {HOST}:{PORT}", file=sys.stderr)
    server.serve_forever()


if __name__ == "__main__":
    main()
