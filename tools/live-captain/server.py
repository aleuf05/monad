"""Live Captain bootstrap API server.

Handles only the conversational surface (packet
LIVE-CAPTAIN-MINIMUM-CONTEXT-BOOTSTRAP-0.1, sections 8-12): GET /api/stream
(SSE), POST /api/turn, GET /api/status. Login, handoffs, research, and
generated-image serving remain on root-console.service unchanged -- none
of that is legacy Chat Captain, and duplicating it here would be exactly
the "ghost system" the packet warns against. Auth reuses root-console's
signed session cookie (same AuthConfig, same environment secrets), so the
existing login flow keeps working unmodified for both services.
"""

from __future__ import annotations

import json
import queue
import sys
import time
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from auth import COOKIE_NAME, AuthConfig
from codex_daemon import CodexDaemon, CodexError
from context_compiler import (
    ContextCompilerError,
    compile_live_captain_context,
    load_required_text,
)
from persistence import LiveCaptainStore, PersistenceError

HOST = "127.0.0.1"
PORT = 4778
ROOT_DIR = Path(__file__).resolve().parent
REPO_ROOT = ROOT_DIR.parent.parent
KERNEL_PATH = ROOT_DIR / "prompts" / "captain-kernel.md"
BEARING_PATH = ROOT_DIR / "context" / "current-bearing.md"
DB_PATH = REPO_ROOT / "data" / "live-captain" / "live-captain.db"
DIAGNOSTIC_LOG_PATH = REPO_ROOT / "data" / "live-captain" / "instruction-sources.log"
RECENT_MESSAGE_LIMIT = 30
STATUS_LABEL = "Live Captain — commissioning baseline"


def log_diagnostic(record: dict) -> None:
    """Packet section 11: capture instruction sources and turn metadata to
    a concise local diagnostic log, never exposed publicly."""
    DIAGNOSTIC_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DIAGNOSTIC_LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, default=str) + "\n")


class LiveCaptainHandler(BaseHTTPRequestHandler):
    daemon: CodexDaemon
    store: LiveCaptainStore
    auth: AuthConfig
    kernel_text: str
    kernel_digest: str
    bearing_text: str
    bearing_digest: str

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        sys.stderr.write("%s - %s\n" % (self.address_string(), format % args))

    def _authenticated(self) -> bool:
        cookie = SimpleCookie(self.headers.get("Cookie", ""))
        morsel = cookie.get(COOKIE_NAME)
        return bool(morsel and self.auth.verify_session(morsel.value))

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
        if self.path == "/api/stream":
            if not self._authenticated():
                self.send_error(401)
                return
            self._handle_stream()
        elif self.path == "/api/status":
            if not self._authenticated():
                self._send_json({"error": "authentication required"}, status=401)
                return
            messages, omitted = self.store.load_recent_messages(RECENT_MESSAGE_LIMIT)
            self._send_json(
                {
                    "label": STATUS_LABEL,
                    "codex": self.daemon.status(),
                    "kernel_path": str(KERNEL_PATH),
                    "kernel_digest": self.kernel_digest,
                    "bearing_path": str(BEARING_PATH),
                    "bearing_digest": self.bearing_digest,
                    "session_id": self.store.session_id,
                    "restart_count": self.store.restart_count(),
                    "recent_message_count": len(messages),
                    "recent_message_window": RECENT_MESSAGE_LIMIT,
                    "omitted_older_messages": omitted,
                }
            )
        else:
            self.send_error(404)

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/api/turn":
            self.send_error(404)
            return
        if not self._authenticated():
            self._send_json({"error": "authentication required"}, status=401)
            return
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            self._send_json({"error": "invalid JSON body"}, status=400)
            return
        text = payload.get("text", "")
        if not isinstance(text, str) or not text.strip():
            self._send_json({"error": "message is empty"}, status=400)
            return

        messages, omitted = self.store.load_recent_messages(RECENT_MESSAGE_LIMIT)
        try:
            compiled = compile_live_captain_context(
                self.kernel_text, self.bearing_text, messages, text, omitted
            )
        except ContextCompilerError as exc:
            self._send_json({"error": str(exc)}, status=500)
            return

        try:
            self.store.record_message("admiral", text, self.kernel_digest, self.bearing_digest)
        except PersistenceError as exc:
            self._send_json({"error": f"persistence failure: {exc}"}, status=500)
            return

        try:
            result = self.daemon.send_and_wait(compiled)
        except (CodexError, ValueError) as exc:
            self._send_json({"error": str(exc)}, status=502)
            return

        try:
            self.store.record_message(
                "captain", result["text"], self.kernel_digest, self.bearing_digest
            )
        except PersistenceError as exc:
            # The Codex reply already happened; a persistence failure here
            # must be reported, not hidden behind a fabricated success.
            self._send_json(
                {
                    "text": result["text"],
                    "warning": f"reply persisted with error: {exc}",
                },
                status=200,
            )
            log_diagnostic(
                {
                    "ts": time.time(),
                    "session_id": self.store.session_id,
                    "thread_id": result["thread_id"],
                    "sandbox": result["sandbox"],
                    "approval_policy": result["approval_policy"],
                    "thread_start_result": result["thread_start_result"],
                    "kernel_digest": self.kernel_digest,
                    "bearing_digest": self.bearing_digest,
                    "recent_message_count": len(messages),
                    "omitted_older_messages": omitted,
                    "persistence_error": str(exc),
                }
            )
            return

        log_diagnostic(
            {
                "ts": time.time(),
                "session_id": self.store.session_id,
                "thread_id": result["thread_id"],
                "sandbox": result["sandbox"],
                "approval_policy": result["approval_policy"],
                "thread_start_result": result["thread_start_result"],
                "kernel_digest": self.kernel_digest,
                "bearing_digest": self.bearing_digest,
                "recent_message_count": len(messages),
                "omitted_older_messages": omitted,
            }
        )
        self._send_json({"text": result["text"], "thread_id": result["thread_id"]})


def main() -> None:
    kernel_text, kernel_digest = load_required_text(KERNEL_PATH, "Captain kernel")
    bearing_text, bearing_digest = load_required_text(BEARING_PATH, "Current bearing")
    store = LiveCaptainStore(DB_PATH)
    daemon = CodexDaemon(cwd=REPO_ROOT)

    LiveCaptainHandler.daemon = daemon
    LiveCaptainHandler.store = store
    LiveCaptainHandler.auth = AuthConfig.from_environment()
    LiveCaptainHandler.kernel_text = kernel_text
    LiveCaptainHandler.kernel_digest = kernel_digest
    LiveCaptainHandler.bearing_text = bearing_text
    LiveCaptainHandler.bearing_digest = bearing_digest

    server = ThreadingHTTPServer((HOST, PORT), LiveCaptainHandler)
    print(f"Live Captain listening on http://{HOST}:{PORT} (kernel={kernel_digest[:12]} bearing={bearing_digest[:12]})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        daemon.close()
        store.close()


if __name__ == "__main__":
    main()
