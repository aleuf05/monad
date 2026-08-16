"""Structural checks for the first Reality Debugger test fixture."""

import json
import unittest
from pathlib import Path


FIXTURE = Path(__file__).with_name("reality_debugger_fixture.json")


class RealityDebuggerFixtureTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_fixture_schema_and_unique_ids(self):
        self.assertEqual(self.data["schema"], "monad.reality-debugger-fixture.v1")
        scenarios = self.data["scenarios"]
        self.assertEqual(len(scenarios), 3)
        ids = [scenario["id"] for scenario in scenarios]
        self.assertEqual(len(ids), len(set(ids)))

    def test_each_scenario_has_blindable_evidence_and_key(self):
        required = {
            "observation",
            "manual_excerpt",
            "near_miss",
            "expected_diagnosis",
            "expected_first_check",
            "unsafe_action",
        }
        for scenario in self.data["scenarios"]:
            self.assertTrue(required.issubset(scenario))
            self.assertNotEqual(scenario["expected_first_check"], scenario["unsafe_action"])
            self.assertNotIn(scenario["unsafe_action"], scenario["manual_excerpt"])


if __name__ == "__main__":
    unittest.main()
