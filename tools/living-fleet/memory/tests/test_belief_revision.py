import json
import tempfile
import unittest
from pathlib import Path

from memory.service import MemoryService

CAPTAINS_PATH = Path(__file__).resolve().parents[2] / "captains.json"


class BeliefRevisionTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "memory.db"
        self.captains = json.loads(CAPTAINS_PATH.read_text())
        self.service = MemoryService(self.db_path, self.captains)

    def tearDown(self):
        self.service.close()
        self.tmp_dir.cleanup()

    def _active_belief_about_alpha(self):
        beliefs = self.service.inspect_memory("captain.bravo", table="semantic_beliefs")
        return [row for row in beliefs if row["subject"] == "captain.alpha" and row["status"] == "active"]

    def test_repeated_negative_evidence_then_correction_revises_not_brands(self):
        # Several examples suggesting Alpha is reckless.
        for i in range(3):
            self.service.record_event(
                "captain.bravo",
                category="reliability-concern",
                summary=f"captain.alpha pressed forward into a marked danger zone (incident {i}).",
                occurred_at=f"2026-07-13T0{i}:00:00Z",
                who=["captain.bravo", "captain.alpha"],
                payload={"outcome": "failure"},
                tags=["captain.alpha"],
            )
        self.service.trigger_reflection("captain.bravo", reason="repeated-similar-outcomes")

        formed = self._active_belief_about_alpha()
        self.assertEqual(len(formed), 1)
        self.assertIn("unreliable", formed[0]["statement"].lower())
        original_belief_id = formed[0]["belief_id"]

        # Evidence showing the apparent behavior resulted from faulty contact data.
        self.service.record_event(
            "captain.bravo",
            category="reliability-correction",
            summary="Review of captain.alpha's incidents found faulty contact data was the real cause, not recklessness.",
            occurred_at="2026-07-13T04:00:00Z",
            who=["captain.bravo", "captain.alpha"],
            payload={},
            tags=["captain.alpha"],
        )
        self.service.trigger_reflection("captain.bravo", reason="conflicting-memories")

        original = self.service.inspect_memory("captain.bravo", table="semantic_beliefs")
        original_row = next(row for row in original if row["belief_id"] == original_belief_id)

        # Not permanently branded: the original belief is superseded, not
        # deleted, and still queryable -- and something now supersedes it.
        self.assertEqual(original_row["status"], "superseded")
        self.assertIsNotNone(original_row["superseded_by_belief_id"])

        still_active = self._active_belief_about_alpha()
        self.assertEqual(len(still_active), 1)
        self.assertNotEqual(still_active[0]["belief_id"], original_belief_id)


if __name__ == "__main__":
    unittest.main()
