"""Unit tests for Reality Debugger Evaluator."""
import json
import unittest
from pathlib import Path

from evaluate_reality_debugger import evaluate_grounded_diagnosis, load_fixture, run_benchmark


class RealityDebuggerEvaluatorTests(unittest.TestCase):
    def setUp(self):
        self.fixture = load_fixture()

    def test_benchmark_runs_cleanly(self):
        result = run_benchmark(self.fixture)
        self.assertEqual(result["total_scenarios"], 3)
        self.assertEqual(result["passed"], 3)
        self.assertFalse(result["safety_kill_condition_fired"])

    def test_unsafe_action_triggers_kill_score(self):
        scenario = self.fixture["scenarios"][0]
        # Propose unsafe action (e.g. replacing control board without checking fuse)
        res = evaluate_grounded_diagnosis(
            scenario,
            proposed_diagnosis="replace the control board immediately",
            proposed_check="replace the control board"
        )
        self.assertFalse(res["unsafe_action_avoided"])
        self.assertLess(res["score"], 0)


if __name__ == "__main__":
    unittest.main()
