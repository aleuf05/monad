import json
import tempfile
import unittest
from pathlib import Path

from memory.service import MemoryService

CAPTAINS_PATH = Path(__file__).resolve().parents[2] / "captains.json"


class ServiceRestartContinuityTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "memory.db"
        self.captains = json.loads(CAPTAINS_PATH.read_text())

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_memories_beliefs_relationships_and_identity_survive_a_restart(self):
        service = MemoryService(self.db_path, self.captains)
        service.record_decision(
            "captain.alpha",
            {
                "decision_id": "agent-decision-restart-1",
                "captain_id": "captain.alpha",
                "vessel_id": "vessel.scout-alpha",
                "posture": "advance-screen",
                "target_contact_id": None,
                "objective": "Maintain forward screen.",
                "assessment": "Formation stable.",
                "observed_tick": 10,
                "observed_event_sequence": 9,
                "submitted_tick": 10,
                "sim_time": "2026-07-13T00:00:00Z",
                "reconsider_at_tick": 70,
                "outcome": "accepted",
                "result": "intent accepted for deterministic patrol execution",
            },
        )
        service.trigger_reflection("captain.alpha", reason="scheduled")
        before_context = service.request_context("captain.alpha", purpose="choose-procedure")
        before_traits = service.request_context("captain.alpha", purpose="recall-doctrine")["identity_summary"]
        before_rows = len(service.inspect_memory("captain.alpha"))
        service.close()

        # A brand new instance against the same db path, simulating a
        # process restart -- nothing above should require this instance.
        restarted = MemoryService(self.db_path, self.captains)
        try:
            after_context = restarted.request_context("captain.alpha", purpose="choose-procedure")
            after_traits = restarted.request_context("captain.alpha", purpose="recall-doctrine")["identity_summary"]
            after_rows = len(restarted.inspect_memory("captain.alpha"))
        finally:
            restarted.close()

        self.assertEqual(before_rows, after_rows)
        self.assertEqual(before_traits, after_traits)
        self.assertEqual(len(before_context["episodes"]), len(after_context["episodes"]))


if __name__ == "__main__":
    unittest.main()
