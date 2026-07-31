import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[0]))

import database
import server as server_module
from engine import CaptainEngine
from model_provider import ProviderResponse
from usage_budget import UsageBudget

ORIGIN = next(iter(server_module.ALLOWED_ORIGINS))


class ScriptedProvider:
    name = "Fake"
    model = "fake-1"

    def __init__(self):
        self.script: list[str] = []

    def generate(self, system_prompt, messages, limits, sandbox="read-only"):
        text = self.script.pop(0) if self.script else "OK.\n```captain-json\n{}\n```"
        return ProviderResponse(
            text=text, provider=self.name, model=self.model,
            input_tokens=1, output_tokens=1, total_tokens=2, finish_reason="completed",
        )


class ApiTests(unittest.TestCase):
    # No app-level login: access control is the LAN-only Caddy site block
    # this service is deployed behind (docs/deployment.md), not anything
    # this server enforces itself. Each test still gets its own
    # server/engine/data dir so chat-turn state doesn't bleed across tests.
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        data_dir = Path(self._tmp.name)
        self.conn = database.connect(data_dir / "captain.sqlite3")
        self.provider = ScriptedProvider()
        self.engine = CaptainEngine(
            provider=self.provider, conn=self.conn, budget=UsageBudget(data_dir / "usage.json"),
            seed_instruction="SEED", data_dir=data_dir,
        )
        self.http_server = server_module.CaptainServer(
            ("127.0.0.1", 0), server_module.Handler, self.engine, self.conn
        )
        self.port = self.http_server.server_address[1]
        self.thread = threading.Thread(target=self.http_server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.http_server.shutdown()
        self.http_server.server_close()
        self.engine.close()
        self.conn.close()
        self._tmp.cleanup()

    def _url(self, path: str) -> str:
        return f"http://127.0.0.1:{self.port}{path}"

    def _post(self, path, payload):
        data = json.dumps(payload).encode()
        request = urllib.request.Request(
            self._url(path), data=data, method="POST",
            headers={"Content-Type": "application/json", "Origin": ORIGIN},
        )
        try:
            response = urllib.request.urlopen(request)
            return response.status, json.loads(response.read())
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read())

    def _get(self, path):
        request = urllib.request.Request(self._url(path))
        try:
            response = urllib.request.urlopen(request)
            return response.status, json.loads(response.read())
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read())

    def test_state_request_succeeds_with_no_login(self):
        status, body = self._get("/api/state")
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        self.assertEqual(body["state"]["current_mode"], database.DEFAULT_MODE)

    def test_post_from_disallowed_origin_is_rejected(self):
        data = json.dumps({"message": "hello"}).encode()
        request = urllib.request.Request(
            self._url("/api/chat"), data=data, method="POST",
            headers={"Content-Type": "application/json", "Origin": "https://evil.example"},
        )
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(request)
        self.assertEqual(ctx.exception.code, 403)

    def test_chat_round_trip(self):
        self.provider.script = ["Understood.\n```captain-json\n{}\n```"]
        status, body = self._post("/api/chat", {"message": "hello captain"})
        self.assertEqual(status, 200)
        self.assertEqual(body["reply"], "Understood.")

        status, body = self._get("/api/messages")
        self.assertEqual(status, 200)
        self.assertEqual(body["messages"][-2]["content"], "hello captain")
        self.assertEqual(body["messages"][-1]["content"], "Understood.")

    def test_mode_change_is_logged_and_persisted(self):
        status, body = self._post("/api/mode", {"mode": "design", "reason": "starting design work"})
        self.assertEqual(status, 200)
        self.assertEqual(body["state"]["current_mode"], "design")

        status, body = self._post("/api/mode", {"mode": "not_a_mode"})
        self.assertEqual(status, 400)

    def test_harvest_accept_requires_dedicated_endpoint(self):
        self.provider.script = [
            "Noted.\n```captain-json\n"
            '{"reply": "Noted.", "harvest_proposals": [{"type": "principle", '
            '"title": "Test", "summary": "S", "confidence": 0.7}]}\n```'
        ]
        self._post("/api/chat", {"message": "remember this"})

        status, body = self._get("/api/harvest?status=candidate")
        self.assertEqual(status, 200)
        candidates = [item for item in body["items"] if item["title"] == "Test"]
        self.assertEqual(len(candidates), 1)
        item_id = candidates[0]["id"]
        self.assertEqual(candidates[0]["status"], "candidate")

        status, body = self._post(f"/api/harvest/{item_id}/accept", {})
        self.assertEqual(status, 200)
        self.assertEqual(body["item"]["status"], "accepted")

    def test_brief_returns_current_state_projection(self):
        fake_state = {
            "generated_at": "2026-07-31T00:00:00+00:00",
            "projection": True,
            "active_course": {"mission": "M", "goal": "G", "next_action": "N"},
            "established_truth": ["T1"],
            "decisions": ["D1"],
            "defects": ["X1"],
        }
        with mock.patch.object(server_module, "BRIEF_PATH", mock.Mock(
            read_text=mock.Mock(return_value=json.dumps(fake_state))
        )):
            status, body = self._get("/api/brief")
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        self.assertEqual(body["brief"]["active_course"]["mission"], "M")
        self.assertEqual(body["brief"]["established_truth"], ["T1"])

    def test_brief_missing_file_returns_503(self):
        missing = Path(self._tmp.name) / "does-not-exist.json"
        with mock.patch.object(server_module, "BRIEF_PATH", missing):
            status, body = self._get("/api/brief")
        self.assertEqual(status, 503)
        self.assertFalse(body["ok"])

    def test_image_status_not_found(self):
        status, body = self._get("/api/image/does-not-exist")
        self.assertEqual(status, 404)
        self.assertFalse(body["ok"])

    def test_image_file_not_ready(self):
        job = database.create_image_job(self.conn, session_id="sess-x", prompt="a ship")
        status, body = self._get(f"/api/image/{job['id']}/file")
        self.assertEqual(status, 404)
        self.assertFalse(body["ok"])


