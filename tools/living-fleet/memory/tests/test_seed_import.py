import json
import tempfile
import unittest
from pathlib import Path

from memory.seed_import import DEFAULT_CAPTAINS, QUACKEN_MISSION, import_seed_memory
from memory.service import MemoryService


class SeedImportTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "memory.db"
        self.captains = json.loads(DEFAULT_CAPTAINS.read_text())

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_every_imported_row_is_tagged_imported_history(self):
        import_seed_memory(self.db_path, DEFAULT_CAPTAINS)
        service = MemoryService(self.db_path, self.captains)
        try:
            rows = service.inspect_memory("captain.alpha")
        finally:
            service.close()
        seeded = [row for row in rows if row["_table"] in ("semantic_beliefs", "procedural_lessons", "narrative_memories", "episodic_memories")]
        self.assertTrue(seeded)
        for row in seeded:
            if row["_table"] == "semantic_beliefs":
                self.assertEqual(row["provenance"], "imported-history")
            if row["_table"] in ("narrative_memories", "episodic_memories"):
                self.assertEqual(row["is_imported_history"], 1)

    def test_rerunning_does_not_duplicate(self):
        first_counts = import_seed_memory(self.db_path, DEFAULT_CAPTAINS)
        self.assertTrue(any(count > 0 for count in first_counts.values()))
        second_counts = import_seed_memory(self.db_path, DEFAULT_CAPTAINS)
        self.assertTrue(all(count == 0 for count in second_counts.values()))

    def test_imported_quacken_numbers_match_the_real_mission_record(self):
        self.assertTrue(QUACKEN_MISSION.exists(), "expected the real quacken-transit-002 mission record to exist")
        mission_data = json.loads(QUACKEN_MISSION.read_text())

        import_seed_memory(self.db_path, DEFAULT_CAPTAINS)
        service = MemoryService(self.db_path, self.captains)
        try:
            bundle = service.request_context("captain.alpha", purpose="reflect-on-mission")
        finally:
            service.close()

        narrative_entry = next(item for item in bundle["narrative"] if item["title"] == "Operation QUACKEN")
        self.assertIn(mission_data["outcome"], narrative_entry["fact_summary"])
        self.assertIn(mission_data["mission_id"], narrative_entry["fact_summary"])


if __name__ == "__main__":
    unittest.main()
