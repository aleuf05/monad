"""Persistent Claude Code CLI daemon -- same role as codex_daemon.py's
CodexDaemon, swappable via the CAPTAIN_BACKEND env var so root-console and
live-captain can run on either backend without any frontend change.

`claude -p --input-format stream-json --output-format stream-json` holds one
long-lived process across many turns (proven live: a second turn recalled
context from the first, same session_id both times), so this mirrors
CodexDaemon's architecture -- one persistent subprocess, a background reader
thread that parses each stdout line and rebroadcasts it as the same
`codex_event` envelope shape console/assets/js/root-console.js already
renders (item/started, item/agentMessage/delta, item/completed,
turn/completed, thread/tokenUsage/updated). Claude's stream-json schema
(stream_event/assistant/user/result) is translated into that shape rather
than teaching the frontend a second vocabulary.
"""

from __future__ import annotations

import json
import os
import queue
import subprocess
import threading
import time
import uuid
from pathlib import Path

CLAUDE_BIN = os.environ.get("CLAUDE_BIN", "/home/cgl/.local/bin/claude")
CLAUDE_MODEL = os.environ.get("CAPTAIN_CLAUDE_MODEL", "sonnet")
SUBSCRIBER_QUEUE_SIZE = 512
CHILD_EXIT_CODE = 70


class CodexError(RuntimeError):
    """Same name as codex_daemon.CodexError so callers can catch one type
    regardless of which backend is active."""


