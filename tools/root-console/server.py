"""Root Console web server.

Serves the live console UI and bridges it to the persistent CodexDaemon
(see codex_daemon.py). The daemon is created once, at process start, and
keeps running for the life of this process regardless of whether any
browser is attached -- closing every browser tab does not stop the
Captain. GET /api/stream is a Server-Sent Events feed of every live Codex
event; POST /api/turn sends new input and returns immediately, with the
reply arriving asynchronously over the SSE stream. Stdlib-only HTTP
server, matching the convention already used by tools/chat-captain.
"""

from __future__ import annotations

import json
import queue
import subprocess
import sys
import threading
import time
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from urllib.parse import parse_qs, urlsplit

from auth import COOKIE_NAME, AuthConfig, LoginLimiter
from codex_daemon import CodexDaemon, CodexError
import handoff
import research

HOST = "127.0.0.1"
PORT = 4792
ROOT_DIR = Path(__file__).resolve().parent
STATIC_DIR = ROOT_DIR / "static"
REPO_ROOT = ROOT_DIR.parent.parent
SESSION_SECONDS = 12 * 60 * 60
COMMISSIONING_TASK_ID = "CODEX-LIVE-CAPTAIN-1"
AUTHORITY_MODE = "MAXIMUM-CAPABILITY COMMISSIONING"

# The other live Monad services -- read-only visibility into the rest of
# the fleet, since a Captain that only knows about itself isn't actually
# more live than a bare Codex CLI session. (name shown in UI, systemd unit)
FLEET_UNITS = [
    ("chat-captain", "chat-captain-web.service"),
    ("live-captain", "live-captain-web.service"),
    ("living-fleet", "living-fleet.service"),
    ("fleetcore", "fleetcore-serve.service"),
    ("world-intake", "world-intake.service"),
    ("watchman", "monad-watchman.service"),
    ("public-root-auth", "public-root-auth.service"),
]


def commissioning_status(daemon: CodexDaemon) -> dict:
    """Truthful, inspectable state for the Live Captain commission."""
    inbox = handoff.ensure_inbox()
    codex_active = daemon.status()["running"]
    target_verified = REPO_ROOT == Path("/home/cgl/dev/monad") and (REPO_ROOT / ".git").exists()
    handoff_connected = inbox.is_dir() and inbox.parent.is_dir()
    return {
        "liveCaptain": "OPERATIONAL" if codex_active else "DEGRADED",
        "codexEmbodiment": "ACTIVE" if codex_active else "INACTIVE",
        "rootConsoleTarget": "VERIFIED" if target_verified else "UNVERIFIED",
        "handoffChannel": "CONNECTED" if handoff_connected else "DISCONNECTED",
        "authorityMode": AUTHORITY_MODE,
        "currentMission": COMMISSIONING_TASK_ID,
        "repository": str(REPO_ROOT),
        "handoffPath": str(inbox),
    }


def fleet_status() -> list[dict]:
    result = []
    for label, unit in FLEET_UNITS:
        try:
            proc = subprocess.run(
                ["systemctl", "is-active", unit],
                capture_output=True,
                text=True,
                timeout=3,
            )
            state = proc.stdout.strip() or "unknown"
        except (subprocess.TimeoutExpired, OSError):
            state = "unknown"
        result.append({"name": label, "unit": unit, "state": state})
    return result

