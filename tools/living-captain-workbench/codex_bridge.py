"""Persistent local Codex app-server bridge using saved ChatGPT authentication."""

from __future__ import annotations

import json
import os
import queue
import shutil
import subprocess
import threading
from pathlib import Path


class CodexBridge:
    def __init__(self, cwd: Path):
        self.cwd = cwd
        self.process = subprocess.Popen(
            [os.environ.get("CODEX_BIN", "/home/cgl/.local/bin/codex"), "app-server"],
            cwd=cwd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )
        self.responses: dict[int, queue.Queue] = {}
        self.notifications: queue.Queue = queue.Queue()
        self.counter = 0
        self.lock = threading.Lock()
        threading.Thread(target=self._read, daemon=True, name="codex-app-server-reader").start()
        self._request("initialize", {
            "clientInfo": {
                "name": "monad_beastscape",
                "title": "Monad Beastscape Captain",
                "version": "0.1.0",
            }
        })
        self._send({"method": "initialized", "params": {}})

    def _send(self, message: dict) -> None:
        if self.process.poll() is not None or not self.process.stdin:
            raise RuntimeError("Codex app-server is not running")
        self.process.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
        self.process.stdin.flush()

    def _request(self, method: str, params: dict, timeout: int = 30) -> dict:
        self.counter += 1
        request_id = self.counter
        response_queue: queue.Queue = queue.Queue(maxsize=1)
        self.responses[request_id] = response_queue
        self._send({"method": method, "id": request_id, "params": params})
        response = response_queue.get(timeout=timeout)
        self.responses.pop(request_id, None)
        if "error" in response:
            raise RuntimeError(f"Codex {method} failed: {response['error'].get('message', 'unknown error')}")
        return response.get("result", {})

    def _read(self) -> None:
        if not self.process.stdout:
            return
        for line in self.process.stdout:
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                continue
            request_id = message.get("id")
            if request_id in self.responses:
                self.responses[request_id].put(message)
            elif message.get("method"):
                self.notifications.put(message)

    def generate(self, prompt: str, schematic: Path, output: Path, on_event) -> None:
        with self.lock:
            while not self.notifications.empty():
                self.notifications.get_nowait()
            started = self._request("thread/start", {
                "cwd": str(self.cwd),
                "sandbox": "workspace-write",
                "ephemeral": True,
            })
            thread_id = started["thread"]["id"]
            mission = (
                f"{prompt}\n\n"
                f"Reference structural schematic: {schematic}\n"
                f"Required final artifact path: {output}\n\n"
                "Use the $imagegen skill with the schematic as the reference image. "
                "Generate exactly one final image. Inspect it for structural fidelity, "
                "then copy the accepted image to the required final artifact path. "
                "Do not modify repository source files. End only after the file exists."
            )
            self._request("turn/start", {
                "threadId": thread_id,
                "cwd": str(self.cwd),
                "input": [
                    {"type": "text", "text": mission},
                    {"type": "localImage", "path": str(schematic)},
                ],
            })
            while True:
                event = self.notifications.get(timeout=600)
                method = event.get("method", "")
                params = event.get("params", {})
                if params.get("threadId") not in {None, thread_id}:
                    continue
                on_event(method)
                if method == "turn/completed":
                    status = params.get("turn", {}).get("status", "completed")
                    if status not in {"completed", "success"}:
                        raise RuntimeError(f"Codex turn ended with status {status}")
                    break
            if not output.exists():
                generated_dir = Path.home() / ".codex" / "generated_images" / thread_id
                candidates = sorted(
                    generated_dir.glob("*"),
                    key=lambda candidate: candidate.stat().st_mtime,
                    reverse=True,
                )
                if candidates:
                    output.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(candidates[0], output)
            if not output.exists() or output.stat().st_size < 10_000:
                raise RuntimeError("Codex completed without returning an image artifact")