class FakeImageGenerator:
    def __init__(self, artifacts_dir: Path):
        self.artifacts_dir = artifacts_dir
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.conn = None

    def submit(self, session_id, prompt):
        job = database.create_image_job(self.conn, session_id=session_id, prompt=prompt)
        content = b"\xff\xd8\xff fake jpeg"
        name = f"{job['id']}.jpg"
        (self.artifacts_dir / name).write_bytes(content)
        return database.update_image_job(
            self.conn, job["id"], status="succeeded", artifact_name=name, artifact_mime="image/jpeg",
        )

    def artifact_path(self, job):
        if not job.get("artifact_name"):
            return None
        path = self.artifacts_dir / job["artifact_name"]
        return path if path.exists() else None


class ImageApiTests(unittest.TestCase):
    """Separate from ApiTests -- needs a server/engine wired with an
    image_generator, unlike the plain setUp shared by the rest of the suite."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        data_dir = Path(self._tmp.name)
        self.conn = database.connect(data_dir / "captain.sqlite3")
        self.provider = ScriptedProvider()
        self.image_generator = FakeImageGenerator(data_dir / "images")
        self.image_generator.conn = self.conn
        self.engine = CaptainEngine(
            provider=self.provider, conn=self.conn, budget=UsageBudget(data_dir / "usage.json"),
            seed_instruction="SEED", data_dir=data_dir, image_generator=self.image_generator,
        )
        self.http_server = server_module.CaptainServer(
            ("127.0.0.1", 0), server_module.Handler, self.engine, self.conn, self.image_generator
        )
        self.port = self.http_server.server_address[1]
        self.thread = threading.Thread(target=self.http_server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.http_server.shutdown()
        self.http_server.server_close()
        self.engine.close()
        self.conn.close()
        self._tmp.cleanup()

    def _url(self, path: str) -> str:
        return f"http://127.0.0.1:{self.port}{path}"

    def _post(self, path, payload):
        data = json.dumps(payload).encode()
        request = urllib.request.Request(
            self._url(path), data=data, method="POST",
            headers={"Content-Type": "application/json", "Origin": ORIGIN},
        )
        try:
            response = urllib.request.urlopen(request)
            return response.status, json.loads(response.read())
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read())

    def _get(self, path):
        request = urllib.request.Request(self._url(path))
        try:
            response = urllib.request.urlopen(request)
            return response.status, response.read(), dict(response.headers)
        except urllib.error.HTTPError as error:
            return error.code, error.read(), dict(error.headers)

    def test_chat_with_image_request_creates_a_servable_image(self):
        self.provider.script = [
            "Generating that now.\n```captain-json\n"
            '{"reply": "Generating that now.", "image_request": "a red ship on a calm sea"}\n```'
        ]
        status, body = self._post("/api/chat", {"message": "draw me a ship"})
        self.assertEqual(status, 200)
        self.assertIsNotNone(body["image_job"])
        self.assertEqual(body["image_job"]["status"], "succeeded")
        job_id = body["image_job"]["id"]

        status, raw, headers = self._get(f"/api/image/{job_id}")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(raw)["job"]["status"], "succeeded")

        status, raw, headers = self._get(f"/api/image/{job_id}/file")
        self.assertEqual(status, 200)
        self.assertEqual(headers.get("Content-Type"), "image/jpeg")
        self.assertEqual(raw, b"\xff\xd8\xff fake jpeg")

    def test_message_history_carries_image_job_id(self):
        self.provider.script = [
            "OK.\n```captain-json\n{\"reply\": \"OK.\", \"image_request\": \"a lighthouse\"}\n```"
        ]
        self._post("/api/chat", {"message": "draw a lighthouse"})
        request = urllib.request.Request(self._url("/api/messages"))
        response = urllib.request.urlopen(request)
        messages = json.loads(response.read())["messages"]
        assistant = [m for m in messages if m["role"] == "assistant"][0]
        self.assertIsNotNone(assistant["image_job_id"])


if __name__ == "__main__":
    unittest.main()
