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
import os
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
    context_size_metrics,
    load_optional_text,
    load_required_text,
)
from persistence import LiveCaptainStore, PersistenceError
import pause_state

# Generated-image serving remains owned by root-console.service.  Reuse its
# trust-boundary mapper here so the Live Captain stream emits the same
# authenticated browser URL instead of leaking an unrenderable local path.
ROOT_CONSOLE_DIR = Path(__file__).resolve().parent.parent / "root-console"
if str(ROOT_CONSOLE_DIR) not in sys.path:
    sys.path.append(str(ROOT_CONSOLE_DIR))
from generated_images import map_generated_images  # noqa: E402
from claude_daemon import ClaudeDaemon  # noqa: E402

HOST = "127.0.0.1"
PORT = 4778
ROOT_DIR = Path(__file__).resolve().parent
REPO_ROOT = ROOT_DIR.parent.parent
KERNEL_PATH = ROOT_DIR / "prompts" / "captain-kernel.md"
BEARING_PATH = ROOT_DIR / "context" / "current-bearing.md"
LEDGER_PATH = ROOT_DIR / "context" / "continuity-ledger.md"
CHANNEL_PATH = ROOT_DIR / "context" / "claude-channel.md"
CHANNEL_PLACEHOLDER = "(no message from Claude right now)"
DB_PATH = REPO_ROOT / "data" / "live-captain" / "live-captain.db"
DIAGNOSTIC_LOG_PATH = REPO_ROOT / "data" / "live-captain" / "instruction-sources.log"
RECENT_MESSAGE_LIMIT = 30
STATUS_LABEL = "Live Captain — commissioning baseline"


def load_context_sources(
    kernel_path: Path = KERNEL_PATH,
    bearing_path: Path = BEARING_PATH,
    ledger_path: Path = LEDGER_PATH,
    channel_path: Path = CHANNEL_PATH,
) -> dict[str, str]:
    """Load one internally consistent context-source set.

    Context documents are deliberately editable operating state. Reloading
    them for each turn lets the Captain improve that state without requiring a
    service restart; validation still fails closed before a turn is recorded.
    The Claude channel is the one exception -- it is allowed to be silent, so
    it loads optionally rather than failing closed.
    """
    kernel_text, kernel_digest = load_required_text(kernel_path, "Captain kernel")
    bearing_text, bearing_digest = load_required_text(bearing_path, "Current bearing")
    ledger_text, ledger_digest = load_required_text(ledger_path, "Continuity ledger")
    channel_text, channel_digest = load_optional_text(channel_path, CHANNEL_PLACEHOLDER)
    return {
        "kernel_text": kernel_text,
        "kernel_digest": kernel_digest,
        "bearing_text": bearing_text,
        "bearing_digest": bearing_digest,
        "ledger_text": ledger_text,
        "ledger_digest": ledger_digest,
        "channel_text": channel_text,
        "channel_digest": channel_digest,
    }


