import json
import tempfile
import unittest
from pathlib import Path

from memory.models import FLEET_SCOPE
from memory.service import MemoryService

CAPTAINS_PATH = Path(__file__).resolve().parents[2] / "captains.json"


class CrossCaptainSharingTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "memory.db"
        self.captains = json.loads(CAPTAINS_PATH.read_text())
        self.service = MemoryService(self.db_path, self.captains)

    def tearDown(self):
        self.service.close()
        self.tmp_dir.cleanup()

    def test_same_fleet_event_gets_independent_per_captain_interpretation(self):
        fleet_result = self.service.record_event(
            "captain.alpha",
            category="fleet-event",
            summary="MONAD held rendezvous with contact QUACKEN; mission success.",
            occurred_at="2026-07-13T19:27:50Z",
            who=["vessel.monad", "contact.rubber-ducky"],
            payload={"outcome": "success"},
            tags=["quacken", "mission-complete"],
            fleet=True,
        )
        fleet_episodic_id = fleet_result["episodic_id"]
        self.assertIsNotNone(fleet_episodic_id)

        fleet_rows = self.service.inspect_memory(FLEET_SCOPE, table="episodic_memories")
        self.assertEqual(len(fleet_rows), 1)
        self.assertEqual(fleet_rows[0]["episodic_id"], fleet_episodic_id)

        interpretations = {
            "captain.alpha": "A satisfying, slightly absurd end to a long patrol.",
            "captain.bravo": "An unremarkable contact resolution, logged and moved on.",
            "captain.charlie": "Relief that the rear guard held while the fleet was distracted by QUACKEN.",
        }
        per_captain_episodic_ids = {}
        for captain_id, interpretation in interpretations.items():
            result = self.service.record_event(
                captain_id,
                category="fleet-event-interpretation",
                summary=f"{captain_id}'s own account of the QUACKEN rendezvous.",
                occurred_at="2026-07-13T19:28:00Z",
                who=[captain_id],
                payload={},
                tags=["quacken"],
                interpretation=interpretation,
                references_episodic_id=fleet_episodic_id,
            )
            per_captain_episodic_ids[captain_id] = result["episodic_id"]

        seen_interpretations = set()
        for captain_id, episodic_id in per_captain_episodic_ids.items():
            self.assertIsNotNone(episodic_id)
            own_rows = self.service.inspect_memory(captain_id, table="episodic_memories")
            own_row = next(row for row in own_rows if row["episodic_id"] == episodic_id)
            self.assertEqual(own_row["captain_id"], captain_id)  # never stored under 'fleet'
            self.assertEqual(own_row["interpretation"], interpretations[captain_id])
            seen_interpretations.add(own_row["interpretation"])
        self.assertEqual(len(seen_interpretations), 3)  # genuinely independent, not copies of one another

    def test_one_captains_belief_revision_never_touches_another_captains_beliefs(self):
        for i in range(3):
            self.service.record_event(
                "captain.alpha",
                category="reliability-concern",
                summary=f"captain.bravo hesitated during a time-critical maneuver (case {i}).",
                occurred_at=f"2026-07-13T0{i}:00:00Z",
                who=["captain.alpha", "captain.bravo"],
                payload={"outcome": "failure"},
                tags=["captain.bravo"],
            )
        self.service.trigger_reflection("captain.alpha", reason="repeated-similar-outcomes")

        alpha_beliefs = self.service.inspect_memory("captain.alpha", table="semantic_beliefs")
        bravo_beliefs = self.service.inspect_memory("captain.bravo", table="semantic_beliefs")

        self.assertTrue(any(row["subject"] == "captain.bravo" for row in alpha_beliefs))
        self.assertFalse(any(row["subject"] == "captain.bravo" for row in bravo_beliefs))


if __name__ == "__main__":
    unittest.main()
