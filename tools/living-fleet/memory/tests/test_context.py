import json
import tempfile
import unittest
from pathlib import Path

from memory.seed_import import import_seed_memory
from memory.service import MemoryService

CAPTAINS_PATH = Path(__file__).resolve().parents[2] / "captains.json"


class ContextFactVsMythologyTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "memory.db"
        import_seed_memory(self.db_path, CAPTAINS_PATH)
        self.captains = json.loads(CAPTAINS_PATH.read_text())
        self.service = MemoryService(self.db_path, self.captains)

    def tearDown(self):
        self.service.close()
        self.tmp_dir.cleanup()

    def test_fact_and_mythology_are_never_merged(self):
        bundle = self.service.request_context("captain.alpha", purpose="reflect-on-mission")
        narrative_text = json.dumps(bundle["narrative"])
        facts_and_episodes_text = json.dumps(bundle["facts"]) + json.dumps(bundle["episodes"])

        self.assertIn("mega-anatid", narrative_text)
        self.assertNotIn("mega-anatid", facts_and_episodes_text)

        self.assertIn("rendezvous", narrative_text.lower())
        # The sober fact_summary lives inside narrative too (for on-page
        # side-by-side display) but must be textually distinguishable from
        # the mythology field, never collapsed into one string.
        narrative_entry = next(item for item in bundle["narrative"] if item["title"] == "Operation QUACKEN")
        self.assertNotEqual(narrative_entry["fact_summary"], narrative_entry["mythology"])
        self.assertIn("success", narrative_entry["fact_summary"].lower())

    def test_doctrine_belief_surfaces_as_a_fact_not_a_belief(self):
        bundle = self.service.request_context("captain.alpha", purpose="recall-doctrine")
        fact_subjects = {item["subject"] for item in bundle["facts"]}
        belief_subjects = {item["subject"] for item in bundle["beliefs"]}
        self.assertIn("doctrine.living-fleet", fact_subjects)
        self.assertNotIn("doctrine.living-fleet", belief_subjects)


if __name__ == "__main__":
    unittest.main()
