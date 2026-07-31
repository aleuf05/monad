#!/usr/bin/env python3
"""Authenticated loopback API for Chat Captain.

Auth block (scrypt password verifier + HMAC-signed session cookie + origin
allowlist + login rate limit + security headers) is copied wholesale from
tools/living-captain/web_service.py -- it is schema-agnostic and proven
live on this host already, just re-pointed at a distinct cookie/env prefix
and port so it runs as an independent sibling service.
"""

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
from urllib.parse import parse_qs, urlparse

import database
from codex_provider import CodexProvider
from context_compiler import load_seed_instruction
from engine import CaptainEngine, OwnershipError
from model_provider import ProviderError
from usage_budget import BudgetExceeded, UsageBudget

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "chat-captain"
PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "captain-system.md"
# The Admiral's Brief reuses the Context Steward's own compact projection
# (docs/context/current-state.json) rather than a second summarization
# path -- it is already full-access (nothing redacted) and already
# executive-level (a curated projection, not the raw doc tree), so this
# endpoint is a thin authenticated read of an existing repository artifact.
BRIEF_PATH = ROOT / "docs" / "context" / "current-state.json"
HOST = "127.0.0.1"
PORT = 4778
# Chat Captain is LAN-only by deliberate design (see docs/deployment.md's
# narrow exception to the retired web-lan/ pattern) -- never served to the
# public internet. Two Caddy paths currently reach this loopback service,
# both gated to the LAN, so both origins are accepted here:
#   1. https://cameronlampley.com/ -- same public hostname as the toy site,
#      but Caddy only proxies to this service for requests whose remote_ip
#      is on the private LAN (relies on the router's NAT hairpin behavior,
#      confirmed working 2026-07-31 -- see scripts/Caddyfile).
#   2. http://192.168.0.100:8080/ -- a dedicated LAN-IP Caddy site block,
#      kept as a fallback while (1) is being verified.
# The session cookie intentionally omits the Secure attribute so it works
# over both the plain-HTTP fallback (2) and the HTTPS primary path (1) --
# a non-Secure cookie is still accepted over HTTPS, just not restricted to it.
ALLOWED_ORIGINS = frozenset(
    origin.strip()
    for origin in os.environ.get(
        "CHAT_CAPTAIN_ALLOWED_ORIGINS",
        "https://cameronlampley.com,http://192.168.0.100:8080",
    ).split(",")
    if origin.strip()
)
COOKIE_NAME = "monad_chat_captain_session"
SESSION_SECONDS = 12 * 60 * 60
MAX_BODY_BYTES = 32_768
MAX_MESSAGE_CHARS = 6_000
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
                bytes.fromhex(os.environ["CHAT_CAPTAIN_PASSWORD_SALT"]),
                bytes.fromhex(os.environ["CHAT_CAPTAIN_PASSWORD_HASH"]),
                bytes.fromhex(os.environ["CHAT_CAPTAIN_SESSION_SECRET"]),
            )
        except (KeyError, ValueError) as error:
            raise ValueError("Chat Captain authentication is not configured") from error

    def verify_password(self, password: str) -> bool:
        candidate = hashlib.scrypt(
            password.encode("utf-8"), salt=self.salt, n=2**14, r=8, p=1, dklen=32
        )
        return hmac.compare_digest(candidate, self.password_hash)

    def issue_session(self, now: int | None = None) -> str:
        timestamp = int(time.time()) if now is None else now
        payload = f"{timestamp}.{secrets.token_hex(16)}"
        signature = hmac.new(self.session_secret, payload.encode("ascii"), hashlib.sha256).digest()
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
        signature = hmac.new(self.session_secret, payload.encode("ascii"), hashlib.sha256).digest()
        expected = base64.urlsafe_b64encode(signature).decode("ascii").rstrip("=")
        return hmac.compare_digest(expected, supplied)


class CaptainServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, handler, engine: CaptainEngine, conn, auth: AuthConfig):
        super().__init__(address, handler)
        self.engine = engine
        self.conn = conn
        self.auth = auth
        self.inference_lock = threading.Lock()
        self.login_lock = threading.Lock()
        self.login_attempts: list[float] = []

    def allow_login_attempt(self) -> bool:
        now = time.monotonic()
        with self.login_lock:
            self.login_attempts = [a for a in self.login_attempts if now - a < LOGIN_WINDOW_SECONDS]
            if len(self.login_attempts) >= LOGIN_ATTEMPTS_PER_WINDOW:
                return False
            self.login_attempts.append(now)
            return True


