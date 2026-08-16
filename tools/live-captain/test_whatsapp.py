"""WhatsApp Channel Adapter Test Suite & Interactive Runner.

Demonstrates and verifies WhatsApp integration with the Canonical Captain Application API.
Can be run as an automated test or used interactively:
    python3 tools/live-captain/test_whatsapp.py --send "Captain, status"
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import unittest

ROOT_DIR = Path(__file__).resolve().parent
REPO_ROOT = ROOT_DIR.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from captain_app import CAPTAIN_APP
from comms import InboundMessage, OutboundMessage, WhatsAppChannelAdapter


class TestWhatsAppAdapter(unittest.TestCase):
    def setUp(self):
        self.adapter = WhatsAppChannelAdapter()

    def test_parse_direct_payload(self):
        raw = {
            "From": "whatsapp:+15551234567",
            "Body": "Captain, what is our bearing?",
            "MessageSid": "SM1234567890",
        }
        inbound = self.adapter.parse_inbound(raw)
        self.assertEqual(inbound.channel, "whatsapp")
        self.assertEqual(inbound.sender, "admiral")
        self.assertEqual(inbound.text, "Captain, what is our bearing?")
        self.assertEqual(inbound.conversation_id, "wa-whatsapp:+15551234567")

    def test_parse_meta_cloud_webhook(self):
        meta_payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "100000000000000",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "messages": [{
                            "from": "15551234567",
                            "id": "wamid.HBgL...",
                            "timestamp": "1786898000",
                            "text": {"body": "Captain, are you healthy?"},
                            "type": "text"
                        }]
                    },
                    "field": "messages"
                }]
            }]
        }
        inbound = self.adapter.parse_inbound(meta_payload)
        self.assertEqual(inbound.channel, "whatsapp")
        self.assertEqual(inbound.text, "Captain, are you healthy?")
        self.assertEqual(inbound.conversation_id, "wa-15551234567")

    def test_whatsapp_turn_roundtrip(self):
        raw = {"From": "+15551234567", "Body": "Captain, status"}
        inbound = self.adapter.parse_inbound(raw)
        outbound = CAPTAIN_APP.process_inbound(inbound)
        
        self.assertIsInstance(outbound, OutboundMessage)
        formatted_wa = self.adapter.format_outbound(outbound)
        self.assertEqual(formatted_wa["messaging_product"], "whatsapp")
        self.assertIn("Live Captain Operational Status", formatted_wa["text"]["body"])


def run_interactive(prompt_text: str, phone_number: str = "+15550001234") -> None:
    adapter = WhatsAppChannelAdapter()
    print(f"\n📱 [WhatsApp Simulator] Sending message from {phone_number}:")
    print(f"   > \"{prompt_text}\"\n")

    # 1. Parse into canonical InboundMessage
    inbound = adapter.parse_inbound({"From": phone_number, "Body": prompt_text})
    
    # 2. Process via Canonical Captain Application API
    outbound = CAPTAIN_APP.process_inbound(inbound)
    
    # 3. Format as WhatsApp outbound payload
    wa_payload = adapter.format_outbound(outbound)
    
    print("⚓ [Captain Response via WhatsApp Adapter]:")
    print("-" * 60)
    print(wa_payload["text"]["body"])
    print("-" * 60)
    print(f"JSON Payload to WhatsApp API:\n{json.dumps(wa_payload, indent=2)}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test WhatsApp Captain Adapter")
    parser.add_argument("--send", type=str, help="Simulate sending a WhatsApp message to Captain")
    parser.add_argument("--from-phone", type=str, default="+15550001234", help="Sender phone number")
    args = parser.parse_args()

    if args.send:
        run_interactive(args.send, args.from_phone)
    else:
        unittest.main()
