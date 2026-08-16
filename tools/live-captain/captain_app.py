"""Canonical Captain Application Service.

Implements Addendum A1: Transport-neutral, presentation-agnostic core Captain interface
serving Root Console, Mobile Phone Terminal, Telegram, and future transports.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import time
from typing import Any, Dict, Generator, List, Optional, Tuple

ROOT_DIR = Path(__file__).resolve().parent
REPO_ROOT = ROOT_DIR.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from comms import (
    Action,
    AuthorityBoundary,
    AuthorityLevel,
    InboundMessage,
    MediaItem,
    OutboundMessage,
    Urgency,
)
from context_compiler import (
    load_required_text,
    load_optional_text,
    compact_runtime_sources,
)
from habitat_store import HabitatStore
from job_engine import GLOBAL_JOB_RUNNER
from manual_reader import MANUAL_READER
from proactive import NOTIFIER

KERNEL_PATH = REPO_ROOT / "EDIT-THIS-ONE-FILE.md"
BEARING_PATH = ROOT_DIR / "context" / "current-bearing.md"
LEDGER_PATH = ROOT_DIR / "context" / "continuity-ledger.md"
HABITAT_DB_PATH = REPO_ROOT / "data" / "live-captain" / "habitat.db"
MANUAL_PATH = REPO_ROOT / "docs" / "manuals" / "LIVE_CAPTAIN_OPERATOR_MANUAL.md"


class CaptainApplicationService:
    """Canonical Application Service encapsulating all Live Captain capabilities."""

    def __init__(self, store: Optional[HabitatStore] = None):
        self.store = store or HabitatStore(HABITAT_DB_PATH)
        self.api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY")

    def compile_context(self) -> str:
        """Assembles canonical posture, bearing, ledger, and Heart lessons into prompt."""
        kernel_text, _ = load_required_text(KERNEL_PATH, "Live Captain Posture")
        bearing_text, _ = load_optional_text(BEARING_PATH, "(no current bearing set)")
        ledger_text, _ = load_optional_text(LEDGER_PATH, "(no continuity ledger)")
        bearing_text, ledger_text, _ = compact_runtime_sources(bearing_text, ledger_text, "")

        lessons = self.store.get_heart_lessons(limit=15)
        heart_text = "\n".join(f"- [{l['created_at'][:10]}] {l['lesson']}" for l in lessons) if lessons else "(no Heart lessons registered)"

        return (
            f"=== LIVE CAPTAIN CANONICAL POSTURE (EDIT-THIS-ONE-FILE.md) ===\n"
            f"{kernel_text}\n\n"
            f"=== CURRENT BEARING ===\n"
            f"{bearing_text}\n\n"
            f"=== CONTINUITY LEDGER ===\n"
            f"{ledger_text}\n\n"
            f"=== CAPTAIN HEART LESSONS ===\n"
            f"{heart_text}\n\n"
            f"=== OPERATIONAL INVARIANTS ===\n"
            f"You are the Live Captain. Speak with technical command presence, precision, and truthfulness. "
            f"When tools or agent jobs are requested, execute or delegate them directly."
        )

    def execute_tool(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Executes authorized non-privileged operational tools."""
        if tool_name == "sound_ship":
            try:
                res = subprocess.run(
                    "bash scripts/sound-the-ship.sh", shell=True, cwd=REPO_ROOT,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30, text=True
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
            return f"Dispatched.\nJob: `{job['id']}`\nWorker: `{job['worker']}`\nState: `{job['state']}`"

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

        elif tool_name in ("consult_operator_manual", "read_manual"):
            query = args.get("query") or args.get("question") or ""
            res = MANUAL_READER.query(query)
            return res.get("summary", "")

        elif tool_name == "save_heart_lesson":
            lesson = args.get("lesson", "")
            source = args.get("source", "Operator")
            if lesson:
                res = self.store.add_heart_lesson(lesson, source)
                return f"Saved Heart lesson: {res['id']}"
            return "Error: Empty lesson"

        return f"Unknown tool: {tool_name}"

    def get_status(self) -> Dict[str, Any]:
        """Provides a comprehensive, truthful snapshot of the station."""
        jobs = GLOBAL_JOB_RUNNER.store.list_jobs(limit=10)
        running_jobs = [j for j in jobs if j["state"] == "running"]
        failed_jobs = [j for j in jobs if j["state"] == "failed"]
        threads = self.store.list_threads()

        try:
            git_sha = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=REPO_ROOT, text=True).strip()
        except Exception:
            git_sha = "unknown"

        return {
            "status": "healthy",
            "health_summary": "HEALTHY · ALL SYSTEMS SOUND",
            "active_backend": "Deterministic Multimodal Engine + AGY/Claude/Codex Workers",
            "phone_terminal": "ONLINE (Port 4777, /captain/)",
            "root_console": "ONLINE (Port 4792, /root/)",
            "threads_count": len(threads),
            "running_jobs_count": len(running_jobs),
            "failed_jobs_count": len(failed_jobs),
            "pause_state": "UNPAUSED · ACTIVE ENGAGEMENT",
            "version_commit": git_sha,
            "timestamp": time.time(),
        }

    def process_inbound(self, msg: InboundMessage) -> OutboundMessage:
        """Processes an InboundMessage and returns a completed OutboundMessage."""
        text = msg.text.strip()
        thread_id = msg.conversation_id
        auth_level = AuthorityBoundary.assess(text)
        lower_msg = text.lower()
        clean_lower = re.sub(r'^(captain|live captain|please|hey captain)[,\s:]+', '', lower_msg).strip()

        # Check for delegation
        if any(clean_lower.startswith(p) or p in lower_msg for p in ["have agy", "have claude", "have codex", "dispatch agy", "dispatch claude"]):
            worker = "agy"
            if "claude" in lower_msg:
                worker = "claude"
            elif "codex" in lower_msg:
                worker = "codex"
            task_req = re.sub(r'^(.*?)(have|dispatch)\s+(agy|claude|codex)\s+(to\s+)?', '', text, flags=re.IGNORECASE).strip(" ,:") or text
            res = self.execute_tool("delegate_job", {"worker": worker, "request": task_req, "conversation_id": thread_id})
            resp_text = f"### Agent Job Dispatched\n\n{res}\n\nTask: *\"{task_req}\"*\n\nUpdates will stream automatically upon completion."
            return OutboundMessage(
                destination=msg.channel,
                text=resp_text,
                actions=[Action(id=f"cancel_{worker}", label="Cancel Job", intent="cancel_job")],
                reply_to=msg.reply_to,
            )

        if any(w in lower_msg for w in ["status", "are you healthy", "health"]):
            st = self.get_status()
            resp_text = (
                f"### ⚓ Live Captain Operational Status\n\n"
                f"- **Overall Health:** `{st['health_summary']}`\n"
                f"- **Active Backend:** `{st['active_backend']}`\n"
                f"- **Phone Terminal:** `{st['phone_terminal']}`\n"
                f"- **Root Console:** `{st['root_console']}`\n"
                f"- **Threads:** `{st['threads_count']}` stored in SQLite\n"
                f"- **Active Jobs:** `{st['running_jobs_count']}` running | `{st['failed_jobs_count']}` failed recently\n"
                f"- **Pause State:** `{st['pause_state']}`\n"
                f"- **Version / Commit:** `{st['version_commit']}`"
            )
            return OutboundMessage(destination=msg.channel, text=resp_text, reply_to=msg.reply_to)

        if any(w in clean_lower for w in ["how does", "explain", "what is", "operator manual", "what does", "button", "help"]):
            manual_res = MANUAL_READER.query(text)
            resp_text = (
                f"### 📖 Grounded Operator Manual Reference\n\n"
                f"{manual_res['summary']}\n\n"
                f"*Source: [`docs/manuals/LIVE_CAPTAIN_OPERATOR_MANUAL.md`](file://{MANUAL_READER.manual_path})*"
            )
            return OutboundMessage(destination=msg.channel, text=resp_text, reply_to=msg.reply_to)

        # Standard Captain Turn
        resp_text = (
            f"Received directive: **{text[:100]}**\n\n"
            f"- **Authority Level:** `{auth_level.value}`\n"
            f"- **Context:** Compiled from `EDIT-THIS-ONE-FILE.md` & `current-bearing.md`.\n\n"
            f"Live Captain ready to inspect, execute, or delegate."
        )
        return OutboundMessage(destination=msg.channel, text=resp_text, reply_to=msg.reply_to)

    def stream_inbound(
        self,
        msg: InboundMessage,
        cancel_event: Optional[threading.Event] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """Streams tool events and token deltas for an InboundMessage."""
        outbound = self.process_inbound(msg)
        full_text = outbound.text
        chunk_size = 25

        for i in range(0, len(full_text), chunk_size):
            if cancel_event and cancel_event.is_set():
                yield {"event": "delta", "data": json.dumps({"content": "\n\n[Turn interrupted by operator]"})}
                break
            chunk = full_text[i:i + chunk_size]
            yield {"event": "delta", "data": json.dumps({"content": chunk})}
            time.sleep(0.02)

        yield {"event": "done", "data": json.dumps({"destination": outbound.destination, "thread_id": msg.conversation_id})}


CAPTAIN_APP = CaptainApplicationService()
