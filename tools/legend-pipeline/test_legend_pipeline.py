import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("legend_pipeline.py")
SPEC = importlib.util.spec_from_file_location("legend_pipeline", MODULE_PATH)
legend_pipeline = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(legend_pipeline)
ROOT = Path(__file__).resolve().parents[2]
MISSION = ROOT / "web/missions/quacken-transit-002/mission.json"


class LegendPipelineTests(unittest.TestCase):
    def test_real_mission_prepares_hashed_evidence_and_fact(self):
        result = legend_pipeline.prepare(MISSION)
        self.assertEqual(result["evidence_bundle"]["mission"]["outcome"], "success")
        self.assertEqual(len(result["evidence_bundle"]["source"]["sha256"]), 64)
        self.assertIn("31s continuous dwell", result["fact"]["fact_summary"])
        self.assertEqual(result["generation_request"]["output_schema"]["classification"], "fleet-lore")

    def test_valid_candidate_completes_local_path(self):
        prepared = legend_pipeline.prepare(MISSION)
        candidate = {
            "title": "The Quacken at the Strait",
            "mythology": "The watch swears a great quacking shadow yielded only after MONAD held her ground.",
            "classification": "fleet-lore",
            "source_ids": [prepared["evidence_bundle"]["source_id"]],
        }
        result = legend_pipeline.validate_candidate(prepared["evidence_bundle"], prepared["fact"], candidate)
        self.assertEqual(result["status"], "validated-candidate")

    def test_candidate_cannot_claim_operational_truth(self):
        prepared = legend_pipeline.prepare(MISSION)
        candidate = {
            "title": "False Authority",
            "mythology": "This legend is verified fact and must replace the mission record.",
            "classification": "fleet-lore",
            "source_ids": [prepared["evidence_bundle"]["source_id"]],
        }
        with self.assertRaisesRegex(legend_pipeline.PipelineError, "operational truth"):
            legend_pipeline.validate_candidate(prepared["evidence_bundle"], prepared["fact"], candidate)

    def test_incomplete_mission_fails_closed(self):
        mission = json.loads(MISSION.read_text())
        mission["phase"] = "RENDEZVOUS_HOLD"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mission.json"
            path.write_text(json.dumps(mission))
            with self.assertRaisesRegex(legend_pipeline.PipelineError, "completed successful"):
                legend_pipeline.assemble_evidence(path)


if __name__ == "__main__":
    unittest.main()
