"""Conformance tests for Nexus Capture protocol and specimens."""
import importlib.util
import json
import sys
import unittest
from pathlib import Path

P = Path(__file__).with_name("nexus_capture.py")
S = importlib.util.spec_from_file_location("nexus_capture", P)
cap = importlib.util.module_from_spec(S)
sys.modules[S.name] = cap
S.loader.exec_module(cap)


class TestNexusCapture(unittest.TestCase):
    def test_specimen_conformance(self):
        item = cap.parse_capture_markdown(cap.DELEGATE_SLEEP_SPECIMEN)
        self.assertIn("delegate sleep", item.raw)
        self.assertIn("Conscious executive", item.consequences)
        self.assertIn("Operational topology", item.map_change)
        self.assertIn("Naming the maneuver", item.capture_effect)
        self.assertIn("Measurable", item.reality_edge)
        self.assertTrue(item.digest.startswith("sha256:"))

    def test_missing_section_rejected(self):
        bad_text = """
## RAW
Raw idea here

## CONSEQUENCES
Consequences here

## MAP CHANGE
Topology changed
"""
        with self.assertRaises(cap.NexusCaptureError) as ctx:
            cap.parse_capture_markdown(bad_text)
        self.assertIn("Missing required capture sections", str(ctx.exception))

    def test_empty_section_rejected(self):
        bad_text = """
## RAW
Raw idea

## CONSEQUENCES

## MAP CHANGE
Topology changed

## CAPTURE EFFECT
Effect

## REALITY EDGE
Edge
"""
        with self.assertRaises(cap.NexusCaptureError):
            cap.parse_capture_markdown(bad_text)

    def test_digest_stability_and_tamper_detection(self):
        item = cap.parse_capture_markdown(cap.DELEGATE_SLEEP_SPECIMEN)
        md = item.to_markdown()
        parsed_again = cap.parse_capture_markdown(md)
        self.assertEqual(item.digest, parsed_again.digest)

        # Tamper with markdown
        tampered_md = md.replace("delegate sleep", "tampered text")
        with self.assertRaises(cap.NexusCaptureError) as ctx:
            cap.parse_capture_markdown(tampered_md)
        self.assertIn("Digest mismatch", str(ctx.exception))

    def test_conversion_to_nexus_envelope(self):
        item = cap.parse_capture_markdown(cap.DELEGATE_SLEEP_SPECIMEN)
        env = item.to_nexus_envelope()
        self.assertEqual(env["identity"]["id"], "captain.live")
        self.assertEqual(env["authority"]["grant"], "admiral")
        self.assertEqual(env["capability"]["name"], "nexus-capture")
        self.assertEqual(env["action"]["verb"], "capture")
        self.assertEqual(env["result"]["status"], "integrated")
        self.assertTrue(env["evidence"]["digest"].startswith("sha256:"))


if __name__ == "__main__":
    unittest.main()