def watch_handoff_inbox(daemon: CodexDaemon, poll_seconds: float = 2.0) -> None:
    """Background loop broadcasting CAPTAIN_HANDOFF_AVAILABLE over the
    existing SSE stream whenever a new handoff file appears -- handoffs are
    written by agent processes independent of this server (a Claude or
    Codex CLI session running anywhere), so this server can only learn about
    them by watching the shared inbox directory, not via a direct call."""
    inbox = handoff.ensure_inbox()
    seen = {p.name for p in inbox.glob("*_handoff.md")}
    while True:
        time.sleep(poll_seconds)
        try:
            current = {p.name for p in inbox.glob("*_handoff.md")}
        except OSError:
            continue
        for name in sorted(current - seen):
            try:
                summary = next(item for item in handoff.list_handoffs() if item["file"] == name)
            except StopIteration:
                continue
            daemon.broadcast(
                {
                    "type": "captain_handoff_available",
                    "eventType": "CAPTAIN_HANDOFF_AVAILABLE",
                    "taskId": summary["taskId"],
                    "agent": summary["agent"],
                    "handoffPath": summary["path"],
                    "repository": summary["repository"],
                    "branch": summary["branch"],
                    "publicationState": summary["publicationState"],
                    "createdAt": time.time(),
                }
            )
        seen = current


STATIC_CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
}


