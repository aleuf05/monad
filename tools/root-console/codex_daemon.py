"""Persistent Codex app-server daemon for the Root Console.

The app-server subprocess is started once, when this daemon is constructed,
and lives for the life of the process -- independent of whether any web UI
is attached. Every JSON-RPC notification it emits (item/started,
item/completed, turn/completed, etc.) is broadcast live to all current
subscribers via CodexDaemon.subscribe(), instead of being drained and
discarded internally the way tools/chat-captain/codex_provider.py's
generate() does. The JSON-RPC-over-stdio transport (_send/_request/_read)
is carried over from that module; send_turn() replaces generate() and
returns as soon as the turn has started, since the reply and every
intermediate event arrive asynchronously through subscribe() instead of
being returned as one blocking call.
"""

from __future__ import annotations

import json
import os
import queue
import subprocess
import threading
import time
from pathlib import Path

CODEX_BIN = os.environ.get("CODEX_BIN", "/home/cgl/.local/bin/codex")
INIT_TIMEOUT_SECONDS = 30
EXECUTION_SANDBOX = "danger-full-access"
APPROVAL_POLICY = "never"


class CodexError(RuntimeError):
    pass


class CodexDaemon:
    """Owns one persistent `codex app-server` process and fans out its
    live event stream to any number of subscribers."""

    def __init__(self, cwd: Path):
        self.cwd = cwd
        self._process = subprocess.Popen(
            [CODEX_BIN, "app-server"],
            cwd=cwd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )
        self._responses: dict[int, queue.Queue] = {}
        self._counter = 0
        self._counter_lock = threading.Lock()
        self._subscribers: list[queue.Queue] = []
        self._subscribers_lock = threading.Lock()
        self._turn_lock = threading.Lock()
        self._active_thread_id: str | None = None
        self._started_at = time.time()
        threading.Thread(target=self._read, daemon=True, name="codex-app-server-reader").start()
        self._request(
            "initialize",
            {
                "clientInfo": {
                    "name": "monad_root_console",
                    "title": "Monad Root Console",
                    "version": "0.1.0",
                }
            },
            timeout=INIT_TIMEOUT_SECONDS,
        )
        self._send({"method": "initialized", "params": {}})

    def _send(self, message: dict) -> None:
        if self._process.poll() is not None or not self._process.stdin:
            raise CodexError("Codex app-server is not running")
        self._process.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
        self._process.stdin.flush()

    def _next_id(self) -> int:
        with self._counter_lock:
            self._counter += 1
            return self._counter

    def _request(self, method: str, params: dict, timeout: int = 30) -> dict:
        request_id = self._next_id()
        response_queue: queue.Queue = queue.Queue(maxsize=1)
        self._responses[request_id] = response_queue
        self._send({"method": method, "id": request_id, "params": params})
        try:
            response = response_queue.get(timeout=timeout)
        except queue.Empty:
            raise CodexError(f"Codex {method} timed out") from None
        finally:
            self._responses.pop(request_id, None)
        if "error" in response:
            detail = response["error"].get("message", "unknown error")
            raise CodexError(f"Codex {method} failed: {detail}")
        return response.get("result", {})

    def _broadcast(self, event: dict) -> None:
        with self._subscribers_lock:
            subscribers = list(self._subscribers)
        for subscriber in subscribers:
            subscriber.put(event)

    def broadcast(self, event: dict) -> None:
        """Public entry point for external sources (e.g. the handoff inbox
        watcher) to push an event onto the same SSE stream as live Codex
        events, instead of standing up a second event system."""
        self._broadcast(event)

    def _read(self) -> None:
        if not self._process.stdout:
            return
        for line in self._process.stdout:
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                continue
            request_id = message.get("id")
            if request_id is not None and request_id in self._responses:
                self._responses[request_id].put(message)
            elif message.get("method"):
                self._broadcast(
                    {
                        "type": "codex_event",
                        "method": message["method"],
                        "params": message.get("params", {}),
                        "ts": time.time(),
                    }
                )

    def subscribe(self) -> "queue.Queue[dict]":
        listener: "queue.Queue[dict]" = queue.Queue()
        with self._subscribers_lock:
            self._subscribers.append(listener)
        return listener

    def unsubscribe(self, listener: "queue.Queue[dict]") -> None:
        with self._subscribers_lock:
            if listener in self._subscribers:
                self._subscribers.remove(listener)

    def send_turn(self, text: str, sandbox: str = EXECUTION_SANDBOX) -> str:
        """Start a new turn and return its thread id immediately. The
        reply and every intermediate event arrive asynchronously through
        subscribe(), not as a return value of this call."""
        text = text.strip()
        if not text:
            raise ValueError("message is empty")
        with self._turn_lock:
            started = self._request(
                "thread/start",
                {
                    "cwd": str(self.cwd),
                    "sandbox": sandbox,
                    "approvalPolicy": APPROVAL_POLICY,
                    "ephemeral": True,
                },
            )
            thread_id = started["thread"]["id"]
            self._active_thread_id = thread_id
            self._broadcast(
                {"type": "turn_started", "thread_id": thread_id, "text": text, "ts": time.time()}
            )
            self._request(
                "turn/start",
                {
                    "threadId": thread_id,
                    "cwd": str(self.cwd),
                    "input": [{"type": "text", "text": text}],
                },
            )
        return thread_id

    def status(self) -> dict:
        return {
            "running": self._process.poll() is None,
            "pid": self._process.pid,
            "active_thread_id": self._active_thread_id,
            "subscriber_count": len(self._subscribers),
            "uptime_seconds": time.time() - self._started_at,
            "execution_sandbox": EXECUTION_SANDBOX,
            "approval_policy": APPROVAL_POLICY,
        }

    def close(self) -> None:
        if self._process.poll() is None:
            self._process.terminate()
