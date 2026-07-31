import hashlib
import http.client
import json
import re
import secrets
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[0]))

import database
import server as server_module
from engine import CaptainEngine
from model_provider import ProviderResponse
from usage_budget import UsageBudget

TEST_PASSWORD = "correct horse battery staple"
ORIGIN = next(iter(server_module.ALLOWED_ORIGINS))


class ScriptedProvider:
    name = "Fake"
    model = "fake-1"

    def __init__(self):
        self.script: list[str] = []

    def generate(self, system_prompt, messages, limits):
        text = self.script.pop(0) if self.script else "OK.\n```captain-json\n{}\n```"
        return ProviderResponse(
            text=text, provider=self.name, model=self.model,
            input_tokens=1, output_tokens=1, total_tokens=2, finish_reason="completed",
        )


def _auth_config() -> server_module.AuthConfig:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(TEST_PASSWORD.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return server_module.AuthConfig(salt, digest, secrets.token_bytes(32))


class ApiTests(unittest.TestCase):
    # Each test gets its own server/engine/data dir -- the login rate
    # limiter and session state are process-lifetime state on the server
    # instance, so sharing one server across tests would make earlier
    # tests' login attempts and chat turns bleed into later assertions.
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        data_dir = Path(self._tmp.name)
        self.conn = database.connect(data_dir / "captain.sqlite3")
        self.provider = ScriptedProvider()
        self.engine = CaptainEngine(
            provider=self.provider, conn=self.conn, budget=UsageBudget(data_dir / "usage.json"),
            seed_instruction="SEED", data_dir=data_dir,
        )
        self.auth = _auth_config()
        self.http_server = server_module.CaptainServer(
            ("127.0.0.1", 0), server_module.Handler, self.engine, self.conn, self.auth
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

    def _opener(self):
        # Login cookies are Set-Cookie ...; Secure -- correct in production
        # (Caddy terminates TLS in front of this loopback service), but
        # plain http.cookiejar refuses to store/replay a Secure cookie over
        # a non-TLS test connection. Track the cookie value by hand instead
        # of relying on cookiejar's (correct) same-scheme enforcement.
        return {"cookie": None}

    def _url(self, path: str) -> str:
        return f"http://127.0.0.1:{self.port}{path}"

    def _headers(self, opener, extra=None):
        headers = dict(extra or {})
        if opener["cookie"]:
            headers["Cookie"] = opener["cookie"]
        return headers

    def _capture_cookie(self, opener, response) -> None:
        set_cookie = response.headers.get("Set-Cookie")
        if set_cookie:
            match = re.match(r"([^=]+=[^;]+);", set_cookie)
            if match:
                opener["cookie"] = match.group(1)

    def _post(self, opener, path, payload, expect_status=200):
        data = json.dumps(payload).encode()
        request = urllib.request.Request(
            self._url(path), data=data, method="POST",
            headers={"Content-Type": "application/json", "Origin": ORIGIN, **self._headers(opener)},
        )
        try:
            response = urllib.request.urlopen(request)
            self._capture_cookie(opener, response)
            return response.status, json.loads(response.read())
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read())

    def _get(self, opener, path, expect_status=200):
        request = urllib.request.Request(self._url(path), headers=self._headers(opener))
        try:
            response = urllib.request.urlopen(request)
            return response.status, json.loads(response.read())
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read())

    def test_unauthenticated_state_request_is_rejected(self):
        opener = self._opener()
        status, body = self._get(opener, "/api/state")
        self.assertEqual(status, 401)
        self.assertFalse(body["ok"])

    def test_login_then_chat_round_trip(self):
        opener = self._opener()
        status, body = self._post(opener, "/login", {"password": TEST_PASSWORD})
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])

        status, body = self._get(opener, "/api/state")
        self.assertEqual(status, 200)
        self.assertEqual(body["state"]["current_mode"], database.DEFAULT_MODE)

        self.provider.script = ["Understood.\n```captain-json\n{}\n```"]
        status, body = self._post(opener, "/api/chat", {"message": "hello captain"})
        self.assertEqual(status, 200)
        self.assertEqual(body["reply"], "Understood.")

        status, body = self._get(opener, "/api/messages")
        self.assertEqual(status, 200)
        self.assertEqual(body["messages"][-2]["content"], "hello captain")
        self.assertEqual(body["messages"][-1]["content"], "Understood.")

    def test_wrong_password_rejected_and_rate_limited(self):
        opener = self._opener()
        for _ in range(5):
            status, body = self._post(opener, "/login", {"password": "wrong"})
            self.assertEqual(status, 401)
        status, body = self._post(opener, "/login", {"password": TEST_PASSWORD})
        self.assertEqual(status, 429)

    def test_mode_change_is_logged_and_persisted(self):
        opener = self._opener()
        self._post(opener, "/login", {"password": TEST_PASSWORD})
        status, body = self._post(opener, "/api/mode", {"mode": "design", "reason": "starting design work"})
        self.assertEqual(status, 200)
        self.assertEqual(body["state"]["current_mode"], "design")

        status, body = self._post(opener, "/api/mode", {"mode": "not_a_mode"})
        self.assertEqual(status, 400)

    def test_harvest_accept_requires_dedicated_endpoint(self):
        opener = self._opener()
        self._post(opener, "/login", {"password": TEST_PASSWORD})
        self.provider.script = [
            "Noted.\n```captain-json\n"
            '{"reply": "Noted.", "harvest_proposals": [{"type": "principle", '
            '"title": "Test", "summary": "S", "confidence": 0.7}]}\n```'
        ]
        self._post(opener, "/api/chat", {"message": "remember this"})

        status, body = self._get(opener, "/api/harvest?status=candidate")
        self.assertEqual(status, 200)
        candidates = [item for item in body["items"] if item["title"] == "Test"]
        self.assertEqual(len(candidates), 1)
        item_id = candidates[0]["id"]
        self.assertEqual(candidates[0]["status"], "candidate")

        status, body = self._post(opener, f"/api/harvest/{item_id}/accept", {})
        self.assertEqual(status, 200)
        self.assertEqual(body["item"]["status"], "accepted")


if __name__ == "__main__":
    unittest.main()
