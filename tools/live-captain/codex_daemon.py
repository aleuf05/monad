"""Persistent Codex app-server daemon for the Live Captain bootstrap.

Transport adapted from tools/root-console/codex_daemon.py (the JSON-RPC-
over-stdio plumbing: _send/_request/_read, subscribe/broadcast) combined
with tools/chat-captain/codex_provider.py's synchronous completion-waiting
pattern (item/completed agentMessage + turn/completed). Neither module's
mode system, context compiler, prompt, or capability partitions are
imported -- only this small, well-understood transport shape.

Every turn starts a fresh ephemeral Codex thread (no server-side thread
continuity). Conversational continuity is manufactured explicitly by the
caller: context_compiler.py assembles kernel + bearing + recent messages
+ current message into one text block, which becomes the entire turn
input. This keeps the compiler, not Codex's own thread state, as the
single place continuity is decided -- see current-bearing.md's governing
design.
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
TURN_TIMEOUT_SECONDS = 180
# Packet LIVE-CAPTAIN-MINIMUM-CONTEXT-BOOTSTRAP-0.1 section 9: workspace-write,
# never. Deliberately narrower than root-console.service's danger-full-access
# -- same unattended posture (approvalPolicy never is required: this is a
# headless daemon with no human attached to answer an approval prompt, so any
# other policy would simply hang on the first sandboxed action), but scoped
# to this repository instead of the whole filesystem.
EXECUTION_SANDBOX = "workspace-write"
APPROVAL_POLICY = "never"
SUBSCRIBER_QUEUE_SIZE = 512
CHILD_EXIT_CODE = 70


class CodexError(RuntimeError):
    pass


class CodexDaemon:
    """Owns one persistent `codex app-server` process and fans out its
    live event stream to any number of subscribers, plus a synchronous
    send_and_wait() for callers that need the completed reply text."""

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
        self._responses_lock = threading.Lock()
        self._counter = 0
        self._counter_lock = threading.Lock()
        self._subscribers: list[queue.Queue] = []
        self._subscribers_lock = threading.Lock()
        self._turn_lock = threading.Lock()
        self._active_thread_id: str | None = None
        self._started_at = time.time()
        self._closing = False
        self.last_thread_start_result: dict = {}
        self.last_initialize_result: dict = {}
        threading.Thread(target=self._read, daemon=True, name="live-captain-codex-reader").start()
        self.last_initialize_result = self._request(
            "initialize",
            {
                "clientInfo": {
                    "name": "monad_live_captain",
                    "title": "Monad Live Captain",
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
        with self._responses_lock:
            self._responses[request_id] = response_queue
        self._send({"method": method, "id": request_id, "params": params})
        try:
            response = response_queue.get(timeout=timeout)
        except queue.Empty:
            raise CodexError(f"Codex {method} timed out") from None
        finally:
            with self._responses_lock:
                self._responses.pop(request_id, None)
        if "error" in response:
            detail = response["error"].get("message", "unknown error")
            raise CodexError(f"Codex {method} failed: {detail}")
        return response.get("result", {})

    def _broadcast(self, event: dict) -> None:
        with self._subscribers_lock:
            subscribers = list(self._subscribers)
        for subscriber in subscribers:
            try:
                subscriber.put_nowait(event)
            except queue.Full:
                try:
                    subscriber.get_nowait()
                except queue.Empty:
                    pass
                try:
                    subscriber.put_nowait(event)
                except queue.Full:
                    pass

    def broadcast(self, event: dict) -> None:
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
            with self._responses_lock:
                response_queue = self._responses.get(request_id)
            if response_queue is not None:
                response_queue.put(message)
            elif message.get("method"):
                self._broadcast(
                    {
                        "type": "codex_event",
                        "method": message["method"],
                        "params": message.get("params", {}),
                        "ts": time.time(),
                    }
                )
        if not self._closing:
            os._exit(CHILD_EXIT_CODE)

    def subscribe(self) -> "queue.Queue[dict]":
        listener: "queue.Queue[dict]" = queue.Queue(maxsize=SUBSCRIBER_QUEUE_SIZE)
        with self._subscribers_lock:
            self._subscribers.append(listener)
        return listener

    def unsubscribe(self, listener: "queue.Queue[dict]") -> None:
        with self._subscribers_lock:
            if listener in self._subscribers:
                self._subscribers.remove(listener)

    def send_and_wait(
        self, compiled_text: str, sandbox: str = EXECUTION_SANDBOX, timeout: int = TURN_TIMEOUT_SECONDS
    ) -> dict:
        """Start one ephemeral turn with compiled_text as its entire input,
        wait for the completed agentMessage, and return the reply plus
        enough metadata to answer the instruction-source questions in
        packet section 11. Also broadcasts every live event so an attached
        SSE viewer sees the same stream root-console.service's UI does."""
        compiled_text = compiled_text.strip()
        if not compiled_text:
            raise ValueError("compiled context is empty")
        listener = self.subscribe()
        try:
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
                self.last_thread_start_result = started
                thread_id = started["thread"]["id"]
                self._active_thread_id = thread_id
                self._broadcast(
                    {
                        "type": "turn_started",
                        "thread_id": thread_id,
                        "text": compiled_text,
                        "ts": time.time(),
                    }
                )
                self._request(
                    "turn/start",
                    {
                        "threadId": thread_id,
                        "cwd": str(self.cwd),
                        "input": [{"type": "text", "text": compiled_text}],
                    },
                )
                final_text: str | None = None
                tool_events: list[dict] = []
                deadline = time.time() + timeout
                while True:
                    remaining = deadline - time.time()
                    if remaining <= 0:
                        raise CodexError("Codex turn timed out")
                    try:
                        event = listener.get(timeout=remaining)
                    except queue.Empty:
                        raise CodexError("Codex turn timed out") from None
                    if event.get("type") != "codex_event":
                        continue
                    method = event.get("method", "")
                    params = event.get("params", {})
                    if params.get("threadId") not in {None, thread_id}:
                        continue
                    if method == "item/completed":
                        item = params.get("item", {})
                        if item.get("type") == "agentMessage":
                            final_text = item.get("text")
                        else:
                            tool_events.append(item)
                    elif method == "turn/completed":
                        status = params.get("turn", {}).get("status", "completed")
                        if status not in {"completed", "success"}:
                            raise CodexError(f"Codex turn ended with status {status}")
                        break
        finally:
            self.unsubscribe(listener)
        if not final_text or not final_text.strip():
            raise CodexError("Codex returned no reply")
        return {
            "text": final_text.strip(),
            "thread_id": thread_id,
            "sandbox": sandbox,
            "approval_policy": APPROVAL_POLICY,
            "tool_events": tool_events,
            "thread_start_result": started,
        }

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
        self._closing = True
        if self._process.poll() is None:
            self._process.terminate()
