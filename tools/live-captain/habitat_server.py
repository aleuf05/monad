#!/usr/bin/env python3
"""Captain Habitat Server — Live Captain Operational Runtime.

Port 4776. Exposes the Captain Habitat API, streaming SSE turn execution,
persistent conversation threads, tool actions, and Heart operational learning.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import queue
import re
import subprocess
import sys
import threading
import time
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional

# Path setup
ROOT_DIR = Path(__file__).resolve().parent
REPO_ROOT = ROOT_DIR.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from habitat_store import HabitatStore
from context_compiler import (
    load_required_text,
    load_optional_text,
    compact_runtime_sources,
)
from comms import (
    Action,
    AuthorityBoundary,
    AuthorityLevel,
    InboundMessage,
    OutboundMessage,
    Urgency,
    WebChannelAdapter,
)
from job_engine import GLOBAL_JOB_RUNNER
from proactive import NOTIFIER

DB_PATH = REPO_ROOT / "data" / "live-captain" / "habitat.db"
STORE = HabitatStore(DB_PATH)

KERNEL_PATH = REPO_ROOT / "EDIT-THIS-ONE-FILE.md"
BEARING_PATH = ROOT_DIR / "context" / "current-bearing.md"
LEDGER_PATH = ROOT_DIR / "context" / "continuity-ledger.md"
UPLOAD_DIR = REPO_ROOT / "data" / "live-captain" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Active execution threads map: thread_id -> threading.Event (cancel signal)
ACTIVE_CANCEL_EVENTS: Dict[str, threading.Event] = {}


def compile_system_prompt() -> str:
    """Compile Live Captain identity, bearing, ledger, and Heart lessons."""
    kernel_text, _ = load_required_text(KERNEL_PATH, "Live Captain Posture")
    bearing_text, _ = load_optional_text(BEARING_PATH, "(no current bearing set)")
    ledger_text, _ = load_optional_text(LEDGER_PATH, "(no continuity ledger)")

    # Compact hot runtime sources
    bearing_text, ledger_text, _ = compact_runtime_sources(bearing_text, ledger_text, "")

    # Load Heart lessons
    heart_lessons = STORE.get_heart_lessons(limit=15)
    heart_block = ""
    if heart_lessons:
        heart_lines = [f"- {h['lesson']} (source: {h['source']})" for h in heart_lessons]
        heart_block = "\n\n## Persisted Captain Heart Lessons\n" + "\n".join(heart_lines)

    return (
        f"{kernel_text}\n\n"
        f"## Current Bearing\n{bearing_text}\n\n"
        f"## Continuity Ledger\n{ledger_text}"
        f"{heart_block}\n\n"
        f"## Operational Instructions\n"
        f"You are the Live Captain operating Captain Habitat. "
        f"Communicate directly, warmly, and ground every claim in real evidence. "
        f"When tool execution is required, format tool requests as JSON blocks or execute them directly."
    )


class ToolExecutor:
    """Executes authorized Live Captain operational tools."""

    @staticmethod
    def execute(tool_name: str, args: Dict[str, Any]) -> str:
        if tool_name == "run_command":
            cmd = args.get("command") or args.get("CommandLine") or ""
            if not cmd:
                return "Error: Empty command"
            try:
                res = subprocess.run(
                    cmd, shell=True, cwd=REPO_ROOT,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    timeout=60, text=True
                )
                output = res.stdout.strip() or "(no output)"
                return f"[Exit code {res.returncode}]\n{output}"
            except subprocess.TimeoutExpired:
                return "Error: Command timed out after 60s"
            except Exception as e:
                return f"Error executing command: {e}"

        elif tool_name in ("read_file", "view_file"):
            path_str = args.get("path") or args.get("AbsolutePath") or ""
            p = Path(path_str) if Path(path_str).is_absolute() else REPO_ROOT / path_str
            if not p.exists():
                return f"Error: File does not exist: {p}"
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
                if len(text) > 8000:
                    text = text[:8000] + f"\n... [truncated, total {len(text)} chars]"
                return text
            except Exception as e:
                return f"Error reading file: {e}"

        elif tool_name in ("write_file", "edit_file"):
            path_str = args.get("path") or args.get("TargetFile") or ""
            content = args.get("content") or args.get("CodeContent") or ""
            p = Path(path_str) if Path(path_str).is_absolute() else REPO_ROOT / path_str
            try:
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content, encoding="utf-8")
                return f"Successfully wrote {len(content)} chars to {p}"
            except Exception as e:
                return f"Error writing file: {e}"

        elif tool_name == "save_heart_lesson":
            lesson = args.get("lesson", "")
            source = args.get("source", "Operator correction")
            if lesson:
                res = STORE.add_heart_lesson(lesson, source)
                return f"Saved Heart lesson: {res['id']}"
            return "Error: Empty lesson"

        elif tool_name == "sound_ship":
            try:
                res = subprocess.run(
                    "bash scripts/sound-the-ship.sh", shell=True, cwd=REPO_ROOT,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    timeout=30, text=True
                )
                return res.stdout.strip()
            except Exception as e:
                return f"Error sounding ship: {e}"

        elif tool_name in ("delegate_job", "dispatch_agent", "run_job"):
            worker = args.get("worker", "agy")
            request = args.get("request") or args.get("prompt") or ""
            conversation_id = args.get("conversation_id")
            if not request:
                return "Error: Empty request for worker"
            job = GLOBAL_JOB_RUNNER.submit(
                worker=worker,
                request=request,
                conversation_id=conversation_id,
                on_complete=lambda j: NOTIFIER.notify(
                    text=f"⚙️ Worker `{j['worker']}` completed job `{j['id']}`.\n\n### Result\n```text\n{j['result'][:1200]}\n```",
                    semantic_role="captain",
                    thread_id=j.get("conversation_id"),
                ),
            )
            return (
                f"Dispatched.\n"
                f"Job: `{job['id']}`\n"
                f"Worker: `{job['worker']}`\n"
                f"State: `{job['state']}`"
            )

        elif tool_name == "list_jobs":
            jobs = GLOBAL_JOB_RUNNER.store.list_jobs(limit=10)
            if not jobs:
                return "No jobs registered."
            lines = [f"- `{j['id']}` [{j['worker']}] ({j['state']}): {j['request'][:60]}" for j in jobs]
            return "\n".join(lines)

        elif tool_name == "cancel_job":
            job_id = args.get("job_id", "").strip()
            ok = GLOBAL_JOB_RUNNER.cancel(job_id)
            return f"Job `{job_id}` cancellation request sent: {'success' if ok else 'failed'}"

        return f"Unknown tool: {tool_name}"


class LLMEngine:
    """Streams response tokens and manages live tool execution loops."""

    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY")

    def run_turn_stream(
        self,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        cancel_event: threading.Event,
        event_queue: queue.Queue
    ) -> tuple[str, List[Dict[str, Any]]]:
        """Runs an execution turn, streaming SSE events to event_queue."""
        
        # If API key is available, call Gemini API with streaming
        if self.api_key:
            return self._run_gemini_stream(system_prompt, messages, cancel_event, event_queue)
        
        # Deterministic / Subprocess fallback execution
        return self._run_fallback_execution(system_prompt, messages, cancel_event, event_queue)

    def _run_gemini_stream(
        self,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        cancel_event: threading.Event,
        event_queue: queue.Queue
    ) -> tuple[str, List[Dict[str, Any]]]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:streamGenerateContent?alt=sse&key={self.api_key}"

        contents = []
        for m in messages:
            role = "model" if m["role"] == "captain" else "user"
            contents.append({"role": role, "parts": [{"text": m["text"]}]})

        payload = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": contents,
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        full_response_text = ""
        tool_events = []

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                for line_bytes in resp:
                    if cancel_event.is_set():
                        event_queue.put({"event": "delta", "data": json.dumps({"content": "\n\n[Turn interrupted by operator]"})})
                        break

                    line = line_bytes.decode("utf-8", errors="replace").strip()
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            data_obj = json.loads(data_str)
                            candidates = data_obj.get("candidates") or []
                            if candidates:
                                parts = candidates[0].get("content", {}).get("parts") or []
                                for p in parts:
                                    text_chunk = p.get("text", "")
                                    if text_chunk:
                                        full_response_text += text_chunk
                                        event_queue.put({"event": "delta", "data": json.dumps({"content": text_chunk})})
                        except Exception:
                            pass
        except Exception as err:
            # On network error, drop back to fallback generator seamlessly
            return self._run_fallback_execution(system_prompt, messages, cancel_event, event_queue)

        return full_response_text, tool_events

    def _run_fallback_execution(
        self,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        cancel_event: threading.Event,
        event_queue: queue.Queue
    ) -> tuple[str, List[Dict[str, Any]]]:
        """Rule-based execution engine that can inspect real repository state & run tools."""
        last_admiral_msg = messages[-1]["text"].strip() if messages else ""
        thread_id = messages[-1].get("thread_id") if messages else None
        tool_events = []
        lower_msg = last_admiral_msg.lower()
        clean_lower = re.sub(r'^(captain|live captain|please|hey captain)[,\s:]+', '', lower_msg).strip()

        # Check for agent delegation (e.g. "have agy inspect ...", "have claude check ...")
        if any(clean_lower.startswith(p) or p in lower_msg for p in ["have agy", "have claude", "have codex", "dispatch agy", "dispatch claude", "dispatch codex"]):
            worker = "agy"
            if "claude" in lower_msg:
                worker = "claude"
            elif "codex" in lower_msg:
                worker = "codex"

            # Strip worker prefix from task request
            task_req = re.sub(r'^(.*?)(have|dispatch)\s+(agy|claude|codex)\s+(to\s+)?', '', last_admiral_msg, flags=re.IGNORECASE).strip(" ,:") or last_admiral_msg

            event_queue.put({"event": "tool", "data": json.dumps({"name": "delegate_job", "action": f"Dispatching {worker.upper()} Job", "summary": f"Job delegated to {worker}"})})
            res = ToolExecutor.execute("delegate_job", {"worker": worker, "request": task_req, "conversation_id": thread_id})
            tool_events.append({"name": "delegate_job", "summary": f"Delegated to {worker}", "result": res})
            response_text = f"### Agent Job Dispatched\n\n{res}\n\nTask: *\"{task_req}\"*\n\nUpdates will stream automatically upon completion."

        elif any(w in lower_msg for w in ["list jobs", "show jobs", "check jobs", "job status"]):
            event_queue.put({"event": "tool", "data": json.dumps({"name": "list_jobs", "action": "Listing Jobs", "summary": "Querying job engine"})})
            res = ToolExecutor.execute("list_jobs", {})
            tool_events.append({"name": "list_jobs", "summary": "Querying job engine", "result": res})
            response_text = f"### Registered Jobs\n\n{res}"

        elif "cancel job" in lower_msg:
            job_id = last_admiral_msg.split("cancel job", 1)[-1].strip(" :`")
            event_queue.put({"event": "tool", "data": json.dumps({"name": "cancel_job", "action": "Cancelling Job", "summary": f"Job {job_id}"})})
            res = ToolExecutor.execute("cancel_job", {"job_id": job_id})
            tool_events.append({"name": "cancel_job", "summary": f"Cancelled {job_id}", "result": res})
            response_text = res

        elif any(w in lower_msg for w in ["sound", "ship", "status", "check ship"]):
            event_queue.put({"event": "tool", "data": json.dumps({"name": "sound_ship", "action": "Sounding Ship", "summary": "bash scripts/sound-the-ship.sh"})})
            res = ToolExecutor.execute("sound_ship", {})
            tool_events.append({"name": "sound_ship", "summary": "bash scripts/sound-the-ship.sh", "result": res})
            response_text = f"### Ship Soundness Report\n\n```text\n{res}\n```\n\nAll systems inspected against canonical posture."

        elif any(w in lower_msg for w in ["heart", "lesson", "persist"]):
            event_queue.put({"event": "tool", "data": json.dumps({"name": "save_heart_lesson", "action": "Saving Heart Lesson", "summary": "Persisting operational lesson"})})
            res = ToolExecutor.execute("save_heart_lesson", {"lesson": last_admiral_msg, "source": "Admiral prompt"})
            tool_events.append({"name": "save_heart_lesson", "summary": "Persisting Heart Lesson", "result": res})
            response_text = f"Persisted operational Heart lesson to storage.\n\nResult: `{res}`"

        else:
            # High-signal standard Captain response
            auth_level = AuthorityBoundary.assess(last_admiral_msg)
            response_text = (
                f"Received directive: **{last_admiral_msg[:100]}**\n\n"
                f"- **Authority Level:** `{auth_level.value}`\n"
                f"- **Context:** Compiled from `EDIT-THIS-ONE-FILE.md` & `current-bearing.md`.\n\n"
                f"Live Captain ready to inspect, execute, or delegate."
            )

        # Stream response text in chunks
        chunk_size = 25
        for i in range(0, len(response_text), chunk_size):
            if cancel_event.is_set():
                break
            chunk = response_text[i:i + chunk_size]
            event_queue.put({"event": "delta", "data": json.dumps({"content": chunk})})
            time.sleep(0.02)

        return response_text, tool_events


LLM = LLMEngine()


class HabitatRequestHandler(BaseHTTPRequestHandler):
    """HTTP Handler for Captain Habitat API."""

    def log_message(self, format: str, *args: tuple) -> None:
        pass

    def _send_json(self, status: int, data: dict) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        path = self.path.split("?")[0].rstrip("/")

        if path in ("/status", "/captain-api/status", "/api/status"):
            self._send_json(200, {
                "status": "ok",
                "service": "captain-habitat",
                "has_llm_key": bool(LLM.api_key),
                "threads_count": len(STORE.list_threads())
            })
            return

        if path in ("/threads", "/captain-api/threads"):
            threads = STORE.list_threads()
            self._send_json(200, {"threads": threads})
            return

        if path.startswith("/captain-api/threads/") or path.startswith("/threads/"):
            thread_id = path.split("/")[-1]
            thread = STORE.get_thread(thread_id)
            if thread:
                self._send_json(200, thread)
            else:
                self.send_error(404, "Thread not found")
            return

        if path in ("/heart", "/captain-api/heart"):
            lessons = STORE.get_heart_lessons()
            self._send_json(200, {"lessons": lessons})
            return

        if path in ("/jobs", "/captain-api/jobs"):
            jobs = GLOBAL_JOB_RUNNER.store.list_jobs(limit=30)
            self._send_json(200, {"jobs": jobs})
            return

        if path.startswith("/captain-api/jobs/") or path.startswith("/jobs/"):
            job_id = path.split("/")[-1]
            job = GLOBAL_JOB_RUNNER.store.get_job(job_id)
            if job:
                self._send_json(200, job)
            else:
                self.send_error(404, "Job not found")
            return

        self.send_error(404, "Not Found")

    def do_POST(self) -> None:
        path = self.path.split("?")[0].rstrip("/")

        if path in ("/jobs", "/captain-api/jobs"):
            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len) if content_len > 0 else b"{}"
            data = json.loads(body.decode("utf-8")) if body else {}
            worker = data.get("worker", "agy")
            request = data.get("request", "")
            conversation_id = data.get("conversation_id")
            if not request:
                self._send_json(400, {"error": "Empty request"})
                return
            job = GLOBAL_JOB_RUNNER.submit(worker=worker, request=request, conversation_id=conversation_id)
            self._send_json(200, job)
            return

        if (path.startswith("/captain-api/jobs/") or path.startswith("/jobs/")) and path.endswith("/cancel"):
            job_id = path.split("/")[-2]
            ok = GLOBAL_JOB_RUNNER.cancel(job_id)
            self._send_json(200, {"status": "cancelled" if ok else "failed", "job_id": job_id})
            return

        if path in ("/notify", "/captain-api/notify"):
            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len) if content_len > 0 else b"{}"
            data = json.loads(body.decode("utf-8")) if body else {}
            text = data.get("text", "")
            if not text:
                self._send_json(400, {"error": "Empty notification text"})
                return
            res = NOTIFIER.notify(
                text=text,
                semantic_role=data.get("role", "captain"),
                urgency=data.get("urgency", "normal"),
                thread_id=data.get("thread_id"),
                actions=data.get("actions"),
            )
            self._send_json(200, res)
            return

        if path in ("/threads", "/captain-api/threads"):
            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len) if content_len > 0 else b"{}"
            data = json.loads(body.decode("utf-8")) if body else {}
            thread = STORE.create_thread(data.get("title"))
            self._send_json(200, thread)
            return

        if path in ("/heart", "/captain-api/heart"):
            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len)
            data = json.loads(body.decode("utf-8")) if body else {}
            lesson = data.get("lesson", "")
            source = data.get("source", "Operator")
            if lesson:
                res = STORE.add_heart_lesson(lesson, source)
                self._send_json(200, res)
            else:
                self._send_json(400, {"error": "Empty lesson"})
            return

        if path in ("/stop", "/captain-api/stop"):
            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len) if content_len > 0 else b"{}"
            data = json.loads(body.decode("utf-8")) if body else {}
            thread_id = data.get("thread_id")
            if thread_id and thread_id in ACTIVE_CANCEL_EVENTS:
                ACTIVE_CANCEL_EVENTS[thread_id].set()
                self._send_json(200, {"status": "stopped", "thread_id": thread_id})
            else:
                self._send_json(200, {"status": "not_running", "thread_id": thread_id})
            return

        if path in ("/upload", "/captain-api/upload"):
            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len)
            filename = f"upload_{int(time.time())}_{uuid.uuid4().hex[:6]}.bin"
            file_path = UPLOAD_DIR / filename
            file_path.write_bytes(body)
            self._send_json(200, {"filename": filename, "path": str(file_path)})
            return

        if path in ("/chat", "/captain-api/chat"):
            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len)
            data = json.loads(body.decode("utf-8")) if body else {}

            thread_id = data.get("thread_id")
            prompt = (data.get("prompt") or "").strip()
            attachments = data.get("attachments") or []

            if not prompt:
                self._send_json(400, {"error": "Empty prompt"})
                return

            if not thread_id:
                thread = STORE.create_thread(prompt[:40])
                thread_id = thread["id"]

            # Save Admiral message
            STORE.add_message(thread_id, "admiral", prompt, attachments=attachments)

            # Prepare SSE stream response headers
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            # Set up cancel event and event queue
            cancel_event = threading.Event()
            ACTIVE_CANCEL_EVENTS[thread_id] = cancel_event
            event_queue: queue.Queue = queue.Queue()

            # Compile context
            system_prompt = compile_system_prompt()
            thread_data = STORE.get_thread(thread_id) or {}
            messages = thread_data.get("messages", [])

            # Run LLM execution in worker thread
            final_text_holder = [""]
            tool_events_holder = [[]]

            def worker():
                t, tools = LLM.run_turn_stream(system_prompt, messages, cancel_event, event_queue)
                final_text_holder[0] = t
                tool_events_holder[0] = tools
                event_queue.put(None)  # EOF marker

            t_thread = threading.Thread(target=worker, daemon=True)
            t_thread.start()

            # Stream SSE to client
            while True:
                try:
                    item = event_queue.get(timeout=0.2)
                    if item is None:
                        break
                    sse_msg = f"event: {item['event']}\ndata: {item['data']}\n\n"
                    self.wfile.write(sse_msg.encode("utf-8"))
                    self.wfile.flush()
                except queue.Empty:
                    if not t_thread.is_alive() and event_queue.empty():
                        break

            # Save Captain message to DB
            captain_text = final_text_holder[0]
            if captain_text:
                STORE.add_message(thread_id, "captain", captain_text, tool_events=tool_events_holder[0])

            # Send done event
            done_msg = f"event: done\ndata: {json.dumps({'thread_id': thread_id})}\n\n"
            self.wfile.write(done_msg.encode("utf-8"))
            self.wfile.flush()

            if thread_id in ACTIVE_CANCEL_EVENTS:
                del ACTIVE_CANCEL_EVENTS[thread_id]
            self.close_connection = True
            return

        self.send_error(404, "Not Found")

    def do_DELETE(self) -> None:
        path = self.path.split("?")[0].rstrip("/")
        if path.startswith("/captain-api/threads/") or path.startswith("/threads/"):
            thread_id = path.split("/")[-1]
            deleted = STORE.delete_thread(thread_id)
            if deleted:
                self._send_json(200, {"status": "deleted", "thread_id": thread_id})
            else:
                self.send_error(404, "Thread not found")
            return
        self.send_error(404, "Not Found")


def run_server(host: str = "127.0.0.1", port: int = 4777) -> None:
    ThreadingHTTPServer.allow_reuse_address = True
    server = ThreadingHTTPServer((host, port), HabitatRequestHandler)
    print(f"⚓ CAPTAIN HABITAT SERVER running at http://{host}:{port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down Captain Habitat server.")
        server.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Captain Habitat Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host address to bind")
    parser.add_argument("--port", type=int, default=4777, help="Port to bind")
    args = parser.parse_args()

    run_server(host=args.host, port=args.port)
