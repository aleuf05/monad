#!/usr/bin/env python3
"""Authenticated, durable work queue for narrowly authorized Live Captain jobs."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import queue
import re
import secrets
import threading
import time
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from codex_bridge import CodexBridge

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "living-captain-workbench"
HOST = "127.0.0.1"
PORT = 4791
ORIGIN = "https://cameronlampley.com"
COOKIE = "monad_captain_session"
SESSION_SECONDS = 12 * 60 * 60
MAX_BODY = 3_000_000
MAX_DAILY_JOBS = int(os.environ.get("CAPTAIN_WORKBENCH_DAILY_LIMIT", "5"))
MODEL = os.environ.get("CAPTAIN_WORKBENCH_IMAGE_MODEL", "gemini-3.1-flash-image")
LIVE_ENABLED = os.environ.get("CAPTAIN_WORKBENCH_LIVE_ENABLED", "").lower() in {"1", "true", "yes"}
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/interactions"
ID_RE = re.compile(r"^[a-f0-9]{24}$")


def now() -> str:
    return datetime.now(UTC).isoformat()


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def observe(job: dict, stage: str, message: str, source: str) -> None:
    """Append an observed fact; stages are evidence, never completion estimates."""
    observed_at = now()
    job.setdefault("observations", []).append({
        "stage": stage,
        "message": message,
        "source": source,
        "observed_at": observed_at,
    })
    job.update(updated_at=observed_at, note=message)


class SessionVerifier:
    def __init__(self, secret: bytes):
        self.secret = secret

    @classmethod
    def from_environment(cls) -> "SessionVerifier":
        try:
            return cls(bytes.fromhex(os.environ["LIVE_CAPTAIN_SESSION_SECRET"]))
        except (KeyError, ValueError) as error:
            raise ValueError("Captain session authentication is not configured") from error

    def verify(self, token: str) -> bool:
        try:
            timestamp_text, nonce, supplied = token.split(".", 2)
            timestamp = int(timestamp_text)
        except (ValueError, AttributeError):
            return False
        current = int(time.time())
        if timestamp > current + 60 or current - timestamp > SESSION_SECONDS:
            return False
        payload = f"{timestamp}.{nonce}".encode("ascii")
        expected = base64.urlsafe_b64encode(
            hmac.new(self.secret, payload, hashlib.sha256).digest()
        ).decode("ascii").rstrip("=")
        return hmac.compare_digest(expected, supplied)


def validate_recipe(value: object) -> dict:
    if not isinstance(value, dict):
        raise ValueError("recipe must be an object")
    if value.get("schema") == "monad.beastscapeSpecimen.v0.1":
        required = {"schema", "v", "f", "type", "region", "nodes", "edges", "id"}
        if not required.issubset(value):
            raise ValueError("Beastscape specimen fields are incomplete")
        if not isinstance(value["v"], list) or len(value["v"]) != 3 or any(not isinstance(n, (int, float)) or isinstance(n, bool) or not 0 <= n <= 1 for n in value["v"]):
            raise ValueError("Beastscape bearings are invalid")
        if not isinstance(value["nodes"], list) or not 1 <= len(value["nodes"]) <= 500:
            raise ValueError("Beastscape node graph is invalid")
        if not isinstance(value["edges"], list) or len(value["edges"]) > 1000:
            raise ValueError("Beastscape edge graph is invalid")
        if not isinstance(value["region"], str) or not isinstance(value["id"], str):
            raise ValueError("Beastscape identity is invalid")
        return value
    expected = {
        "schema", "family", "symmetry", "branch_depth", "reach",
        "curl", "irregularity", "terminal", "seed", "id",
    }
    if set(value) != expected:
        raise ValueError("recipe fields do not match beastDefinition.v0.1")
    if value["schema"] != "monad.beastDefinition.v0.1" or value["family"] != "radial-hydra":
        raise ValueError("unsupported beast recipe")
    ranges = {
        "symmetry": (3, 12), "branch_depth": (0, 3), "reach": (.35, .9),
        "curl": (-.8, .8), "irregularity": (0, .6), "seed": (1, 999999),
    }
    for name, (low, high) in ranges.items():
        number = value[name]
        if not isinstance(number, (int, float)) or isinstance(number, bool) or not low <= number <= high:
            raise ValueError(f"recipe {name} is out of bounds")
    if value["terminal"] not in {"eye", "maw", "spike"}:
        raise ValueError("unsupported terminal organ")
    if not isinstance(value["id"], str) or len(value["id"]) > 80:
        raise ValueError("invalid recipe id")
    return value


def decode_schematic(data_url: object) -> bytes:
    if not isinstance(data_url, str) or not data_url.startswith("data:image/png;base64,"):
        raise ValueError("schematic_png must be a PNG data URL")
    try:
        image = base64.b64decode(data_url.split(",", 1)[1], validate=True)
    except (ValueError, base64.binascii.Error):
        raise ValueError("schematic PNG is invalid") from None
    if len(image) > 2_000_000 or not image.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("schematic PNG is invalid or too large")
    return image


def captain_prompt(recipe: dict) -> str:
    if recipe["schema"] == "monad.beastscapeSpecimen.v0.1":
        organs = sum(1 for node in recipe["nodes"] if node.get("role") == "organ")
        cores = sum(1 for node in recipe["nodes"] if node.get("role") == "core")
        return (
            "You are the visual interpretation station of the Live Captain Workbench. "
            "Transform the supplied Beastscape structural schematic into one polished square creature concept "
            "suitable as an image-to-3D source. The graph is authoritative. Preserve its complete connectivity, "
            f"regional organization ({recipe['region']}), {len(recipe['nodes'])} structural nodes, "
            f"{len(recipe['edges'])} relations, {cores} core nodes, and {organs} terminal organs. "
            "Show one complete coherent organism centered and fully inside frame on a plain dark neutral background. "
            "Add plausible tissue, mass, taper, surface differentiation, and restrained studio rim light without "
            "changing the skeleton. No text, diagram marks, labels, border, scenery, extra creatures, or cropped anatomy."
        )
    terminal = {"eye": "luminous watcher eyes", "maw": "small petal-like maws", "spike": "elegant signal spines"}[recipe["terminal"]]
    return (
        "You are the visual interpretation station of the Live Captain Workbench. "
        "Transform the supplied structural schematic into a polished square creature concept image "
        "suitable as an image-to-3D source. Preserve the schematic's radial topology and count: "
        f"exactly {recipe['symmetry']} primary limbs, branch depth {recipe['branch_depth']}, "
        f"relative reach {recipe['reach']:.2f}, curl {recipe['curl']:.2f}, and {terminal}. "
        f"Controlled irregularity is {recipe['irregularity']:.2f}; seed identity is {recipe['seed']}. "
        "Show one complete creature, centered, fully inside frame, on a plain dark neutral background. "
        "Use coherent anatomy, strong readable silhouette, subtle organic surface detail, studio rim light, "
        "and no text, diagram marks, labels, border, extra creatures, scenery, or cropped appendages. "
        "The schematic is authoritative geometry; artistic detail may enrich but must not contradict it."
    )


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


class Workbench:
    def __init__(self, data_dir: Path, api_key: str, transport=urlopen):
        self.data_dir = data_dir
        self.jobs_dir = data_dir / "jobs"
        self.artifacts_dir = data_dir / "artifacts"
        self.api_key = api_key
        self.transport = transport
        self.codex = None
        self.queue: queue.Queue[str] = queue.Queue()
        self.lock = threading.Lock()
        self.cancelled: set[str] = set()
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        for path in self.jobs_dir.glob("*.json"):
            job = json.loads(path.read_text(encoding="utf-8"))
            if job.get("status") in {"queued", "running"}:
                job.update(status="queued")
                observe(job, "recovered", "Job recovered after service restart.", "workbench")
                atomic_json(path, job)
                self.queue.put(job["id"])
        threading.Thread(target=self._worker, name="captain-workbench", daemon=True).start()

    def submit(self, recipe: dict, schematic: bytes, engine: str = "gemini") -> dict:
        if engine not in {"gemini", "codex"}:
            raise ValueError("unsupported Captain engine")
        if engine == "gemini" and not LIVE_ENABLED:
            raise PermissionError("paid generation is disarmed by the Captain Workbench")
        with self.lock:
            today = datetime.now(UTC).date().isoformat()
            consumed = sum(
                1 for path in self.jobs_dir.glob("*.json")
                if json.loads(path.read_text(encoding="utf-8")).get("created_at", "").startswith(today)
            )
            if consumed >= MAX_DAILY_JOBS:
                raise RuntimeError(f"daily Workbench limit reached ({MAX_DAILY_JOBS})")
            job_id = secrets.token_hex(12)
            source_path = self.artifacts_dir / f"{job_id}-schematic.png"
            source_path.write_bytes(schematic)
            job = {
                "schema": "monad.captainWorkbenchJob.v0.1",
                "id": job_id, "capability": "beast.image.enhance",
                "status": "queued", "created_at": now(), "updated_at": now(),
                "recipe": recipe, "engine": engine,
                "model": MODEL if engine == "gemini" else "codex-chatgpt-auth",
                "request_limit": 1,
                "request_count": 0, "artifact_available": False,
                "observations": [],
            }
            observe(job, "admitted", "Captain Workbench accepted the structural recipe.", "workbench")
            atomic_json(self.jobs_dir / f"{job_id}.json", job)
            self.queue.put(job_id)
            return job

    def get(self, job_id: str) -> dict | None:
        path = self.jobs_dir / f"{job_id}.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    def cancel(self, job_id: str) -> dict | None:
        with self.lock:
            job = self.get(job_id)
            if not job:
                return None
            if job.get("status") in {"succeeded", "failed", "cancelled"}:
                return job
            self.cancelled.add(job_id)
            job.update(status="cancelled", artifact_available=False)
            observe(
                job,
                "cancelled",
                "Workbench cancelled the run. Any provider call already in flight may finish remotely; its output will be discarded.",
                "operator",
            )
            atomic_json(self.jobs_dir / f"{job_id}.json", job)
            return job

    def is_cancelled(self, job_id: str) -> bool:
        with self.lock:
            return job_id in self.cancelled

    def artifact(self, job_id: str) -> tuple[Path, str] | None:
        job = self.get(job_id)
        if not job or not job.get("artifact_available"):
            return None
        path = self.artifacts_dir / job["artifact_name"]
        return (path, job["artifact_mime"]) if path.exists() else None

    def _worker(self) -> None:
        while True:
            job_id = self.queue.get()
            try:
                self._execute(job_id)
            finally:
                self.queue.task_done()

    def _execute(self, job_id: str) -> None:
        path = self.jobs_dir / f"{job_id}.json"
        job = self.get(job_id)
        if not job:
            return
        if job.get("status") == "cancelled" or self.is_cancelled(job_id):
            return
        job.update(status="running", request_count=1)
        observe(job, "worker_claimed", "Worker claimed the job.", "workbench")
        atomic_json(path, job)
        try:
            if job.get("engine") == "codex":
                self._execute_codex(path, job)
                return
            source = (self.artifacts_dir / f"{job_id}-schematic.png").read_bytes()
            payload = {
                "model": MODEL,
                "input": [
                    {"type": "text", "text": captain_prompt(job["recipe"])},
                    {"type": "image", "mime_type": "image/png", "data": base64.b64encode(source).decode("ascii")},
                ],
                "response_format": {"type": "image", "mime_type": "image/jpeg", "aspect_ratio": "1:1", "image_size": "1K"},
            }
            request = Request(
                ENDPOINT, data=json.dumps(payload).encode("utf-8"), method="POST",
                headers={"Content-Type": "application/json", "x-goog-api-key": self.api_key},
            )
            observe(job, "provider_request", "Gemini image request sent; provider exposes no intermediate completion telemetry.", "workbench")
            atomic_json(path, job)
            with self.transport(request, timeout=180) as response:
                result = json.loads(response.read())
            if self.is_cancelled(job_id):
                return
            observe(job, "provider_response", "Gemini returned a response.", "provider")
            atomic_json(path, job)
            image = extract_image(result)
            if not image:
                raise ValueError("provider returned no readable image")
            content, mime = image
            suffix = ".png" if mime == "image/png" else ".jpg"
            name = f"{job_id}{suffix}"
            (self.artifacts_dir / name).write_bytes(content)
            job.update(
                status="succeeded", artifact_available=True,
                artifact_name=name, artifact_mime=mime,
                provider_usage=result.get("usage", result.get("usageMetadata")),
            )
            observe(job, "artifact_ready", "Enhanced interpretation is stored and ready for review.", "workbench")
        except (HTTPError, URLError, TimeoutError, ValueError, OSError, json.JSONDecodeError) as error:
            detail = f"provider HTTP {error.code}" if isinstance(error, HTTPError) else type(error).__name__
            job.update(status="failed")
            observe(job, "failed", f"Enhancement failed safely: {detail}.", "workbench")
        atomic_json(path, job)

    def _execute_codex(self, path: Path, job: dict) -> None:
        source = self.artifacts_dir / f"{job['id']}-schematic.png"
        output = self.artifacts_dir / f"{job['id']}.png"

        def progress(method: str) -> None:
            observations = {
                "turn/started": ("captain_turn_started", "Live Captain turn started."),
                "item/started": ("captain_item_started", "Live Captain reported an item started."),
                "item/completed": ("captain_item_completed", "Live Captain reported an item completed."),
            }
            if method in observations:
                stage, message = observations[method]
                observe(job, stage, message, "codex_app_server")
                atomic_json(path, job)

        try:
            if self.codex is None:
                self.codex = CodexBridge(ROOT)
            self.codex.generate(captain_prompt(job["recipe"]), source, output, progress)
            if self.is_cancelled(job["id"]):
                output.unlink(missing_ok=True)
                return
            job.update(
                status="succeeded", artifact_available=True,
                artifact_name=output.name, artifact_mime="image/png",
            )
            observe(job, "artifact_ready", "Live Captain returned an image artifact.", "workbench")
        except (RuntimeError, TimeoutError, OSError, queue.Empty) as error:
            self.codex = None
            job.update(status="failed")
            observe(job, "failed", f"Live Captain failed safely: {str(error)[:180]}.", "workbench")
        atomic_json(path, job)


class Server(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, handler, workbench: Workbench):
        super().__init__(address, handler)
        self.workbench = workbench


class Handler(BaseHTTPRequestHandler):
    server: Server

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/health":
            self._json({
                "ok": True, "service": "living-captain-workbench",
                "model": MODEL, "paid_generation": "armed" if LIVE_ENABLED else "disarmed",
                "engines": ["gemini", "codex"],
                "codex_auth": "chatgpt-managed",
            })
            return
        match = re.fullmatch(r"/jobs/([a-f0-9]{24})(/image)?", path)
        if not match:
            self._json({"ok": False, "error": "not found"}, 404)
            return
        job_id, image_path = match.groups()
        if image_path:
            artifact = self.server.workbench.artifact(job_id)
            if not artifact:
                self._json({"ok": False, "error": "artifact not available"}, 404)
                return
            path, mime = artifact
            body = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "private, no-store")
            self.send_header("Content-Disposition", f'inline; filename="{path.name}"')
            self.end_headers()
            self.wfile.write(body)
            return
        job = self.server.workbench.get(job_id)
        self._json({"ok": True, "job": job}, 200 if job else 404)

    def do_POST(self) -> None:
        if self.headers.get("Origin") != ORIGIN:
            self._json({"ok": False, "error": "origin rejected"}, 403)
            return
        path = urlparse(self.path).path
        cancel_match = re.fullmatch(r"/jobs/([a-f0-9]{24})/cancel", path)
        if cancel_match:
            job = self.server.workbench.cancel(cancel_match.group(1))
            self._json(
                {"ok": bool(job), "job": job, "error": None if job else "job not found"},
                200 if job else 404,
            )
            return
        if path != "/jobs":
            self._json({"ok": False, "error": "not found"}, 404)
            return
        try:
            body = self._read_json()
            job = self.server.workbench.submit(
                validate_recipe(body.get("recipe")),
                decode_schematic(body.get("schematic_png")),
                body.get("engine", "gemini"),
            )
            self._json({"ok": True, "job": job}, 202)
        except ValueError as error:
            self._json({"ok": False, "error": str(error)}, 400)
        except PermissionError as error:
            self._json({"ok": False, "error": str(error)}, 423)
        except RuntimeError as error:
            self._json({"ok": False, "error": str(error)}, 429)

    def _read_json(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            raise ValueError("invalid Content-Length") from None
        if length < 1 or length > MAX_BODY:
            raise ValueError("request body is too large")
        try:
            value = json.loads(self.rfile.read(length))
        except json.JSONDecodeError:
            raise ValueError("request body must be JSON") from None
        if not isinstance(value, dict):
            raise ValueError("request body must be an object")
        return value

    def _json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args) -> None:  # noqa: A002
        pass


def main() -> int:
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise SystemExit("GEMINI_API_KEY is missing")
    workbench = Workbench(DATA_DIR, api_key)
    server = Server((HOST, PORT), Handler, workbench)
    print(f"Living Captain Workbench listening on http://{HOST}:{PORT}", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