class Handler(BaseHTTPRequestHandler):
    server: CaptainServer

    # --- routing -----------------------------------------------------

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        query = parse_qs(urlparse(self.path).query)
        if path == "/health":
            self._json({"ok": True, "service": "chat-captain"})
            return
        if not self._authenticated():
            self._json({"ok": False, "error": "authentication required"}, 401)
            return
        if path == "/api/state":
            self._handle_get_state()
        elif path == "/api/messages":
            self._handle_get_messages(query)
        elif path == "/api/harvest":
            self._handle_get_harvest(query)
        elif path == "/api/brief":
            self._handle_get_brief()
        else:
            self._json({"ok": False, "error": "not found"}, 404)

    def do_POST(self) -> None:
        if self.headers.get("Origin") not in ALLOWED_ORIGINS:
            self._json({"ok": False, "error": "origin rejected"}, 403)
            return
        path = urlparse(self.path).path
        try:
            body = self._read_json()
        except ValueError as error:
            self._json({"ok": False, "error": str(error)}, 400)
            return

        if path == "/login":
            self._handle_login(body)
            return
        if path == "/logout":
            self._handle_logout()
            return
        if not self._authenticated():
            self._json({"ok": False, "error": "authentication required"}, 401)
            return
        if path == "/api/chat":
            self._handle_chat(body)
        elif path.startswith("/api/harvest/") and path.endswith("/accept"):
            self._handle_harvest_review(path, "accepted")
        elif path.startswith("/api/harvest/") and path.endswith("/reject"):
            self._handle_harvest_review(path, "rejected")
        elif path == "/api/mode":
            self._handle_set_mode(body)
        elif path == "/api/project":
            self._handle_set_project(body)
        elif path == "/api/session/close":
            self._handle_session_close()
        elif path == "/api/session/new":
            self._handle_session_new()
        else:
            self._json({"ok": False, "error": "not found"}, 404)

    # --- handlers ------------------------------------------------------

    def _handle_login(self, body: dict) -> None:
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
                    "HttpOnly; SameSite=Strict"
                )
            },
        )

    def _handle_logout(self) -> None:
        self._json(
            {"ok": True},
            headers={"Set-Cookie": f"{COOKIE_NAME}=; Path=/; Max-Age=0; HttpOnly; SameSite=Strict"},
        )

    def _handle_get_state(self) -> None:
        state = database.get_state(self.server.conn)
        project = database.get_project(self.server.conn, state["active_project_id"]) if state.get("active_project_id") else None
        session = database.get_session(self.server.conn, state["current_session_id"]) if state.get("current_session_id") else None
        self._json(
            {
                "ok": True,
                "state": state,
                "project": project,
                "session": session,
                "usage": self.server.engine.budget.status(),
            }
        )

    def _handle_get_messages(self, query: dict) -> None:
        session_id = (query.get("session_id") or [None])[0]
        if not session_id:
            state = database.get_state(self.server.conn)
            session_id = state.get("current_session_id")
        if not session_id:
            self._json({"ok": True, "session_id": None, "messages": []})
            return
        messages = database.list_messages(self.server.conn, session_id)
        self._json({"ok": True, "session_id": session_id, "messages": messages})

    def _handle_get_harvest(self, query: dict) -> None:
        status = (query.get("status") or [None])[0]
        items = database.list_harvest_items(self.server.conn, status=status)
        self._json({"ok": True, "items": items})

    def _handle_get_brief(self) -> None:
        try:
            raw = BRIEF_PATH.read_text(encoding="utf-8")
        except OSError:
            self._json({"ok": False, "error": "brief unavailable"}, 503)
            return
        try:
            brief = json.loads(raw)
        except json.JSONDecodeError:
            self._json({"ok": False, "error": "brief is malformed"}, 503)
            return
        self._json({"ok": True, "brief": brief})

    def _handle_chat(self, body: dict) -> None:
        text = body.get("message")
        if not isinstance(text, str) or not text.strip():
            self._json({"ok": False, "error": "message is required"}, 400)
            return
        if len(text) > MAX_MESSAGE_CHARS:
            self._json({"ok": False, "error": "message is too long"}, 413)
            return

        requested_mode = body.get("mode")
        requested_project_id = body.get("project_id")
        if isinstance(requested_mode, str) and requested_mode in database.MODES:
            state = database.get_state(self.server.conn)
            if requested_mode != state["current_mode"]:
                database.log_mode_event(
                    self.server.conn, previous_mode=state["current_mode"],
                    new_mode=requested_mode, reason="set via /api/chat", source="operator",
                )
                database.update_state(self.server.conn, current_mode=requested_mode)
        if isinstance(requested_project_id, str):
            if database.get_project(self.server.conn, requested_project_id):
                database.update_state(self.server.conn, active_project_id=requested_project_id)

        if not self.server.inference_lock.acquire(blocking=False):
            self._json({"ok": False, "error": "Captain is already replying"}, 409)
            return
        try:
            self.server.engine._ensure_open_session()
            result = self.server.engine.reply(text)
            self._json({"ok": True, **result, "state": database.get_state(self.server.conn)})
        except BudgetExceeded as error:
            self._json({"ok": False, "error": str(error)}, 429)
        except ProviderError:
            self._json({"ok": False, "error": "model unavailable; your message remains preserved"}, 503)
        finally:
            self.server.inference_lock.release()

    def _handle_harvest_review(self, path: str, status: str) -> None:
        item_id = path.split("/")[3]
        item = database.set_harvest_status(self.server.conn, item_id, status)
        if item is None:
            self._json({"ok": False, "error": "harvest item not found"}, 404)
            return
        if status == "accepted":
            database.update_state(self.server.conn, last_successful_harvest_at=database.now())
        self._json({"ok": True, "item": item})

    def _handle_set_mode(self, body: dict) -> None:
        mode = body.get("mode")
        if mode not in database.MODES:
            self._json({"ok": False, "error": "unsupported mode"}, 400)
            return
        state = database.get_state(self.server.conn)
        database.log_mode_event(
            self.server.conn, previous_mode=state["current_mode"], new_mode=mode,
            reason=body.get("reason"), source="operator",
        )
        updated = database.update_state(self.server.conn, current_mode=mode)
        self._json({"ok": True, "state": updated})

    def _handle_set_project(self, body: dict) -> None:
        project_id = body.get("project_id")
        if not project_id:
            title = body.get("title")
            if not isinstance(title, str) or not title.strip():
                self._json({"ok": False, "error": "project_id or title is required"}, 400)
                return
            project = database.create_project(self.server.conn, title=title.strip(), purpose=body.get("purpose", ""))
            project_id = project["id"]
        elif not database.get_project(self.server.conn, project_id):
            self._json({"ok": False, "error": "project not found"}, 404)
            return
        updated = database.update_state(self.server.conn, active_project_id=project_id)
        self._json({"ok": True, "state": updated, "project": database.get_project(self.server.conn, project_id)})

    def _handle_session_close(self) -> None:
        if not self.server.inference_lock.acquire(blocking=False):
            self._json({"ok": False, "error": "Captain is already replying"}, 409)
            return
        try:
            session = self.server.engine.close_session()
            self._json({"ok": True, "session": session})
        finally:
            self.server.inference_lock.release()

    def _handle_session_new(self) -> None:
        session = self.server.engine.start_session()
        self._json({"ok": True, "session": session})

    # --- plumbing --------------------------------------------------------

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
            value = json.loads(self.rfile.read(length)) if length else {}
        except json.JSONDecodeError:
            raise ValueError("request body must be JSON") from None
        if not isinstance(value, dict):
            raise ValueError("request body must be a JSON object")
        return value

    def _json(self, payload: dict, status: int = 200, headers: dict | None = None) -> None:
        body = json.dumps(payload, separators=(",", ":"), default=str).encode("utf-8")
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


def build_engine() -> tuple[CaptainEngine, object]:
    conn = database.connect(DATA_DIR / "captain.sqlite3")
    prompt = load_seed_instruction(str(PROMPT_PATH))
    provider = CodexProvider(cwd=ROOT)
    engine = CaptainEngine(
        provider=provider,
        conn=conn,
        budget=UsageBudget(DATA_DIR / "usage.json"),
        seed_instruction=prompt,
        data_dir=DATA_DIR,
    )
    return engine, conn


def main() -> int:
    try:
        auth = AuthConfig.from_environment()
        engine, conn = build_engine()
    except (OSError, ValueError, OwnershipError) as error:
        print(f"Chat Captain web service cannot start: {error}", file=sys.stderr)
        return 2
    server = CaptainServer((HOST, PORT), Handler, engine, conn, auth)
    print(f"Chat Captain listening on http://{HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        engine.close()
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
