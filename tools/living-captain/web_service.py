#!/usr/bin/env python3
"""Authenticated loopback API for Live Captain Private Conference."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import sys
import threading
import time
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from conversation import ConversationStore
from gemini_provider import GeminiProvider
from live_captain_engine import CaptainEngine, OwnershipError, SecretRejected
from model_provider import ProviderError
from usage_budget import BudgetExceeded, UsageBudget


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "living-captain"
PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "captain-system.md"
HOST = "127.0.0.1"
PORT = 4776
ALLOWED_ORIGIN = "https://cameronlampley.com"
COOKIE_NAME = "monad_captain_session"
SESSION_SECONDS = 12 * 60 * 60
MAX_BODY_BYTES = 16_384
MAX_MESSAGE_CHARS = 4_000
LOGIN_WINDOW_SECONDS = 60
LOGIN_ATTEMPTS_PER_WINDOW = 5


class AuthConfig:
    def __init__(self, salt: bytes, password_hash: bytes, session_secret: bytes):
        self.salt = salt
        self.password_hash = password_hash
        self.session_secret = session_secret

    @classmethod
    def from_environment(cls) -> "AuthConfig":
        try:
            return cls(
                bytes.fromhex(os.environ["LIVE_CAPTAIN_PASSWORD_SALT"]),
                bytes.fromhex(os.environ["LIVE_CAPTAIN_PASSWORD_HASH"]),
                bytes.fromhex(os.environ["LIVE_CAPTAIN_SESSION_SECRET"]),
            )
        except (KeyError, ValueError) as error:
            raise ValueError("Private Conference authentication is not configured") from error

    def verify_password(self, password: str) -> bool:
        candidate = hashlib.scrypt(
            password.encode("utf-8"),
            salt=self.salt,
            n=2**14,
            r=8,
            p=1,
            dklen=32,
        )
        return hmac.compare_digest(candidate, self.password_hash)

    def issue_session(self, now: int | None = None) -> str:
        timestamp = int(time.time()) if now is None else now
        payload = f"{timestamp}.{secrets.token_hex(16)}"
        signature = hmac.new(
            self.session_secret,
            payload.encode("ascii"),
            hashlib.sha256,
        ).digest()
        encoded = base64.urlsafe_b64encode(signature).decode("ascii").rstrip("=")
        return f"{payload}.{encoded}"

    def verify_session(self, token: str, now: int | None = None) -> bool:
        try:
            timestamp_text, nonce, supplied = token.split(".", 2)
            timestamp = int(timestamp_text)
        except (ValueError, AttributeError):
            return False
        current = int(time.time()) if now is None else now
        if timestamp > current + 60 or current - timestamp > SESSION_SECONDS:
            return False
        payload = f"{timestamp}.{nonce}"
        signature = hmac.new(
            self.session_secret,
            payload.encode("ascii"),
            hashlib.sha256,
        ).digest()
        expected = base64.urlsafe_b64encode(signature).decode("ascii").rstrip("=")
        return hmac.compare_digest(expected, supplied)


class ConferenceServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, handler, engine: CaptainEngine, auth: AuthConfig):
        super().__init__(address, handler)
        self.engine = engine
        self.auth = auth
        self.inference_lock = threading.Lock()
        self.login_lock = threading.Lock()
        self.login_attempts: list[float] = []

    def allow_login_attempt(self) -> bool:
        now = time.monotonic()
        with self.login_lock:
            self.login_attempts = [
                attempt
                for attempt in self.login_attempts
                if now - attempt < LOGIN_WINDOW_SECONDS
            ]
            if len(self.login_attempts) >= LOGIN_ATTEMPTS_PER_WINDOW:
                return False
            self.login_attempts.append(now)
            return True


class Handler(BaseHTTPRequestHandler):
    server: ConferenceServer

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/health":
            self._json({"ok": True, "service": "live-captain-conference"})
            return
        if not self._authenticated():
            self._json({"ok": False, "error": "authentication required"}, 401)
            return
        if path == "/status":
            self._json({"ok": True, **self.server.engine.status()})
            return
        if path == "/messages":
            self._json(
                {
                    "ok": True,
                    "session_id": self.server.engine.store.session_id,
                    "messages": self.server.engine.transcript(),
                }
            )
            return
        self._json({"ok": False, "error": "not found"}, 404)

    def do_POST(self) -> None:
        if self.headers.get("Origin") != ALLOWED_ORIGIN:
            self._json({"ok": False, "error": "origin rejected"}, 403)
            return
        path = urlparse(self.path).path
        try:
            body = self._read_json()
        except ValueError as error:
            self._json({"ok": False, "error": str(error)}, 400)
            return
        if path == "/login":
            if not self.server.allow_login_attempt():
                self._json({"ok": False, "error": "login temporarily limited"}, 429)
                return
            password = body.get("password")
            if not isinstance(password, str) or not self.server.auth.verify_password(password):
                self._json({"ok": False, "error": "invalid credentials"}, 401)
                return
            token = self.server.auth.issue_session()
            self._json(
                {"ok": True},
                headers={
                    "Set-Cookie": (
                        f"{COOKIE_NAME}={token}; Path=/; Max-Age={SESSION_SECONDS}; "
                        "HttpOnly; Secure; SameSite=Strict"
                    )
                },
            )
            return
        if path == "/logout":
            self._json(
                {"ok": True},
                headers={
                    "Set-Cookie": (
                        f"{COOKIE_NAME}=; Path=/; Max-Age=0; "
                        "HttpOnly; Secure; SameSite=Strict"
                    )
                },
            )
            return
        if path != "/messages":
            self._json({"ok": False, "error": "not found"}, 404)
            return
        if not self._authenticated():
            self._json({"ok": False, "error": "authentication required"}, 401)
            return
        text = body.get("message")
        if not isinstance(text, str) or not text.strip():
            self._json({"ok": False, "error": "message is required"}, 400)
            return
        if len(text) > MAX_MESSAGE_CHARS:
            self._json({"ok": False, "error": "message is too long"}, 413)
            return
        if not self.server.inference_lock.acquire(blocking=False):
            self._json({"ok": False, "error": "Captain is already replying"}, 409)
            return
        try:
            response = self.server.engine.reply(text)
            self._json(
                {
                    "ok": True,
                    "reply": response.text,
                    "provider": response.provider,
                    "model": response.model,
                    "usage": self.server.engine.budget.status(),
                }
            )
        except SecretRejected:
            self._json({"ok": False, "error": "possible API key rejected"}, 400)
        except BudgetExceeded as error:
            self._json({"ok": False, "error": str(error)}, 429)
        except ProviderError:
            self._json(
                {
                    "ok": False,
                    "error": "model unavailable; your message remains preserved",
                },
                503,
            )
        finally:
            self.server.inference_lock.release()

    def _authenticated(self) -> bool:
        cookie = SimpleCookie(self.headers.get("Cookie", ""))
        morsel = cookie.get(COOKIE_NAME)
        return bool(morsel and self.server.auth.verify_session(morsel.value))

    def _read_json(self) -> dict:
        length_text = self.headers.get("Content-Length")
        if length_text is None:
            raise ValueError("Content-Length is required")
        try:
            length = int(length_text)
        except ValueError:
            raise ValueError("invalid Content-Length") from None
        if length < 0 or length > MAX_BODY_BYTES:
            raise ValueError("request body is too large")
        try:
            value = json.loads(self.rfile.read(length))
        except json.JSONDecodeError:
            raise ValueError("request body must be JSON") from None
        if not isinstance(value, dict):
            raise ValueError("request body must be a JSON object")
        return value

    def _json(self, payload: dict, status: int = 200, headers: dict | None = None) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args) -> None:  # noqa: A002
        pass


def build_engine() -> CaptainEngine:
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is missing")
    prompt = PROMPT_PATH.read_text(encoding="utf-8").strip()
    return CaptainEngine(
        provider=GeminiProvider(api_key),
        store=ConversationStore(DATA_DIR),
        budget=UsageBudget(DATA_DIR / "usage.json"),
        system_prompt=prompt,
        api_key_for_redaction=api_key,
    )


def main() -> int:
    try:
        auth = AuthConfig.from_environment()
        engine = build_engine()
    except (OSError, ValueError, OwnershipError) as error:
        print(f"Live Captain web service cannot start: {error}", file=sys.stderr)
        return 2
    server = ConferenceServer((HOST, PORT), Handler, engine, auth)
    print(f"Live Captain Private Conference listening on http://{HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        engine.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