class RootConsoleHandler(BaseHTTPRequestHandler):
    daemon: CodexDaemon
    auth: AuthConfig
    login_limiter: LoginLimiter

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        sys.stderr.write("%s - %s\n" % (self.address_string(), format % args))

    def _authenticated(self) -> bool:
        cookie = SimpleCookie(self.headers.get("Cookie", ""))
        morsel = cookie.get(COOKIE_NAME)
        return bool(morsel and self.auth.verify_session(morsel.value))

    def _serve_static(self, relative_path: str) -> None:
        candidate = (STATIC_DIR / relative_path).resolve()
        if STATIC_DIR not in candidate.parents and candidate != STATIC_DIR:
            self.send_error(404)
            return
        if not candidate.is_file():
            self.send_error(404)
            return
        content_type = STATIC_CONTENT_TYPES.get(candidate.suffix, "application/octet-stream")
        body = candidate.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        # Never let the browser cache these -- this file gets rewritten
        # frequently during active work and a stale cached copy has caused
        # real confusion (old UI appearing to still be there after a fix).
        self.send_header("Cache-Control", "no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle_stream(self) -> None:
        listener = self.daemon.subscribe()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        try:
            while True:
                try:
                    event = listener.get(timeout=15)
                except queue.Empty:
                    self.wfile.write(b": keepalive\n\n")
                    self.wfile.flush()
                    continue
                self.wfile.write(f"data: {json.dumps(event)}\n\n".encode("utf-8"))
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            self.daemon.unsubscribe(listener)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlsplit(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        # index.html/app.js load unauthenticated -- they contain the login
        # form itself, shown when /api/status/stream come back 401.
        if path == "/":
            self._serve_static("index.html")
        elif path.startswith("/static/"):
            self._serve_static(path[len("/static/"):])
        elif path == "/api/stream":
            if not self._authenticated():
                self.send_error(401)
                return
            self._handle_stream()
        elif path == "/api/status":
            if not self._authenticated():
                self._send_json({"error": "authentication required"}, status=401)
                return
            status = self.daemon.status()
            status["commissioning"] = commissioning_status(self.daemon)
            self._send_json(status)
        elif path == "/api/fleet":
            if not self._authenticated():
                self._send_json({"error": "authentication required"}, status=401)
                return
            self._send_json({"fleet": fleet_status()})
        elif path == "/api/handoffs":
            if not self._authenticated():
                self._send_json({"error": "authentication required"}, status=401)
                return
            self._send_json({"handoffs": handoff.list_handoffs()})
        elif path == "/api/handoffs/detail":
            if not self._authenticated():
                self._send_json({"error": "authentication required"}, status=401)
                return
            filename = (query.get("file") or [""])[0]
            try:
                content = handoff.read_handoff(filename)
            except handoff.HandoffError as exc:
                self._send_json({"error": str(exc)}, status=404)
                return
            self._send_json({"file": filename, "content": content})
        elif path == "/api/research/packets":
            if not self._authenticated():
                self._send_json({"error": "authentication required"}, status=401)
                return
            self._send_json(research.list_packets())
        elif path == "/api/research/arc":
            if not self._authenticated():
                self._send_json({"error": "authentication required"}, status=401)
                return
            arc_id = (query.get("id") or [""])[0]
            try:
                self._send_json(research.get_arc(arc_id))
            except research.ResearchError as exc:
                self._send_json({"error": str(exc)}, status=404)
        elif path == "/api/research/events":
            if not self._authenticated():
                self._send_json({"error": "authentication required"}, status=401)
                return
            arc_id = (query.get("id") or [""])[0]
            try:
                self._send_json({"events": research.get_events(arc_id)})
            except research.ResearchError as exc:
                self._send_json({"error": str(exc)}, status=404)
        elif path == "/api/research/replay":
            if not self._authenticated():
                self._send_json({"error": "authentication required"}, status=401)
                return
            arc_id = (query.get("id") or [""])[0]
            try:
                self._send_json({"events": research.get_replay(arc_id)})
            except research.ResearchError as exc:
                self._send_json({"error": str(exc)}, status=400)
        else:
            self.send_error(404)

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            self._send_json({"error": "invalid JSON body"}, status=400)
            return

        if self.path == "/api/login":
            if not self.login_limiter.allow():
                self._send_json({"error": "login temporarily limited"}, status=429)
                return
            password = payload.get("password")
            if not isinstance(password, str) or not self.auth.verify_password(password):
                self._send_json({"error": "invalid credentials"}, status=401)
                return
            token = self.auth.issue_session()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            # Secure only when the original client connection was actually
            # HTTPS (Caddy sets X-Forwarded-Proto on its public route).
            # This service is reached three ways: public HTTPS via Caddy,
            # plain-HTTP LAN via Caddy, and plain-HTTP loopback directly --
            # unconditionally forcing Secure would silently break login on
            # the latter two, which are real, currently-used paths.
            secure_flag = "; Secure" if self.headers.get("X-Forwarded-Proto") == "https" else ""
            self.send_header(
                "Set-Cookie",
                f"{COOKIE_NAME}={token}; Path=/; Max-Age={SESSION_SECONDS}; HttpOnly; SameSite=Strict{secure_flag}",
            )
            body = json.dumps({"ok": True}).encode("utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if self.path == "/api/logout":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header(
                "Set-Cookie", f"{COOKIE_NAME}=; Path=/; Max-Age=0; HttpOnly; SameSite=Strict"
            )
            body = json.dumps({"ok": True}).encode("utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if self.path == "/api/research/command":
            if not self._authenticated():
                self._send_json({"error": "authentication required"}, status=401)
                return
            arc_id = payload.get("arcId", "")
            command = payload.get("command", "")
            try:
                result = research.run_command(arc_id, command)
            except research.ResearchError as exc:
                self._send_json({"error": str(exc)}, status=400)
                return
            self._send_json(result)
            return

        if self.path != "/api/turn":
            self.send_error(404)
            return
        if not self._authenticated():
            self._send_json({"error": "authentication required"}, status=401)
            return
        text = payload.get("text", "")
        try:
            thread_id = self.daemon.send_turn(text)
        except ValueError as exc:
            self._send_json({"error": str(exc)}, status=400)
            return
        except CodexError as exc:
            self._send_json({"error": str(exc)}, status=502)
            return
        self._send_json({"thread_id": thread_id}, status=202)


def main() -> None:
    daemon = CodexDaemon(cwd=REPO_ROOT)
    RootConsoleHandler.daemon = daemon
    RootConsoleHandler.auth = AuthConfig.from_environment()
    RootConsoleHandler.login_limiter = LoginLimiter()
    threading.Thread(
        target=watch_handoff_inbox, args=(daemon,), daemon=True, name="handoff-inbox-watcher"
    ).start()
    server = ThreadingHTTPServer((HOST, PORT), RootConsoleHandler)
    print(f"Root Console listening on http://{HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        daemon.close()


if __name__ == "__main__":
    main()
