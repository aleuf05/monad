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

# Shell analysis is seconds of CPU on a million-vertex mesh, and the answer
# only changes when the file does. Keyed on mtime_ns so an edited asset
# re-analyses automatically.
_SHELL_CACHE: dict[str, tuple[int, dict]] = {}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = urlparse(self.path).path

        if path == "/api/assets":
            self._json(200, {"ok": True, **inspector.collect(REPO_ROOT)})
            return

        if path.startswith("/api/validate/"):
            target = self._safe_asset(path[len("/api/validate/"):])
            if target is None:
                self._json(404, {"ok": False, "error": "not found"})
                return
            key = str(target)
            stamp = target.stat().st_mtime_ns
            cached = _SHELL_CACHE.get(key)
            if cached and cached[0] == stamp:
                self._json(200, {**cached[1], "cached": True})
                return
            try:
                result = inspector.shell_analysis(target)
            except Exception as error:  # noqa: BLE001 - report, don't crash the panel
                self._json(500, {"ok": False, "error": str(error)})
                return
            _SHELL_CACHE[key] = (stamp, result)
            self._json(200, {**result, "cached": False})
            return

        if path.startswith("/api/asset/"):
            target = self._safe_asset(path[len("/api/asset/"):])
            if target is None:
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

    def _safe_asset(self, rel: str) -> Path | None:
        """Resolve a request path to a .glb inside the repo, or nothing.
        An endpoint that takes a path must not be talked out of the repo."""
        target = (REPO_ROOT / unquote(rel)).resolve()
        if not str(target).startswith(str(REPO_ROOT) + "/"):
            return None
        if target.suffix.lower() != ".glb" or not target.is_file():
            return None
        return target

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
