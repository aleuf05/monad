"""Unit tests for the Canonical Communication Layer & Authority Boundary."""

from __future__ import annotations

import unittest
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from comms import (
    Action,
    AuthorityBoundary,
    AuthorityLevel,
    InboundMessage,
    MediaItem,
    OutboundMessage,
    TelegramChannelAdapter,
    Urgency,
    WebChannelAdapter,
)


class TestCommsModel(unittest.TestCase):
    def test_media_and_action_serialization(self):
        media = MediaItem(media_type="image", url="/images/kraken.png", alt="Kraken 3D")
        self.assertEqual(media.to_dict()["url"], "/images/kraken.png")

        action = Action(id="act-1", label="Approve", intent="approve_mission", authority_level="authorized")
        self.assertEqual(action.to_dict()["id"], "act-1")

        msg = OutboundMessage(
            destination="phone_web",
            text="Station ready",
            media=[media],
            actions=[action],
            urgency=Urgency.HIGH.value,
        )
        data = msg.to_dict()
        self.assertEqual(data["destination"], "phone_web")
        self.assertEqual(len(data["media"]), 1)
        self.assertEqual(len(data["actions"]), 1)

        restored = OutboundMessage.from_dict(data)
        self.assertEqual(restored.text, "Station ready")
        self.assertEqual(restored.media[0].url, "/images/kraken.png")
        self.assertEqual(restored.actions[0].id, "act-1")

    def test_authority_boundary_assessment(self):
        self.assertEqual(AuthorityBoundary.assess("Explain how Caddy routes work"), AuthorityLevel.CONVERSATIONAL)
        self.assertEqual(AuthorityBoundary.assess("Prepare to restart Caddy"), AuthorityLevel.PROPOSED)
        self.assertEqual(AuthorityBoundary.assess("systemctl restart root-console"), AuthorityLevel.PRIVILEGED_STAGED)
        self.assertEqual(AuthorityBoundary.assess("sudo service restart"), AuthorityLevel.PRIVILEGED_STAGED)
        self.assertEqual(AuthorityBoundary.assess("sound the ship"), AuthorityLevel.AUTHORIZED)

    def test_web_channel_adapter(self):
        adapter = WebChannelAdapter()
        raw_in = {
            "thread_id": "thread-123",
            "prompt": "Test input",
            "attachments": [{"filename": "sample.png", "path": "/tmp/sample.png"}],
        }
        inbound = adapter.parse_inbound(raw_in)
        self.assertEqual(inbound.conversation_id, "thread-123")
        self.assertEqual(inbound.text, "Test input")
        self.assertEqual(len(inbound.media), 1)

        outbound = OutboundMessage(destination="client-1", text="Status OK")
        formatted = adapter.format_outbound(outbound)
        self.assertEqual(formatted["type"], "message")
        self.assertEqual(formatted["text"], "Status OK")

    def test_telegram_channel_adapter(self):
        adapter = TelegramChannelAdapter()
        outbound = OutboundMessage(
            destination="tg-chat",
            text="Mission Report",
            semantic_role="engineering",
            actions=[Action(id="a1", label="Inspect", intent="inspect")],
        )
        formatted = adapter.format_outbound(outbound)
        self.assertTrue(formatted["text"].startswith("🔧 "))
        self.assertIn("reply_markup", formatted)
        self.assertEqual(len(formatted["reply_markup"]["inline_keyboard"]), 1)


if __name__ == "__main__":
    unittest.main()
