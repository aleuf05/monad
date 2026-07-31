"""Codex app-server-backed ModelProvider.

Each generate() call starts a fresh ephemeral thread and one turn; the
app-server subprocess persists for the life of this provider, but no
conversational state is kept inside Codex itself. The ship's own SQLite
state (see database.py) is the sole continuity layer across restarts --
this deliberately avoids depending on Codex thread resumption, which is
unproven in this repository (tools/living-captain-workbench/codex_bridge.py
only ever uses ephemeral, single-turn threads; nothing here calls
thread/resume).

The JSON-RPC-over-stdio transport (_send/_request/_read) is carried over
from codex_bridge.py verbatim. generate() itself is new: it sends one text
turn and extracts the agentMessage reply (pattern proven in
tools/living-captain-workbench/prove_app_server.py), instead of
codex_bridge.py's job-specific image-file-polling logic.
"""

from __future__ import annotations

import json
import os
import queue
import subprocess
import threading
from pathlib import Path

from model_provider import GenerationLimits, Message, ProviderError, ProviderResponse

DEFAULT_MODEL = "codex"
INIT_TIMEOUT_SECONDS = 30
TURN_TIMEOUT_SECONDS = 180


class CodexProvider:
    name = "Codex"

    def __init__(self, cwd: Path, model: str = DEFAULT_MODEL):
        self.cwd = cwd
        self.model = model
        self._process = subprocess.Popen(
            [os.environ.get("CODEX_BIN", "/home/cgl/.local/bin/codex"), "app-server"],
            cwd=cwd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )
        self._responses: dict[int, queue.Queue] = {}
        self._notifications: queue.Queue = queue.Queue()
        self._counter = 0
        self._lock = threading.Lock()
        threading.Thread(target=self._read, daemon=True, name="codex-app-server-reader").start()
        self._request(
            "initialize",
            {
                "clientInfo": {
                    "name": "monad_chat_captain",
                    "title": "Monad Chat Captain",
                    "version": "0.1.0",
                }
            },
            timeout=INIT_TIMEOUT_SECONDS,
        )
        self._send({"method": "initialized", "params": {}})

    def _send(self, message: dict) -> None:
        if self._process.poll() is not None or not self._process.stdin:
            raise ProviderError("Codex app-server is not running")
        self._process.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
        self._process.stdin.flush()

    def _request(self, method: str, params: dict, timeout: int = 30) -> dict:
        self._counter += 1
        request_id = self._counter
        response_queue: queue.Queue = queue.Queue(maxsize=1)
        self._responses[request_id] = response_queue
        self._send({"method": method, "id": request_id, "params": params})
        try:
            response = response_queue.get(timeout=timeout)
        except queue.Empty:
            raise ProviderError(f"Codex {method} timed out") from None
        finally:
            self._responses.pop(request_id, None)
        if "error" in response:
            detail = response["error"].get("message", "unknown error")
            raise ProviderError(f"Codex {method} failed: {detail}")
        return response.get("result", {})

    def _read(self) -> None:
        if not self._process.stdout:
            return
        for line in self._process.stdout:
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                continue
            request_id = message.get("id")
            if request_id in self._responses:
                self._responses[request_id].put(message)
            elif message.get("method"):
                self._notifications.put(message)

    def generate(
        self,
        system_prompt: str,
        messages: list[Message],
        limits: GenerationLimits,
    ) -> ProviderResponse:
        transcript = "\n\n".join(
            f"{message.role.upper()}: {message.content}" for message in messages
        )
        prompt = f"{system_prompt}\n\n---\n\n{transcript}" if transcript else system_prompt

        with self._lock:
            while not self._notifications.empty():
                self._notifications.get_nowait()
            started = self._request(
                "thread/start",
                {
                    "cwd": str(self.cwd),
                    "sandbox": "read-only",
                    "approvalPolicy": "never",
                    "ephemeral": True,
                },
            )
            thread_id = started["thread"]["id"]
            self._request(
                "turn/start",
                {
                    "threadId": thread_id,
                    "cwd": str(self.cwd),
                    "input": [{"type": "text", "text": prompt}],
                },
            )
            final_text: str | None = None
            while True:
                try:
                    event = self._notifications.get(timeout=TURN_TIMEOUT_SECONDS)
                except queue.Empty:
                    raise ProviderError("Codex turn timed out") from None
                method = event.get("method", "")
                params = event.get("params", {})
                if params.get("threadId") not in {None, thread_id}:
                    continue
                if method == "item/completed":
                    item = params.get("item", {})
                    if item.get("type") == "agentMessage":
                        final_text = item.get("text")
                elif method == "turn/completed":
                    status = params.get("turn", {}).get("status", "completed")
                    if status not in {"completed", "success"}:
                        raise ProviderError(f"Codex turn ended with status {status}")
                    break

        if not final_text or not final_text.strip():
            raise ProviderError("Codex returned no reply")
        return ProviderResponse(
            text=final_text.strip(),
            provider=self.name,
            model=self.model,
            input_tokens=None,
            output_tokens=None,
            total_tokens=None,
            finish_reason="completed",
        )

    def close(self) -> None:
        if self._process.poll() is None:
            self._process.terminate()
