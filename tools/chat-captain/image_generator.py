"""Background text-to-image job runner for Chat Captain.

Calls the same Gemini image endpoint already proven live in
tools/living-captain-workbench/service.py (Captain Workbench Beast Image),
simplified for pure text-to-image (no input schematic). Jobs run on a
background worker thread so a chat turn returns immediately with a job id
instead of blocking on image generation; the ship's own SQLite state
(image_jobs table) is the durable record of status, matching this
project's continuity-belongs-to-the-ship principle -- not something held
only in this process's memory.
"""

from __future__ import annotations

import base64
import json
import queue
import sqlite3
import threading
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import database

MODEL = "gemini-3.1-flash-image"
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/interactions"


def extract_image(value: object) -> tuple[bytes, str] | None:
    """Tolerate REST response shape changes while requiring an explicit image MIME type."""
    if isinstance(value, dict):
        mime = value.get("mime_type") or value.get("mimeType")
        data = value.get("data")
        if isinstance(mime, str) and mime.startswith("image/") and isinstance(data, str):
            try:
                return base64.b64decode(data, validate=True), mime
            except (ValueError, base64.binascii.Error):
                pass
        for child in value.values():
            found = extract_image(child)
            if found:
                return found
    elif isinstance(value, list):
        for child in value:
            found = extract_image(child)
            if found:
                return found
    return None


class ImageGenerator:
    def __init__(self, conn: sqlite3.Connection, api_key: str, artifacts_dir: Path, transport=urlopen):
        self.conn = conn
        self.api_key = api_key
        self.artifacts_dir = Path(artifacts_dir)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.transport = transport
        self._queue: queue.Queue[str] = queue.Queue()
        self._lock = threading.Lock()
        threading.Thread(target=self._worker, daemon=True, name="image-generator").start()

    def submit(self, session_id: str, prompt: str) -> dict:
        with self._lock:
            job = database.create_image_job(self.conn, session_id=session_id, prompt=prompt)
        self._queue.put(job["id"])
        return job

    def artifact_path(self, job: dict) -> Path | None:
        if not job.get("artifact_name"):
            return None
        path = self.artifacts_dir / job["artifact_name"]
        return path if path.exists() else None

    def _worker(self) -> None:
        while True:
            job_id = self._queue.get()
            try:
                self._execute(job_id)
            finally:
                self._queue.task_done()

    def _execute(self, job_id: str) -> None:
        with self._lock:
            job = database.get_image_job(self.conn, job_id)
            if not job:
                return
            database.update_image_job(self.conn, job_id, status="running")

        payload = {
            "model": MODEL,
            "input": [{"type": "text", "text": job["prompt"]}],
            "response_format": {"type": "image", "mime_type": "image/jpeg", "aspect_ratio": "1:1", "image_size": "1K"},
        }
        request = Request(
            ENDPOINT, data=json.dumps(payload).encode("utf-8"), method="POST",
            headers={"Content-Type": "application/json", "x-goog-api-key": self.api_key},
        )
        try:
            with self.transport(request, timeout=180) as response:
                result = json.loads(response.read())
            image = extract_image(result)
            if not image:
                raise ValueError("provider returned no readable image")
            content, mime = image
            suffix = ".png" if mime == "image/png" else ".jpg"
            name = f"{job_id}{suffix}"
            (self.artifacts_dir / name).write_bytes(content)
            with self._lock:
                database.update_image_job(
                    self.conn, job_id, status="succeeded", artifact_name=name, artifact_mime=mime,
                )
        except (HTTPError, URLError, TimeoutError, ValueError, OSError, json.JSONDecodeError) as error:
            detail = f"provider HTTP {error.code}" if isinstance(error, HTTPError) else type(error).__name__
            with self._lock:
                database.update_image_job(self.conn, job_id, status="failed", error=detail)