def browser_sse_payload(event: dict) -> bytes:
    """Encode a daemon event only after applying browser trust-boundary maps."""
    return f"data: {json.dumps(map_generated_images(event))}\n\n".encode("utf-8")


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
    ledger_text: str
    ledger_digest: str

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
                self.wfile.write(browser_sse_payload(event))
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
                    **{f"pause_{k}" if k != "paused" else k: v
                       for k, v in pause_state.read().items()},
                    "codex": self.daemon.status(),
                    "kernel_path": str(KERNEL_PATH),
                    "kernel_digest": self.kernel_digest,
                    "bearing_path": str(BEARING_PATH),
                    "bearing_digest": self.bearing_digest,
                    "ledger_path": str(LEDGER_PATH),
                    "ledger_digest": self.ledger_digest,
                    "channel_path": str(CHANNEL_PATH),
                    "channel_digest": self.channel_digest,
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

        # Refuse *new* turns while paused. Nothing is recorded, no context is
        # compiled, no model is called — continuity is left exactly as it was.
        if pause_state.is_paused():
            self._send_json(pause_state.refusal(), status=409)
            return

        try:
            sources = load_context_sources()
        except ContextCompilerError as exc:
            self._send_json({"error": str(exc)}, status=500)
            return

        # Publish the newly validated set for status inspection and use the
        # same local set throughout this turn.
        handler = type(self)
        for name, value in sources.items():
            setattr(handler, name, value)

        turn_started = time.monotonic()
        messages, omitted = self.store.load_recent_messages(RECENT_MESSAGE_LIMIT)
        try:
            compiled = compile_live_captain_context(
                sources["kernel_text"],
                sources["bearing_text"],
                sources["ledger_text"],
                messages,
                text,
                omitted,
                sources["channel_text"],
            )
        except ContextCompilerError as exc:
            self._send_json({"error": str(exc)}, status=500)
            return
        context_metrics = context_size_metrics(
            sources["kernel_text"], sources["bearing_text"], sources["ledger_text"],
            messages, text, compiled,
        )
        context_assembly_ms = round((time.monotonic() - turn_started) * 1000, 3)

        try:
            self.store.record_message(
                "admiral",
                text,
                sources["kernel_digest"],
                sources["bearing_digest"],
                sources["ledger_digest"],
            )
        except PersistenceError as exc:
            self._send_json({"error": f"persistence failure: {exc}"}, status=500)
            return

        inference_started = time.monotonic()
        try:
            result = self.daemon.send_and_wait(compiled)
        except (CodexError, ValueError) as exc:
            failed_inference_ms = round((time.monotonic() - inference_started) * 1000, 3)
            log_diagnostic(
                {
                    "ts": time.time(),
                    "session_id": self.store.session_id,
                    "kernel_digest": sources["kernel_digest"],
                    "bearing_digest": sources["bearing_digest"],
                    "ledger_digest": sources["ledger_digest"],
                    "recent_message_count": len(messages),
                    "omitted_older_messages": omitted,
                    "context_metrics": context_metrics,
                    "context_assembly_ms": context_assembly_ms,
                    "failed_inference_ms": failed_inference_ms,
                    "turn_error": str(exc),
                }
            )
            self._send_json({"error": str(exc)}, status=502)
            return
        inference_ms = round((time.monotonic() - inference_started) * 1000, 3)

        try:
            self.store.record_message(
                "captain",
                result["text"],
                sources["kernel_digest"],
                sources["bearing_digest"],
                sources["ledger_digest"],
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
                    "kernel_digest": sources["kernel_digest"],
                    "bearing_digest": sources["bearing_digest"],
                    "ledger_digest": sources["ledger_digest"],
                    "recent_message_count": len(messages),
                    "omitted_older_messages": omitted,
                    "context_metrics": context_metrics,
                    "context_assembly_ms": context_assembly_ms,
                    "inference_ms": inference_ms,
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
                "kernel_digest": sources["kernel_digest"],
                "bearing_digest": sources["bearing_digest"],
                "ledger_digest": sources["ledger_digest"],
                "recent_message_count": len(messages),
                "omitted_older_messages": omitted,
                "context_metrics": context_metrics,
                "context_assembly_ms": context_assembly_ms,
                "inference_ms": inference_ms,
            }
        )
        self._send_json({"text": result["text"], "thread_id": result["thread_id"]})


def main() -> None:
    sources = load_context_sources()
    store = LiveCaptainStore(DB_PATH)
    backend = os.environ.get("CAPTAIN_BACKEND", "claude")
    daemon = ClaudeDaemon(cwd=REPO_ROOT) if backend == "claude" else CodexDaemon(cwd=REPO_ROOT)

    LiveCaptainHandler.daemon = daemon
    LiveCaptainHandler.store = store
    LiveCaptainHandler.auth = AuthConfig.from_environment()
    for name, value in sources.items():
        setattr(LiveCaptainHandler, name, value)

    server = ThreadingHTTPServer((HOST, PORT), LiveCaptainHandler)
    print(
        f"Live Captain listening on http://{HOST}:{PORT} "
        f"(kernel={sources['kernel_digest'][:12]} "
        f"bearing={sources['bearing_digest'][:12]} "
        f"ledger={sources['ledger_digest'][:12]})"
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        daemon.close()
        store.close()


if __name__ == "__main__":
    main()
