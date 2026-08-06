#!/usr/bin/env python3
"""HTTP surface for Aegis INSPECT. Gated by the same forward_auth as the console."""

from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "aegis-rig"))
import inspector  # noqa: E402
import pipeline  # noqa: E402
import solver  # noqa: E402

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

        if path == "/api/pipeline":
            self._json(200, {
                "ok": True,
                "stages": [
                    {"stage": "INSPECT", "built": True,
                     "note": "reads structure and rig state from the glTF JSON"},
                    {"stage": "VALIDATE", "built": True,
                     "note": "union-find over the index buffer; disjoint-shell risk"},
                    {"stage": "AUTHORIZE", "built": True,
                     "note": "runs the gates and issues a single-use token"},
                    {"stage": "EXECUTE", "built": True,
                     "note": "synthesises the skeleton and writes a rigged .glb"},
                    {"stage": "RECORD", "built": True,
                     "note": "commits to git — git is the provenance store"},
                ],
                "engine": "rust" if solver.core_available() else "python",
                "engine_note": (
                    "Rust core built — maths runs native"
                    if solver.core_available()
                    else "Rust core not built; falling back to the Python reference"),
                "rigid_span_factor": solver.RIGID_SPAN_FACTOR,
                "default_joints": solver.DEFAULT_JOINTS,
            })
            return

        self._json(404, {"ok": False, "error": "not found"})

    def do_POST(self) -> None:
        path = urlparse(self.path).path

        if path.startswith("/api/authorize/"):
            target = self._safe_asset(path[len("/api/authorize/"):])
            if target is None:
                self._json(404, {"ok": False, "error": "not found"})
                return
            joints = self._joint_count()
            try:
                self._json(200, pipeline.authorize(target, joints))
            except Exception as error:  # noqa: BLE001 - report, don't crash the panel
                self._json(500, {"ok": False, "error": str(error)})
            return

        for name, action in (("execute", pipeline.execute), ("record", pipeline.record)):
            prefix = f"/api/{name}/"
            if path.startswith(prefix):
                token = unquote(path[len(prefix):]).strip("/")
                try:
                    self._json(200, action(token))
                except pipeline.PipelineError as error:
                    self._json(409, {"ok": False, "stage": name.upper(),
                                     "error": str(error)})
                except Exception as error:  # noqa: BLE001
                    self._json(500, {"ok": False, "stage": name.upper(),
                                     "error": str(error)})
                return

        self._json(404, {"ok": False, "error": "not found"})

    def _joint_count(self) -> int:
        raw = urlparse(self.path).query
        for part in raw.split("&"):
            if part.startswith("joints="):
                try:
                    return max(2, min(64, int(part[len("joints="):])))
                except ValueError:
                    break
        return solver.DEFAULT_JOINTS

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
