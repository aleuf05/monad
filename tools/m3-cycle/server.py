#!/usr/bin/env python3
"""HTTP surface for the M³ cycle, behind the Root Console.

Evaluate is read-only and safe to call at any time. Commit and rollback
change the repository, and both re-evaluate first rather than trusting a
verdict the browser is holding -- the working tree can move between a
page render and a button press.

Gated by the same Caddy forward_auth check as the console page, so no
second password.
"""

from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine  # noqa: E402

HOST = "127.0.0.1"
PORT = 4798
REPO_ROOT = Path(__file__).resolve().parents[2]


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if urlparse(self.path).path != "/api/evaluate":
            self._json(404, {"ok": False, "error": "not found"})
            return
        try:
            self._json(200, {"ok": True, "result": engine.evaluate(REPO_ROOT)})
        except engine.CycleError as error:
            self._json(500, {"ok": False, "error": str(error)})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path not in ("/api/commit", "/api/rollback"):
            self._json(404, {"ok": False, "error": "not found"})
            return
        try:
            # Re-evaluate rather than trusting the browser's copy of the
            # verdict: C_t is defined as triggered only when the tri-condition
            # holds, and the tree may have moved since the page rendered.
            result = engine.evaluate(REPO_ROOT)
            if not result["proposed"]:
                self._json(400, {"ok": False, "error": "no Δ_t to act on"})
                return

            if path == "/api/rollback":
                engine.rollback(REPO_ROOT)
                self._json(200, {"ok": True, "action": "rollback",
                                 "restored": len(result["changed"])})
                return

            if result["verdict"] != "commit":
                self._json(409, {
                    "ok": False, "action": "commit-refused",
                    "error": "tri-condition does not hold; commit is not available",
                    "result": result,
                })
                return

            count = len(result["changed"])
            message = (
                f"M³ cycle: commit {count} document change(s)\n\n"
                f"Cont=1, V {result['valuation']['before']} -> "
                f"{result['valuation']['after']}, "
                f"Q_rev improved: {', '.join(result['q_rev']['improved']) or 'none'}.\n\n"
                "Evaluated by tools/m3-cycle/engine.py against the tri-condition\n"
                "axiom of MSIR-M3-NUCLEAR-PACKET-02 §II."
            )
            self._json(200, {"ok": True, "action": "commit",
                             **engine.commit(REPO_ROOT, message)})
        except engine.CycleError as error:
            self._json(500, {"ok": False, "error": str(error)})

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args) -> None:  # noqa: A002
        pass


class Server(ThreadingHTTPServer):
    daemon_threads = True


def main() -> int:
    server = Server((HOST, PORT), Handler)
    print(f"m3-cycle listening on http://{HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
