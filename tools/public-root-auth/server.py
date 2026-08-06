#!/usr/bin/env python3
"""Password-only auth gate for the public https://cameronlampley.com/root
fallback. Deliberately separate from tools/chat-captain/server.py -- this
guards Caddy's forward_auth check for a public path, not the LAN-only
Chat Captain app itself, and has nothing to do with the Codex-backed
conversation engine.

Single admin password, no username -- this page has exactly one intended
user. Auth block (scrypt + HMAC-signed session cookie) follows the same
pattern used earlier in tools/chat-captain/server.py before that service's
password was removed as redundant with LAN isolation; here the threat
model is different (this path is genuinely public), so a password gate
is appropriate.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import sys
import time
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HOST = "127.0.0.1"
PORT = 4779
COOKIE_NAME = "monad_root_session"
SESSION_SECONDS = 365 * 24 * 60 * 60  # "log in once" -- a year, not a day.
LOGIN_WINDOW_SECONDS = 60
LOGIN_ATTEMPTS_PER_WINDOW = 5

LOGIN_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Admiral's Console</title>
<style>
  body {{ background:#0B1220; color:#DCE6F2; font-family:'JetBrains Mono',monospace;
    min-height:100vh; display:flex; align-items:center; justify-content:center; margin:0; }}
  form {{ background:#111A2B; border:1px solid #1E2C42; border-radius:10px; padding:28px;
    width:100%; max-width:320px; display:flex; flex-direction:column; gap:12px; }}
  h1 {{ font-size:18px; color:#E8A33D; margin:0 0 4px; }}
  input {{ background:#0B1220; border:1px solid #1E2C42; color:#DCE6F2; padding:10px; border-radius:6px; font:inherit; }}
  button {{ background:#4FD1C5; color:#05201D; border:none; border-radius:6px; padding:10px; font-weight:700; cursor:pointer; font:inherit; }}
  .error {{ color:#E05252; font-size:12px; margin:0; }}
</style></head>
<body>
<form method="post" action="/root-login">
  <h1>⚓ Admiral's Console</h1>
  <input type="password" name="password" placeholder="Password" autocomplete="current-password" autofocus required>
  <button type="submit">Enter</button>
  {error}
</form>
</body></html>"""


class AuthConfig:
    def __init__(self, salt: bytes, password_hash: bytes, session_secret: bytes):
        self.salt = salt
        self.password_hash = password_hash
        self.session_secret = session_secret

    @classmethod
    def from_environment(cls) -> "AuthConfig":
        return cls(
            bytes.fromhex(os.environ["ROOT_AUTH_PASSWORD_SALT"]),
            bytes.fromhex(os.environ["ROOT_AUTH_PASSWORD_HASH"]),
            bytes.fromhex(os.environ["ROOT_AUTH_SESSION_SECRET"]),
        )

    def verify_password(self, password: str) -> bool:
        candidate = hashlib.scrypt(password.encode("utf-8"), salt=self.salt, n=2**14, r=8, p=1, dklen=32)
        return hmac.compare_digest(candidate, self.password_hash)

    def issue_session(self) -> str:
        timestamp = int(time.time())
        payload = f"{timestamp}.{secrets.token_hex(16)}"
        signature = hmac.new(self.session_secret, payload.encode("ascii"), hashlib.sha256).hexdigest()
        return f"{payload}.{signature}"

    def verify_session(self, token: str) -> bool:
        try:
            timestamp_text, nonce, supplied = token.split(".", 2)
            timestamp = int(timestamp_text)
        except (ValueError, AttributeError):
            return False
        now = int(time.time())
        if timestamp > now + 60 or now - timestamp > SESSION_SECONDS:
            return False
        payload = f"{timestamp}.{nonce}"
        expected = hmac.new(self.session_secret, payload.encode("ascii"), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, supplied)


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


class Handler(BaseHTTPRequestHandler):
    server: Server

    def _authenticated(self) -> bool:
        cookie = SimpleCookie(self.headers.get("Cookie", ""))
        morsel = cookie.get(COOKIE_NAME)
        return bool(morsel and self.server.auth.verify_session(morsel.value))

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/check":
            self._send(200 if self._authenticated() else 401, b"")
            return
        if path == "/check-page":
            # Same check as /check, but for forward_auth gating a real
            # page load (/root/*), not a JS fetch() to the API. Caddy's
            # forward_auth returns any non-2xx response from here
            # directly to the client -- handle_errors cannot intercept
            # it (it's a normal response, not a Caddy "error"; confirmed
            # live) -- so the redirect has to be issued right here.
            if self._authenticated():
                self._send(200, b"")
            else:
                self.send_response(302)
                self.send_header("Location", "/root-login")
                self.send_header("Content-Length", "0")
                self.end_headers()
            return
        if path == "/root-login":
            self._send_html(200, LOGIN_PAGE.format(error=""))
            return
        self._send(404, b"not found")

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path != "/root-login":
            self._send(404, b"not found")
            return
        length = int(self.headers.get("Content-Length", 0))
        body = parse_qs(self.rfile.read(length).decode("utf-8"))
        password = (body.get("password") or [""])[0]

        if not self.server.allow_login_attempt():
            self._send_html(429, LOGIN_PAGE.format(error='<p class="error">Too many attempts, wait a minute.</p>'))
            return
        if not password or not self.server.auth.verify_password(password):
            self._send_html(401, LOGIN_PAGE.format(error='<p class="error">Incorrect password.</p>'))
            return

        token = self.server.auth.issue_session()
        self.send_response(303)
        self.send_header("Location", "/root/")
        self.send_header(
            "Set-Cookie",
            f"{COOKIE_NAME}={token}; Path=/; Max-Age={SESSION_SECONDS}; HttpOnly; SameSite=Lax; Secure",
        )
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _send(self, status: int, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, status: int, html: str) -> None:
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
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
        print(f"public-root-auth cannot start: {error}", file=sys.stderr)
        return 2
    server = Server((HOST, PORT), Handler, auth)
    print(f"public-root-auth listening on http://{HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
