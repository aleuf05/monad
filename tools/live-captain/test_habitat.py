"""Unit & Integration tests for Captain Habitat Backend & Persistence Engine."""

from __future__ import annotations

import json
import socket
import sys
import unittest
import urllib.request
from pathlib import Path
from threading import Thread
from time import sleep

ROOT_DIR = Path(__file__).resolve().parent
REPO_ROOT = ROOT_DIR.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from habitat_store import HabitatStore
from habitat_server import run_server


class TestHabitatStore(unittest.TestCase):
    def setUp(self):
        self.tmp_db = REPO_ROOT / "data" / "test_habitat.db"
        if self.tmp_db.exists():
            self.tmp_db.unlink()
        self.store = HabitatStore(self.tmp_db)

    def tearDown(self):
        for suffix in ("", "-wal", "-shm"):
            p = self.tmp_db.parent / (self.tmp_db.name + suffix)
            if p.exists():
                try:
                    p.unlink()
                except OSError:
                    pass

    def test_thread_crud(self):
        t = self.store.create_thread("Test Mission")
        self.assertTrue(t["id"].startswith("thread-"))
        self.assertEqual(t["title"], "Test Mission")

        threads = self.store.list_threads()
        self.assertEqual(len(threads), 1)

        msg = self.store.add_message(t["id"], "admiral", "Report status")
        self.assertEqual(msg["role"], "admiral")

        loaded = self.store.get_thread(t["id"])
        self.assertIsNotNone(loaded)
        self.assertEqual(len(loaded["messages"]), 1)
        self.assertEqual(loaded["messages"][0]["text"], "Report status")

    def test_heart_lessons(self):
        h = self.store.add_heart_lesson("Always sound the ship before reporting", "Operator correction")
        self.assertTrue(h["id"].startswith("heart-"))

        lessons = self.store.get_heart_lessons()
        self.assertEqual(len(lessons), 1)
        self.assertIn("sound the ship", lessons[0]["lesson"])


class TestHabitatServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", 0))
        cls.port = s.getsockname()[1]
        s.close()

        cls.server_thread = Thread(target=run_server, kwargs={"host": "127.0.0.1", "port": cls.port}, daemon=True)
        cls.server_thread.start()
        sleep(0.4)

    def test_status_endpoint(self):
        url = f"http://127.0.0.1:{self.port}/captain-api/status"
        with urllib.request.urlopen(url) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["status"], "ok")
            self.assertEqual(data["service"], "captain-habitat")

    def test_thread_lifecycle(self):
        # Create thread
        url = f"http://127.0.0.1:{self.port}/captain-api/threads"
        payload = json.dumps({"title": "Test Stream Thread"}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            thread = json.loads(resp.read().decode("utf-8"))
            thread_id = thread["id"]

        # Chat SSE turn
        chat_url = f"http://127.0.0.1:{self.port}/captain-api/chat"
        chat_payload = json.dumps({"thread_id": thread_id, "prompt": "sound the ship"}).encode("utf-8")
        chat_req = urllib.request.Request(chat_url, data=chat_payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(chat_req) as resp:
            self.assertEqual(resp.status, 200)
            stream_body = resp.read().decode("utf-8")
            self.assertIn("event: delta", stream_body)
            self.assertIn("event: done", stream_body)


if __name__ == "__main__":
    unittest.main()
