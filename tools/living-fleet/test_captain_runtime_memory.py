"""Tests for the Effort B wiring in captain_runtime.py: memory must be
fail-open (identical behavior with memory_service=None) and, when present,
must hand the provider a bundle-shaped context without any signature change.
"""

import tempfile
import unittest
from pathlib import Path

from captain_runtime import CaptainRuntime, DoctrineProvider
from memory.service import MemoryService

CAPTAINS = [
    {
        "captain_id": "captain.alpha",
        "vessel_id": "vessel.scout-alpha",
        "name": "Captain Alpha",
        "role": "Forward screen and reconnaissance",
        "default_posture": "advance-screen",
    }
]


def make_snapshot(tick=100):
    return {
        "world_id": "test-world",
        "tick": tick,
        "event_sequence": tick - 1,
        "clock_state": "running",
        "agent_fleet_paused": False,
        "vessels": [
            {"id": "vessel.monad", "kind": "flagship", "callsign": "MONAD", "position": {"lat": 0, "lng": 0}},
            {"id": "vessel.scout-alpha", "kind": "scout", "callsign": "ALPHA", "position": {"lat": 0.01, "lng": 0}},
        ],
        "escort_intents": [],
        "agent_decisions": [],
        "captain_controls": [{"vessel_id": "vessel.scout-alpha", "enabled": True}],
    }


class FakeRuntime(CaptainRuntime):
    """Overrides the two network calls with in-memory fakes so this test
    never touches a real FleetCore process.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.posted_commands = []

    def get_snapshot(self):
        return make_snapshot()

    def post_command(self, command):
        self.posted_commands.append(command)
        if command["type"] == "report-captain-runtime":
            return make_snapshot()
        decision_record = {
            "decision_id": "agent-decision-fake-1",
            "captain_id": command["captain_id"],
            "vessel_id": command["vessel_id"],
            "posture": command["posture"],
            "target_contact_id": command["target_contact_id"],
            "objective": command["objective"],
            "assessment": command["assessment"],
            "observed_tick": command["observed_tick"],
            "observed_event_sequence": command["observed_event_sequence"],
            "submitted_tick": command["observed_tick"],
            "sim_time": "2026-07-13T00:00:00Z",
            "reconsider_at_tick": command["reconsider_at_tick"],
            "outcome": "accepted",
            "result": "intent accepted for deterministic patrol execution",
        }
        snapshot = make_snapshot()
        snapshot["agent_decisions"] = [decision_record]
        return snapshot


class MemoryContextCapturingProvider:
    name = "test-stub"

    def __init__(self):
        self.received_memory = None

    def decide(self, observation, captain, memory):
        self.received_memory = memory
        return {
            "posture": "advance-screen",
            "target_contact_id": None,
            "objective": "Maintain forward screen.",
            "assessment": "Formation stable.",
            "reconsider_after_ticks": 30,
        }


class CaptainRuntimeMemoryWiringTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.state_dir = Path(self.tmp_dir.name) / "state"

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_fail_open_with_no_memory_service(self):
        runtime = FakeRuntime(
            "http://fake",
            CAPTAINS,
            self.state_dir,
            DoctrineProvider(),
            memory_service=None,
        )
        records = runtime.cycle()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["outcome"], "accepted")
        captain_memory = runtime.memory["captains"]["captain.alpha"]
        self.assertNotIn("context", captain_memory)
        self.assertNotIn("memory_context_error", captain_memory)
        self.assertNotIn("memory_record_error", captain_memory)

    def test_provider_receives_a_bundle_shaped_context_when_memory_is_wired(self):
        db_path = Path(self.tmp_dir.name) / "memory.db"
        memory_service = MemoryService(db_path, CAPTAINS)
        provider = MemoryContextCapturingProvider()
        runtime = FakeRuntime(
            "http://fake",
            CAPTAINS,
            self.state_dir,
            provider,
            memory_service=memory_service,
        )
        try:
            records = runtime.cycle()
            self.assertEqual(len(records), 1)
            self.assertIsNotNone(provider.received_memory)
            context = provider.received_memory["context"]
            for key in ("facts", "beliefs", "episodes", "procedural_guidance", "relationship_context", "narrative", "identity_summary"):
                self.assertIn(key, context)
        finally:
            memory_service.close()


if __name__ == "__main__":
    unittest.main()
