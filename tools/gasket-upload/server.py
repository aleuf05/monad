#!/usr/bin/env python3
"""Live GLB upload for the public Gasket 3D stage on the front page.

Public-facing: web/index.html embeds an upload form directly in the
Gasket section so the Admiral can drop in a new .glb from any browser,
no SSH/SCP needed. The upload itself is password-gated (same scrypt +
rate-limit pattern as tools/public-root-auth/server.py, reusing that
same env file/password -- the one already used to authorize live edits
on this site) since an open unauthenticated write endpoint on the public
site would let anyone overwrite the model or fill the disk.

No manifest, no sync job: a successful upload overwrites
web/assets/models/gasket/gasket.glb directly (atomic rename), and the
front-end's Three.js viewer reads that exact path live, cache-busted by
mtime. This is the one file on disk; there is no other copy to keep in
sync.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

HOST = "127.0.0.1"
PORT = 4796
MODEL_DIR = Path(__file__).resolve().parents[2] / "web" / "assets" / "models" / "gasket"
MODEL_PATH = MODEL_DIR / "gasket.glb"
MAX_UPLOAD_BYTES = 150 * 1024 * 1024  # generous ceiling for a Tripo GLB export
GLB_MAGIC = b"glTF"
LOGIN_WINDOW_SECONDS = 60
LOGIN_ATTEMPTS_PER_WINDOW = 5


class AuthConfig:
    def __init__(self, salt: bytes, password_hash: bytes):
        self.salt = salt
        self.password_hash = password_hash

    @classmethod
    def from_environment(cls) -> "AuthConfig":
        return cls(
            bytes.fromhex(os.environ["ROOT_AUTH_PASSWORD_SALT"]),
            bytes.fromhex(os.environ["ROOT_AUTH_PASSWORD_HASH"]),
        )

    def verify_password(self, password: str) -> bool:
        candidate = hashlib.scrypt(password.encode("utf-8"), salt=self.salt, n=2**14, r=8, p=1, dklen=32)
        return hmac.compare_digest(candidate, self.password_hash)


class Server(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, handler, auth: AuthConfig):
        super().__init__(address, handler)
        self.auth = auth
        self.login_attempts: list[float] = []

    def allow_login_attempt(self) -> bool:
        now = time.monotonic()
        self.login_attempts = [a for a in self.login_attempts if now - a < LOGIN_WINDOW_SECONDS]
        if len(self.login_attempts) >= LOGIN_ATTEMPTS_PER_WINDOW:
            return False
        self.login_attempts.append(now)
        return True


def _parse_multipart(body: bytes, boundary: bytes) -> dict[str, dict]:
    parts: dict[str, dict] = {}
    delimiter = b"--" + boundary
    for chunk in body.split(delimiter):
        chunk = chunk.strip(b"\r\n")
        if not chunk or chunk == b"--":
            continue
        header_blob, _, content = chunk.partition(b"\r\n\r\n")
        if not content:
            continue
        content = content[:-2] if content.endswith(b"\r\n") else content
        headers = header_blob.decode("utf-8", "replace")
        name = None
        filename = None
        for line in headers.split("\r\n"):
            if line.lower().startswith("content-disposition:"):
                for piece in line.split(";"):
                    piece = piece.strip()
                    if piece.startswith("name="):
                        name = piece.split("=", 1)[1].strip('"')
                    elif piece.startswith("filename="):
                        filename = piece.split("=", 1)[1].strip('"')
        if name:
            parts[name] = {"filename": filename, "content": content}
    return parts


class Handler(BaseHTTPRequestHandler):
    server: Server

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path != "/api/upload":
            self._json(404, {"ok": False, "error": "not found"})
            return

        length = int(self.headers.get("Content-Length", 0))
        if length <= 0 or length > MAX_UPLOAD_BYTES:
            self._json(413, {"ok": False, "error": f"payload must be under {MAX_UPLOAD_BYTES // (1024*1024)}MB"})
            return

        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type or "boundary=" not in content_type:
            self._json(400, {"ok": False, "error": "expected multipart/form-data"})
            return
        boundary = content_type.split("boundary=", 1)[1].strip().strip('"').encode("utf-8")

        body = self.rfile.read(length)
        parts = _parse_multipart(body, boundary)

        if not self.server.allow_login_attempt():
            self._json(429, {"ok": False, "error": "too many attempts, wait a minute"})
            return

        password = parts.get("password", {}).get("content", b"").decode("utf-8", "replace")
        if not password or not self.server.auth.verify_password(password):
            self._json(401, {"ok": False, "error": "incorrect password"})
            return

        upload = parts.get("file")
        if not upload or not upload["content"]:
            self._json(400, {"ok": False, "error": "no file provided"})
            return

        data = upload["content"]
        if data[:4] != GLB_MAGIC:
            self._json(400, {"ok": False, "error": "not a valid .glb (binary glTF) file"})
            return

        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        tmp_path = MODEL_DIR / ".gasket.glb.tmp"
        tmp_path.write_bytes(data)
        os.replace(tmp_path, MODEL_PATH)

        self._json(200, {"ok": True, "bytes": len(data), "uploaded_at": int(time.time())})

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/status":
            exists = MODEL_PATH.is_file()
            self._json(200, {
                "ok": True,
                "exists": exists,
                "mtime": int(MODEL_PATH.stat().st_mtime) if exists else None,
                "bytes": MODEL_PATH.stat().st_size if exists else None,
            })
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

    def log_message(self, format, *args) -> None:  # noqa: A002
        pass


def main() -> int:
    try:
        auth = AuthConfig.from_environment()
    except (KeyError, ValueError) as error:
        print(f"gasket-upload cannot start: {error}", file=sys.stderr)
        return 2
    server = Server((HOST, PORT), Handler, auth)
    print(f"gasket-upload listening on http://{HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
