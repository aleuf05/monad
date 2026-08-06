"""Trust-boundary commissioning tests for the Root Console research rail."""

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).with_name("research.py")
SPEC = importlib.util.spec_from_file_location("root_console_research", MODULE_PATH)
research = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(research)


class ResearchPacketTests(unittest.TestCase):
    def test_canonical_packet_is_archive_backed_and_not_commandable(self):
        packet = research.get_arc("CAP-ARI-003")
        self.assertTrue(packet["canonical"])
        self.assertEqual(packet["dataMode"], "LIVE")
        self.assertEqual(packet["status"], "AUTHORIZED_NOT_STARTED")
        self.assertEqual(packet["currentGeneration"], 0)
        self.assertIn("admiralty/archive/", packet["sourcePath"])
        with self.assertRaisesRegex(research.ResearchError, "no Captain research-execution backend"):
            research.run_command("CAP-ARI-003", "start")

    def test_missing_archive_packet_is_reported_not_invented(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            research, "ARCHIVE_DIR", Path(directory)
        ):
            listing = research.list_packets()
        self.assertEqual(listing["missingCanonicalIds"], research.CANONICAL_IDS)
        self.assertEqual([p["researchArcId"] for p in listing["packets"]], [research.DEMO_ARC_ID])

    def test_demo_identity_cannot_shadow_canonical_identity(self):
        listing = research.list_packets()
        ids = [packet["researchArcId"] for packet in listing["packets"]]
        self.assertEqual(len(ids), len(set(ids)))
        demo = next(packet for packet in listing["packets"] if packet["researchArcId"] == research.DEMO_ARC_ID)
        self.assertFalse(demo["canonical"])
        self.assertEqual(demo["dataMode"], "MOCK")
        self.assertEqual(demo["relatedCanonicalId"], "CAP-ARI-003")


class DemoArcLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.arc = research._DemoArc()

    def test_bounded_arc_reaches_natural_stopping_point(self):
        self.assertEqual(self.arc.snapshot()["status"], "AUTHORIZED_NOT_STARTED")
        self.arc.command("start")
        for _ in range(4):
            self.arc.command("approve_next_experiment")
        snapshot = self.arc.snapshot()
        self.assertEqual(snapshot["status"], "AWAITING_ADMIRAL")
        self.assertEqual(snapshot["currentGeneration"], 2)
        self.assertEqual(snapshot["runsUsed"], 14)
        self.assertEqual(snapshot["captainAssessment"]["confidence"], "MEDIUM")
        export = self.arc.command("export_packet")
        self.assertTrue(export["atNaturalStoppingPoint"])
        self.assertEqual(export["dataMode"], "MOCK")
        with self.assertRaisesRegex(research.ResearchError, "no further experiments"):
            self.arc.command("approve_next_experiment")

    def test_pause_is_a_real_execution_gate(self):
        self.arc.command("start")
        self.arc.command("pause")
        with self.assertRaisesRegex(research.ResearchError, "paused"):
            self.arc.command("approve_next_experiment")
        self.arc.command("resume")
        self.arc.command("approve_next_experiment")
        self.assertEqual(self.arc.snapshot()["currentGeneration"], 1)

    def test_returned_snapshots_and_events_are_defensive_copies(self):
        self.arc.command("start")
        snapshot = self.arc.snapshot()
        snapshot["activeExperiment"]["status"] = "FORGED"
        events = self.arc.events()
        events[0]["summary"] = "FORGED"
        self.assertEqual(self.arc.snapshot()["activeExperiment"]["status"], "RUNNING")
        self.assertNotEqual(self.arc.events()[0]["summary"], "FORGED")

    def test_deterministic_replay_does_not_mutate_or_leak_cached_state(self):
        before = self.arc.snapshot()
        with mock.patch.object(research, "DEMO_ARC", self.arc):
            replay = research.get_replay(research.DEMO_ARC_ID)
            replay[0]["event"]["summary"] = "FORGED"
            second = research.get_replay(research.DEMO_ARC_ID)
        self.assertEqual(self.arc.snapshot(), before)
        self.assertNotEqual(second[0]["event"]["summary"], "FORGED")
        self.assertEqual(second[-1]["arc"]["status"], "AWAITING_ADMIRAL")
        self.assertEqual(second[-1]["arc"]["dataMode"], "MOCK")


if __name__ == "__main__":
    unittest.main()
