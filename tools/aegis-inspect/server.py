#!/usr/bin/env python3
"""HTTP surface for Aegis INSPECT. Gated by the same forward_auth as the console."""

from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import inspector  # noqa: E402

HOST, PORT = "127.0.0.1", 4799
REPO_ROOT = Path(__file__).resolve().parents[2]


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = urlparse(self.path).path

        if path == "/api/assets":
            self._json(200, {"ok": True, **inspector.collect(REPO_ROOT)})
            return

        if path.startswith("/api/asset/"):
            rel = unquote(path[len("/api/asset/"):])
            target = (REPO_ROOT / rel).resolve()
            # Containment check: a preview endpoint that accepts a path
            # must not be talked out of the repo with ../
            if not str(target).startswith(str(REPO_ROOT)) or target.suffix.lower() != ".glb" or not target.is_file():
                self._json(404, {"ok": False, "error": "not found"})
                return
            body = target.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "model/gltf-binary")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(body)
            return

        self._json(404, {"ok": False, "error": "not found"})

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args) -> None:
        pass


class Server(ThreadingHTTPServer):
    daemon_threads = True


def main() -> int:
    server = Server((HOST, PORT), Handler)
    print(f"aegis-inspect listening on http://{HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
