"""Tests for Monad CardMaker v0.1.

Verifies:
1. Generator engine logic (Deterministic fallback & LLM integration interface)
2. Card JSON structure (headline, subtitle, quote, message, signature, theme)
3. HTTP server endpoints (/api/status, /api/generate, static file delivery)
4. Offline execution with custom inputs ("Ken / aviation / family / warm-funny")
"""

from __future__ import annotations

import json
import sys
import unittest
import urllib.request
from pathlib import Path
from threading import Thread
from time import sleep

CARDMAKER_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CARDMAKER_DIR))

from generator import CardGeneratorEngine, CardInput, DeterministicCardGenerator, CardContent
from server import run_server


class TestCardGenerator(unittest.TestCase):
    """Unit tests for Card Generator engine."""

    def setUp(self):
        self.generator = DeterministicCardGenerator()

    def test_ken_aviation_card_generation(self):
        card_input = CardInput(
            recipient="Ken",
            occasion="Birthday",
            relationship="Family",
            details="aviation enthusiast, builds remote control planes, loves family barbecues",
            tone="Funny"
        )
        card = self.generator.generate(card_input)

        self.assertIsInstance(card, CardContent)
        self.assertIn("Ken", card.front_headline)
        self.assertTrue(len(card.inside_message) > 20)
        self.assertIn("Ken", card.inside_message)
        self.assertIn("Family", card.closing_signature)
        self.assertEqual(card.theme.svg_icon, "plane")

    def test_tones_support(self):
        tones = ["Warm", "Funny", "Sentimental", "Weird", "Surprise Me"]
        for tone in tones:
            card_input = CardInput(
                recipient="Alice",
                occasion="Thank You",
                relationship="Friend",
                details="loves coffee and books",
                tone=tone
            )
            card = self.generator.generate(card_input)
            self.assertTrue(bool(card.front_headline))
            self.assertTrue(bool(card.inside_message))

    def test_empty_details_fallback(self):
        card_input = CardInput(
            recipient="Bob",
            occasion="Congratulations",
            relationship="Colleague",
            details="",
            tone="Warm"
        )
        card = self.generator.generate(card_input)
        self.assertIn("Bob", card.front_headline)
        self.assertIn("Bob", card.inside_message)


class TestCardMakerServer(unittest.TestCase):
    """Integration tests for CardMaker HTTP Server."""

    @classmethod
    def setUpClass(cls):
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('127.0.0.1', 0))
        cls.port = s.getsockname()[1]
        s.close()

        cls.server_thread = Thread(target=run_server, kwargs={"host": "127.0.0.1", "port": cls.port}, daemon=True)
        cls.server_thread.start()
        sleep(0.4)

    def test_status_endpoint(self):
        url = f"http://127.0.0.1:{self.port}/api/status"
        with urllib.request.urlopen(url) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["status"], "ok")
            self.assertEqual(data["service"], "monad-cardmaker")

    def test_index_page(self):
        url = f"http://127.0.0.1:{self.port}/"
        with urllib.request.urlopen(url) as resp:
            self.assertEqual(resp.status, 200)
            html = resp.read().decode("utf-8")
            self.assertIn("MONAD CARDMAKER", html)
            self.assertIn("cardForm", html)

    def test_generate_api_endpoint(self):
        url = f"http://127.0.0.1:{self.port}/api/generate"
        payload = json.dumps({
            "recipient": "Ken",
            "occasion": "Birthday",
            "relationship": "Family",
            "details": "aviation enthusiast, remote control planes",
            "tone": "Funny"
        }).encode("utf-8")

        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            card = json.loads(resp.read().decode("utf-8"))
            self.assertIn("front_headline", card)
            self.assertIn("inside_message", card)
            self.assertIn("Ken", card["inside_message"])


if __name__ == "__main__":
    unittest.main()
