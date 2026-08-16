"""Unit tests for the Canonical Captain Application Service (Addendum A1)."""

from __future__ import annotations

import unittest
from pathlib import Path
import sys
import uuid

ROOT_DIR = Path(__file__).resolve().parent
REPO_ROOT = ROOT_DIR.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from captain_app import CaptainApplicationService
from comms import InboundMessage, MediaItem, OutboundMessage, Urgency
from habitat_store import HabitatStore


class TestCaptainApplicationService(unittest.TestCase):
    def setUp(self):
        self.tmp_db = REPO_ROOT / "data" / f"test_app_{uuid.uuid4().hex[:8]}.db"
        self.store = HabitatStore(self.tmp_db)
        self.app = CaptainApplicationService(self.store)

    def tearDown(self):
        for suffix in ("", "-wal", "-shm"):
            p = self.tmp_db.parent / (self.tmp_db.name + suffix)
            if p.exists():
                try:
                    p.unlink()
                except OSError:
                    pass

    def test_status_report(self):
        st = self.app.get_status()
        self.assertEqual(st["status"], "healthy")
        self.assertIn("ALL SYSTEMS SOUND", st["health_summary"])
        self.assertIn("Port 4777", st["phone_terminal"])

    def test_inbound_status_turn(self):
        msg = InboundMessage(
            channel="telegram",
            sender="admiral",
            conversation_id="tg-100",
            text="Captain, status.",
        )
        outbound = self.app.process_inbound(msg)
        self.assertIsInstance(outbound, OutboundMessage)
        self.assertEqual(outbound.destination, "telegram")
        self.assertIn("Live Captain Operational Status", outbound.text)
        self.assertIn("HEALTHY", outbound.text)

    def test_inbound_manual_consultation(self):
        msg = InboundMessage(
            channel="root_console",
            sender="admiral",
            conversation_id="console-1",
            text="Explain how agent delegation works",
        )
        outbound = self.app.process_inbound(msg)
        self.assertIn("Operator Manual Reference", outbound.text)
        self.assertIn("Agent Jobs", outbound.text)

    def test_inbound_streaming(self):
        msg = InboundMessage(
            channel="phone_web",
            sender="admiral",
            conversation_id="thread-test",
            text="What is your current bearing?",
        )
        events = list(self.app.stream_inbound(msg))
        self.assertTrue(len(events) > 1)
        self.assertEqual(events[-1]["event"], "done")


if __name__ == "__main__":
    unittest.main()
