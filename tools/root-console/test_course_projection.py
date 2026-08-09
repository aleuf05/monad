import json
import tempfile
import unittest
from pathlib import Path

import course_projection


class CourseProjectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "web/data").mkdir(parents=True)

    def tearDown(self):
        self.temp.cleanup()

    def write(self, name, value):
        (self.root / "web/data" / name).write_text(json.dumps(value))

    def test_clear_watch_keeps_human_gate_distinct_from_captain_action(self):
        self.write("fleetnet.json", {"operations": {"status": "clear", "alerts": []}, "tree": {"head": "abc"}})
        self.write("watch-officer-status.json", {"world_intake": {"pending_count": 4, "oldest_pending_age_hours": 8}})
        result = course_projection.build(self.root, [], [], {"outcome": "pending"})
        self.assertIn("4 pending", result["captain_action"])
        self.assertIn("Admiral acceptance", result["human_gate"])
        self.assertEqual(result["schema"], "monad.captainCourse.v1")

    def test_alert_preempts_backlog_and_preserves_continuity(self):
        alert = {"action": "Repair voice service.", "severity": "critical"}
        self.write("fleetnet.json", {"operations": {"status": "action-required", "alerts": [alert]}})
        self.write("watch-officer-status.json", {"world_intake": {"pending_count": 9}})
        result = course_projection.build(self.root, [{"taskId": "T1"}], [{"title": "L1"}], {"outcome": "fault", "note": "no audio"})
        self.assertEqual(result["captain_action"], "Repair voice service.")
        self.assertEqual(result["continuity"]["latest_handoff"]["taskId"], "T1")
        self.assertIn("no audio", result["human_gate"])

    def test_missing_sources_degrade_to_unknown_without_inventing_state(self):
        result = course_projection.build(self.root, [], [], {"outcome": "pending"})
        self.assertEqual(result["watch"]["status"], "unknown")
        self.assertIsNone(result["backlog"]["world_intake_pending"])


if __name__ == "__main__":
    unittest.main()
