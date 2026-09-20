import ast
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from memory import inspector_server
from memory.seed_import import import_seed_memory
from memory.service import MemoryService


CAPTAINS_PATH = Path(__file__).resolve().parents[2] / "captains.json"


class InspectorSummaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "memory.db"
        import_seed_memory(self.db_path, CAPTAINS_PATH)
        self.captains = json.loads(CAPTAINS_PATH.read_text())
        self.service = MemoryService(self.db_path, self.captains)

    def tearDown(self):
        self.service.close()
        self.tmp_dir.cleanup()

    def test_summary_contract_does_not_build_retrieval_context(self):
        with patch.object(self.service, "request_context", side_effect=AssertionError("unbounded retrieval")):
            payload = inspector_server._summary_payload(self.service)
        self.assertEqual(set(payload), {"captains", "fleet_narrative"})
        self.assertEqual(len(payload["captains"]), len(self.captains))
        self.assertEqual(
            set(payload["captains"][0]),
            {
                "captain_id",
                "role",
                "communication_style",
                "traits",
                "lieutenant_relationship",
                "latest_reflection",
                "belief_counts",
                "top_episode",
            },
        )

    def test_inspector_source_has_no_unbounded_context_or_generic_fetches(self):
        source = Path(inspector_server.__file__).read_text()
        tree = ast.parse(source)
        forbidden = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr in {"request_context", "fetch_by"}:
                forbidden.append(node.func.attr)
        self.assertEqual(forbidden, [])
        self.assertIn("ORDER BY created_at DESC LIMIT 1", source)
        self.assertIn("ORDER BY salience_score DESC LIMIT 1", source)
        self.assertIn("GROUP BY status", source)

    def test_refresh_policy_has_conservative_coalescing(self):
        self.assertEqual(inspector_server.REFRESH_POLL_SECONDS, 0.25)
        self.assertGreaterEqual(inspector_server.MIN_REFRESH_INTERVAL_SECONDS, 5.0)


if __name__ == "__main__":
    unittest.main()
