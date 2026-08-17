"""Persistent AGY (Google Antigravity CLI) daemon.

Provides the canonical AGY adapter for Live Captain and Root Console,
matching the interface of ClaudeDaemon and CodexDaemon so Live Captain can
operate with AGY as its primary backend without any frontend or routing
divergence.

Translates AGY's stream-json event schema (init/step_update/result) into the
canonical codex_event shape rendered across Monad console surfaces
(item/started, item/agentMessage/delta, item/completed, turn/completed,
thread/tokenUsage/updated).
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
from typing import Any

AGY_BIN = os.environ.get("AGY_BIN", "/home/cgl/.local/bin/agy")
AGY_MODEL = os.environ.get("CAPTAIN_AGY_MODEL", "gemini-3.7-flash-high")
SUBSCRIBER_QUEUE_SIZE = 512
CHILD_EXIT_CODE = 70


class AgyError(RuntimeError):
    """Raised when an AGY execution or turn fails."""


class CodexError(AgyError):
    """Alias to preserve caller exception compatibility across backends."""


class AgyDaemon:
    """Owns AGY execution lifecycle and fans out translated event streams
    to any number of subscribers. Public interface matches ClaudeDaemon and
    CodexDaemon."""

    def __init__(self, cwd: Path):
        self.cwd = cwd
        self._subscribers: list[queue.Queue] = []
        self._subscribers_lock = threading.Lock()
        self._turn_lock = threading.Lock()
        self._active_thread_id: str | None = None
        self._active_source: str = "admiral"
        self._active_process: subprocess.Popen | None = None
        self._started_at = time.time()
        self._closing = False

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

    def subscribe(self) -> queue.Queue[dict]:
        listener: queue.Queue[dict] = queue.Queue(maxsize=SUBSCRIBER_QUEUE_SIZE)
        with self._subscribers_lock:
            self._subscribers.append(listener)
        return listener

    def unsubscribe(self, listener: queue.Queue[dict]) -> None:
        with self._subscribers_lock:
            if listener in self._subscribers:
                self._subscribers.remove(listener)

    def _codex_event(self, method: str, params: dict, source: str = "admiral") -> None:
        self._broadcast({
            "type": "codex_event",
            "method": method,
            "params": params,
            "source": source,
            "ts": time.time(),
        })

    def _item_completed(self, item: dict, source: str = "admiral") -> None:
        self._codex_event("item/completed", {"item": item}, source=source)

    def _build_command(self, text: str) -> list[str]:
        cmd = [
            AGY_BIN,
            "-p", text,
            "--output-format", "stream-json",
            "--dangerously-skip-permissions",
        ]
        if AGY_MODEL:
            cmd.extend(["--model", AGY_MODEL])
        return cmd

    def _run_turn_sync(
        self,
        text: str,
        thread_id: str,
        source: str,
    ) -> None:
        """Executes one AGY turn subprocess and processes stream-json events synchronously."""
        cmd = self._build_command(text)
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=self.cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
        except OSError as exc:
            self._codex_event(
                "turn/completed",
                {
                    "threadId": thread_id,
                    "turn": {
                        "status": "failed",
                        "error": {"message": f"Failed to execute AGY binary ({AGY_BIN}): {exc}", "additionalDetails": None},
                    },
                },
                source=source,
            )
            return

        self._active_process = proc
        response_received = False
        final_text: str | None = None
        turn_completed = False

        if proc.stdout:
            for raw_line in proc.stdout:
                raw_line = raw_line.strip()
                if not raw_line:
                    continue
                try:
                    message = json.loads(raw_line)
                except json.JSONDecodeError:
                    continue

                event_type = message.get("event")
                if event_type == "init":
                    init_data = message.get("init", {})
                    conv_id = message.get("conversation_id") or thread_id
                    self._codex_event(
                        "thread/initialized",
                        {"threadId": thread_id, "conversationId": conv_id, "init": init_data},
                        source=source,
                    )

                elif event_type == "step_update":
                    step = message.get("step_update", {})
                    step_index = step.get("step_index", 0)
                    step_type = step.get("step_type", "")
                    state = step.get("state", "")

                    if step_type == "agent_response":
                        delta = step.get("text_delta")
                        if delta:
                            self._codex_event(
                                "item/agentMessage/delta",
                                {"itemId": f"text-{step_index}", "delta": delta},
                                source=source,
                            )
                        if state == "DONE" and step.get("response"):
                            final_text = step.get("response")
                            self._item_completed(
                                {"id": f"text-{step_index}", "type": "agentMessage", "text": final_text},
                                source=source,
                            )

                    elif step_type == "tool":
                        tool_name = step.get("tool_name") or "tool"
                        tool_info = step.get("tool_info") or {}
                        params = tool_info.get("parameters") or {}
                        summary = (
                            params.get("CommandLine")
                            or params.get("query")
                            or params.get("TargetFile")
                            or params.get("AbsolutePath")
                            or params.get("Url")
                            or ""
                        )
                        if not summary and params:
                            try:
                                summary = json.dumps(params)
                            except Exception:
                                summary = str(params)
                        cmd_summary = f"{tool_name}: {summary}".strip(": ")
                        tool_id = f"tool-{step_index}"

                        if state == "ACTIVE":
                            self._codex_event(
                                "item/started",
                                {"item": {"id": tool_id, "type": "commandExecution", "command": cmd_summary}},
                                source=source,
                            )
                        elif state == "DONE":
                            out_text = str(tool_info.get("output", ""))[:2000]
                            self._item_completed(
                                {"id": tool_id, "type": "commandExecution", "command": cmd_summary, "text": out_text},
                                source=source,
                            )

                    usage = step.get("usage")
                    if usage:
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
                            source=source,
                        )

                elif event_type == "result":
                    result = message.get("result", {})
                    status = result.get("status", "SUCCESS")
                    resp = result.get("response", "")
                    if resp:
                        final_text = resp
                        self._item_completed(
                            {"id": "text-final", "type": "agentMessage", "text": resp},
                            source=source,
                        )
                    usage = result.get("usage")
                    if usage:
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
                            source=source,
                        )

                    is_error = (status != "SUCCESS")
                    turn_dict = {"status": "failed" if is_error else "completed"}
                    if is_error:
                        turn_dict["error"] = {
                            "message": result.get("error_message") or f"AGY turn ended with status {status}",
                            "additionalDetails": None,
                        }
                    self._codex_event("turn/completed", {"threadId": thread_id, "turn": turn_dict}, source=source)
                    turn_completed = True
                    response_received = True

        proc.wait()
        exit_code = proc.returncode
        self._active_process = None

        if not turn_completed:
            stderr_out = ""
            if proc.stderr:
                try:
                    stderr_out = proc.stderr.read().strip()
                except Exception:
                    pass
            if exit_code != 0 and not response_received:
                err_msg = stderr_out or f"AGY process exited with code {exit_code}"
                self._codex_event(
                    "turn/completed",
                    {"threadId": thread_id, "turn": {"status": "failed", "error": {"message": err_msg, "additionalDetails": None}}},
                    source=source,
                )
            else:
                if final_text:
                    self._item_completed({"id": "text-final", "type": "agentMessage", "text": final_text}, source=source)
                self._codex_event(
                    "turn/completed",
                    {"threadId": thread_id, "turn": {"status": "completed"}},
                    source=source,
                )

    def send_turn(self, text: str, sandbox: str | None = None) -> str:
        """Start a new turn asynchronously and return thread_id immediately."""
        text = text.strip()
        if not text:
            raise ValueError("message is empty")
        with self._turn_lock:
            thread_id = str(uuid.uuid4())
            self._active_thread_id = thread_id
            self._active_source = "admiral"
            self._broadcast({"type": "turn_started", "thread_id": thread_id, "text": text, "ts": time.time()})
            self._codex_event("turn/started", {"threadId": thread_id}, source="admiral")

            worker = threading.Thread(
                target=self._run_turn_sync,
                args=(text, thread_id, "admiral"),
                daemon=True,
                name=f"agy-turn-{thread_id[:8]}",
            )
            worker.start()
            return thread_id

    def send_and_wait(
        self,
        compiled_text: str,
        sandbox: str | None = None,
        timeout: int = 180,
        source: str = "admiral",
    ) -> dict:
        """Start one turn synchronously, wait for completion, and return results."""
        compiled_text = compiled_text.strip()
        if not compiled_text:
            raise ValueError("compiled context is empty")

        with self._turn_lock:
            listener = self.subscribe()
            try:
                thread_id = str(uuid.uuid4())
                self._active_thread_id = thread_id
                self._active_source = source
                self._broadcast({"type": "turn_started", "thread_id": thread_id, "text": compiled_text, "source": source, "ts": time.time()})
                self._codex_event("turn/started", {"threadId": thread_id}, source=source)

                worker = threading.Thread(
                    target=self._run_turn_sync,
                    args=(compiled_text, thread_id, source),
                    daemon=True,
                    name=f"agy-turn-wait-{thread_id[:8]}",
                )
                worker.start()

                final_text: str | None = None
                tool_events: list[dict] = []
                deadline = time.time() + timeout

                while True:
                    remaining = deadline - time.time()
                    if remaining <= 0:
                        if self._active_process and self._active_process.poll() is None:
                            self._active_process.terminate()
                        raise AgyError("AGY turn timed out")
                    try:
                        event = listener.get(timeout=remaining)
                    except queue.Empty:
                        if self._active_process and self._active_process.poll() is None:
                            self._active_process.terminate()
                        raise AgyError("AGY turn timed out") from None

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
                            raise AgyError(f"AGY turn ended with status {status}: {error.get('message', '')}")
                        break
            finally:
                self.unsubscribe(listener)

        if not final_text or not final_text.strip():
            raise AgyError("AGY returned no reply")

        return {
            "text": final_text.strip(),
            "thread_id": thread_id,
            "sandbox": sandbox or "workspace-write",
            "approval_policy": "never",
            "source": source,
            "tool_events": tool_events,
            "thread_start_result": {},
        }

    def status(self) -> dict:
        proc = self._active_process
        is_running = proc is not None and proc.poll() is None
        return {
            "running": not self._closing,
            "pid": proc.pid if is_running else os.getpid(),
            "active_thread_id": self._active_thread_id,
            "subscriber_count": len(self._subscribers),
            "uptime_seconds": time.time() - self._started_at,
            "execution_sandbox": "workspace-write",
            "approval_policy": "never",
            "backend": "agy",
            "model": AGY_MODEL,
        }

    def close(self) -> None:
        self._closing = True
        proc = self._active_process
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
