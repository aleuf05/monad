import json
import tempfile
import unittest
from pathlib import Path

from memory.service import MemoryService

CAPTAINS_PATH = Path(__file__).resolve().parents[2] / "captains.json"


class ExperienceInfluencesJudgmentTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "memory.db"
        self.captains = json.loads(CAPTAINS_PATH.read_text())
        self.service = MemoryService(self.db_path, self.captains)

    def tearDown(self):
        self.service.close()
        self.tmp_dir.cleanup()

    def test_a_remembered_failure_traceably_changes_later_guidance(self):
        baseline = self.service.request_context("captain.alpha", purpose="choose-procedure")
        self.assertEqual(baseline["procedural_guidance"], [])

        result = self.service.record_event(
            "captain.alpha",
            category="investigate-contact",
            summary="Closed on an unidentified contact too fast and nearly lost separation.",
            occurred_at="2026-07-13T00:00:00Z",
            who=["captain.alpha", "lieutenant.cgl"],
            payload={"outcome": "failure", "nearest_distance_m": 250},
            tags=["investigate-contact"],
        )
        self.assertIsNotNone(result["episodic_id"])

        self.service.trigger_reflection("captain.alpha", reason="major-failure")

        after = self.service.request_context("captain.alpha", purpose="choose-procedure")
        self.assertTrue(after["procedural_guidance"])
        guidance_entry = after["procedural_guidance"][0]
        evidence = guidance_entry["evidence_json"]
        self.assertEqual(evidence[0]["episodic_id"], result["episodic_id"])


if __name__ == "__main__":
    unittest.main()
