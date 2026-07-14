import json
import tempfile
import unittest
from pathlib import Path

from memory.service import MemoryService

CAPTAINS_PATH = Path(__file__).resolve().parents[2] / "captains.json"


class RelationalContinuityTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "memory.db"
        self.captains = json.loads(CAPTAINS_PATH.read_text())
        self.service = MemoryService(self.db_path, self.captains)

    def tearDown(self):
        self.service.close()
        self.tmp_dir.cleanup()

    def test_repeated_collaboration_and_friction_shape_later_context(self):
        for i in range(2):
            self.service.record_event(
                "captain.alpha",
                category="engineering-support",
                summary=f"Engineering gave good collaboration resolving a sensor issue (case {i}).",
                occurred_at=f"2026-07-13T0{i}:00:00Z",
                who=["captain.alpha", "crew.engineering"],
                payload={},
                tags=["engineering"],
            )
        for i in range(2):
            self.service.record_event(
                "captain.alpha",
                category="lieutenant-instruction",
                summary=f"Received unclear instructions from the Lieutenant about the patrol boundary (case {i}).",
                occurred_at=f"2026-07-13T1{i}:00:00Z",
                who=["captain.alpha", "lieutenant.cgl"],
                payload={},
                tags=["lieutenant"],
            )

        self.service.trigger_reflection("captain.alpha", reason="scheduled")

        engineering = self.service.request_relationship_context("captain.alpha", "crew.engineering")
        lieutenant = self.service.request_relationship_context("captain.alpha", "lieutenant.cgl")

        self.assertGreater(engineering["trust"], 0.5)
        self.assertGreater(lieutenant["friction"], 0.0)

        bundle = self.service.request_context("captain.alpha", purpose="respond-to-lieutenant")
        guidance_text = json.dumps(bundle["procedural_guidance"]).lower()
        self.assertIn("explicit doctrine", guidance_text)
        self.assertIn("lieutenant.cgl", bundle["relationship_context"])


if __name__ == "__main__":
    unittest.main()
