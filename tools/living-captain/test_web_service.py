import http.client
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import web_service
from conversation import ConversationStore
from live_captain_engine import CaptainEngine, OwnershipError
from model_provider import ProviderResponse
from usage_budget import UsageBudget


class FakeProvider:
    name = "Fake"
    model = "fake-web-v1"

    def generate(self, system_prompt, messages, limits):
        return ProviderResponse(
            text="Aye, Admiral. Web path verified.",
            provider=self.name,
            model=self.model,
            input_tokens=10,
            output_tokens=6,
            total_tokens=16,
            finish_reason="STOP",
        )


def auth_config(password="correct horse battery"):
    import hashlib

    salt = b"s" * 16
    digest = hashlib.scrypt(
        password.encode(),
        salt=salt,
        n=2**14,
        r=8,
        p=1,
        dklen=32,
    )
    return web_service.AuthConfig(salt, digest, b"k" * 32)


class WebServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        data = Path(self.temp.name)
        self.engine = CaptainEngine(
            provider=FakeProvider(),
            store=ConversationStore(data),
            budget=UsageBudget(data / "usage.json"),
            system_prompt="Captain system prompt",
        )
        self.server = web_service.ConferenceServer(
            ("127.0.0.1", 0),
            web_service.Handler,
            self.engine,
            auth_config(),
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.host, self.port = self.server.server_address

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.engine.close()
        self.temp.cleanup()

    def request(self, method, path, body=None, cookie=None, origin=None):
        connection = http.client.HTTPConnection(self.host, self.port, timeout=3)
        headers = {}
        payload = None
        if body is not None:
            payload = json.dumps(body)
            headers["Content-Type"] = "application/json"
        if cookie:
            headers["Cookie"] = cookie
        if origin:
            headers["Origin"] = origin
        connection.request(method, path, body=payload, headers=headers)
        response = connection.getresponse()
        data = json.loads(response.read())
        result = response.status, dict(response.getheaders()), data
        connection.close()
        return result

    def login(self):
        status, headers, body = self.request(
            "POST",
            "/login",
            {"password": "correct horse battery"},
            origin=web_service.ALLOWED_ORIGIN,
        )
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        cookie = headers["Set-Cookie"].split(";", 1)[0]
        self.assertIn("HttpOnly", headers["Set-Cookie"])
        self.assertIn("Secure", headers["Set-Cookie"])
        self.assertIn("SameSite=Strict", headers["Set-Cookie"])
        return cookie

    def test_health_is_public_but_transcript_is_not(self):
        status, _, body = self.request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        status, _, body = self.request("GET", "/messages")
        self.assertEqual(status, 401)
        self.assertFalse(body["ok"])

    def test_wrong_origin_is_rejected_before_password_check(self):
        status, _, body = self.request(
            "POST",
            "/login",
            {"password": "correct horse battery"},
            origin="https://example.invalid",
        )
        self.assertEqual(status, 403)
        self.assertEqual(body["error"], "origin rejected")

    def test_login_attempts_are_bounded(self):
        for _ in range(web_service.LOGIN_ATTEMPTS_PER_WINDOW):
            status, _, _ = self.request(
                "POST",
                "/login",
                {"password": "wrong password"},
                origin=web_service.ALLOWED_ORIGIN,
            )
            self.assertEqual(status, 401)
        status, _, body = self.request(
            "POST",
            "/login",
            {"password": "wrong password"},
            origin=web_service.ALLOWED_ORIGIN,
        )
        self.assertEqual(status, 429)
        self.assertEqual(body["error"], "login temporarily limited")

    def test_authenticated_message_persists_and_returns_usage(self):
        cookie = self.login()
        status, _, body = self.request(
            "POST",
            "/messages",
            {"message": "Report your limits."},
            cookie=cookie,
            origin=web_service.ALLOWED_ORIGIN,
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["reply"], "Aye, Admiral. Web path verified.")
        self.assertEqual(body["usage"]["request_count"], 1)

        status, _, transcript = self.request("GET", "/messages", cookie=cookie)
        self.assertEqual(status, 200)
        self.assertEqual(
            [message["role"] for message in transcript["messages"]],
            ["user", "assistant"],
        )

    def test_session_signature_and_expiry(self):
        auth = auth_config()
        token = auth.issue_session(now=1_000)
        self.assertTrue(auth.verify_session(token, now=1_001))
        self.assertFalse(
            auth.verify_session(token, now=1_000 + web_service.SESSION_SECONDS + 1)
        )
        self.assertFalse(auth.verify_session(token + "tampered", now=1_001))

    def test_single_owner_rejects_second_engine(self):
        with self.assertRaisesRegex(OwnershipError, "already owns"):
            CaptainEngine(
                provider=FakeProvider(),
                store=ConversationStore(Path(self.temp.name)),
                budget=UsageBudget(Path(self.temp.name) / "usage.json"),
                system_prompt="Captain system prompt",
            )


if __name__ == "__main__":
    unittest.main()