class ClaudeDaemon:
    """Owns one persistent `claude -p --input-format stream-json` process
    and fans out its translated event stream to any number of subscribers.
    Public interface matches codex_daemon.CodexDaemon exactly."""

    def __init__(self, cwd: Path):
        self.cwd = cwd
        self._process = subprocess.Popen(
            [
                CLAUDE_BIN,
                "-p",
                "--input-format", "stream-json",
                "--output-format", "stream-json",
                "--include-partial-messages",
                "--permission-mode", "bypassPermissions",
                "--model", CLAUDE_MODEL,
                "--verbose",
            ],
            cwd=cwd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )
        self._subscribers: list[queue.Queue] = []
        self._subscribers_lock = threading.Lock()
        self._turn_lock = threading.Lock()
        self._active_thread_id: str | None = None
        self._pending_tools: dict[str, dict] = {}
        self._started_at = time.time()
        self._closing = False
        threading.Thread(target=self._read, daemon=True, name="claude-reader").start()

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

    def subscribe(self) -> "queue.Queue[dict]":
        listener: "queue.Queue[dict]" = queue.Queue(maxsize=SUBSCRIBER_QUEUE_SIZE)
        with self._subscribers_lock:
            self._subscribers.append(listener)
        return listener

    def unsubscribe(self, listener: "queue.Queue[dict]") -> None:
        with self._subscribers_lock:
            if listener in self._subscribers:
                self._subscribers.remove(listener)

    def _codex_event(self, method: str, params: dict) -> None:
        self._broadcast({"type": "codex_event", "method": method, "params": params, "ts": time.time()})

    def _item_completed(self, item: dict) -> None:
        self._codex_event("item/completed", {"item": item})

    def _write_turn(self, text: str) -> str:
        """Caller must hold self._turn_lock. Writes one user message to the
        persistent Claude process and returns its thread_id."""
        if self._process.poll() is not None or not self._process.stdin:
            raise CodexError("Claude process is not running")
        thread_id = self._active_thread_id or str(uuid.uuid4())
        self._active_thread_id = thread_id
        self._broadcast({"type": "turn_started", "thread_id": thread_id, "text": text, "ts": time.time()})
        self._codex_event("turn/started", {"threadId": thread_id})
        line = json.dumps(
            {"type": "user", "message": {"role": "user", "content": [{"type": "text", "text": text}]}}
        )
        self._process.stdin.write(line + "\n")
        self._process.stdin.flush()
        return thread_id

    def send_turn(self, text: str, sandbox: str | None = None) -> str:
        """Start a new turn and return immediately; the reply and every
        intermediate event arrive asynchronously through subscribe().
        Matches codex_daemon.CodexDaemon.send_turn (root-console's async
        streaming caller)."""
        text = text.strip()
        if not text:
            raise ValueError("message is empty")
        with self._turn_lock:
            return self._write_turn(text)

    def send_and_wait(self, compiled_text: str, sandbox: str | None = None, timeout: int = 180) -> dict:
        """Start one turn and block until it completes, returning the reply
        text plus tool_events. Matches tools/live-captain/codex_daemon.py's
        CodexDaemon.send_and_wait (live-captain's synchronous caller)."""
        compiled_text = compiled_text.strip()
        if not compiled_text:
            raise ValueError("compiled context is empty")
        # Subscribe only after acquiring the turn lock, and only right before
        # writing this call's own turn. Subscribing earlier lets a waiting
        # caller's queue silently accumulate broadcasts from whichever turn
        # is currently holding the lock; when that caller's own turn starts,
        # it then drains those stale queued events first and returns another
        # caller's reply as its own (confirmed live under the concurrency
        # stress test: three near-simultaneous /api/turn calls produced three
        # persisted Captain replies with identical text and sub-10ms gaps,
        # incompatible with three real inferences).
        try:
            with self._turn_lock:
                listener = self.subscribe()
                thread_id = self._write_turn(compiled_text)
                final_text: str | None = None
                tool_events: list[dict] = []
                deadline = time.time() + timeout
                while True:
                    remaining = deadline - time.time()
                    if remaining <= 0:
                        raise CodexError("Claude turn timed out")
                    try:
                        event = listener.get(timeout=remaining)
                    except queue.Empty:
                        raise CodexError("Claude turn timed out") from None
                    if event.get("type") != "codex_event":
                        continue
                    method = event.get("method", "")
                    params = event.get("params", {})
                    if method == "item/completed":
                        item = params.get("item", {})
                        if item.get("type") == "agentMessage":
                            final_text = item.get("text")
                        else:
                            tool_events.append(item)
                    elif method == "turn/completed":
                        status = params.get("turn", {}).get("status", "completed")
                        if status not in {"completed", "success"}:
                            error = params.get("turn", {}).get("error", {})
                            raise CodexError(f"Claude turn ended with status {status}: {error.get('message', '')}")
                        break
        finally:
            self.unsubscribe(listener)
        if not final_text or not final_text.strip():
            raise CodexError("Claude returned no reply")
        return {
            "text": final_text.strip(),
            "thread_id": thread_id,
            "sandbox": sandbox or "bypassPermissions",
            "approval_policy": "never",
            "tool_events": tool_events,
            "thread_start_result": {},
        }

    def _read(self) -> None:
        if not self._process.stdout:
            return
        current_text_item_id: str | None = None
        item_counter = 0
        for raw_line in self._process.stdout:
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            try:
                message = json.loads(raw_line)
            except json.JSONDecodeError:
                continue
            mtype = message.get("type")

            if mtype == "stream_event":
                event = message.get("event", {})
                etype = event.get("type")
                if etype == "content_block_start" and event.get("content_block", {}).get("type") == "text":
                    item_counter += 1
                    current_text_item_id = f"text-{item_counter}"
                elif etype == "content_block_delta":
                    delta = event.get("delta", {})
                    if delta.get("type") == "text_delta" and current_text_item_id:
                        self._codex_event(
                            "item/agentMessage/delta",
                            {"itemId": current_text_item_id, "delta": delta.get("text", "")},
                        )
                elif etype == "content_block_stop":
                    current_text_item_id = None

            elif mtype == "assistant":
                for block in (message.get("message") or {}).get("content", []):
                    btype = block.get("type")
                    if btype == "text":
                        self._item_completed(
                            {"id": f"text-{item_counter}", "type": "agentMessage", "text": block.get("text", "")}
                        )
                    elif btype == "thinking":
                        self._item_completed(
                            {"id": f"thinking-{item_counter}", "type": "reasoning", "text": block.get("thinking", "")}
                        )
                    elif btype == "tool_use":
                        tool_id = block.get("id")
                        name = block.get("name", "tool")
                        tool_input = block.get("input", {}) or {}
                        summary = (
                            tool_input.get("command")
                            or tool_input.get("file_path")
                            or tool_input.get("path")
                            or tool_input.get("pattern")
                            or ""
                        )
                        self._pending_tools[tool_id] = {"name": name, "summary": summary}
                        self._codex_event(
                            "item/started",
                            {"item": {"id": tool_id, "type": "commandExecution", "command": f"{name}: {summary}".strip(": ")}},
                        )

            elif mtype == "user":
                for block in (message.get("message") or {}).get("content", []):
                    if block.get("type") != "tool_result":
                        continue
                    tool_id = block.get("tool_use_id")
                    pending = self._pending_tools.pop(tool_id, {"name": "tool", "summary": ""})
                    content = block.get("content")
                    if isinstance(content, list):
                        content = " ".join(c.get("text", "") for c in content if isinstance(c, dict))
                    text = str(content)[:2000]
                    self._item_completed(
                        {
                            "id": tool_id,
                            "type": "commandExecution",
                            "command": f"{pending['name']}: {pending['summary']}".strip(": "),
                            "text": text,
                        }
                    )

            elif mtype == "result":
                usage = message.get("usage") or {}
                self._codex_event(
                    "thread/tokenUsage/updated",
                    {
                        "tokenUsage": {
                            "total": {
                                "inputTokens": usage.get("input_tokens", 0),
                                "outputTokens": usage.get("output_tokens", 0),
                            }
                        }
                    },
                )
                is_error = bool(message.get("is_error"))
                turn = {"status": "failed" if is_error else "completed"}
                if is_error:
                    turn["error"] = {
                        "message": message.get("result") or message.get("subtype") or "unknown error",
                        "additionalDetails": None,
                    }
                self._codex_event("turn/completed", {"threadId": self._active_thread_id, "turn": turn})
                current_text_item_id = None

        if not self._closing:
            os._exit(CHILD_EXIT_CODE)

    def status(self) -> dict:
        return {
            "running": self._process.poll() is None,
            "pid": self._process.pid,
            "active_thread_id": self._active_thread_id,
            "subscriber_count": len(self._subscribers),
            "uptime_seconds": time.time() - self._started_at,
            "execution_sandbox": "bypassPermissions",
            "approval_policy": "never",
            "backend": "claude",
            "model": CLAUDE_MODEL,
        }

    def close(self) -> None:
        self._closing = True
        if self._process.poll() is None:
            self._process.terminate()
