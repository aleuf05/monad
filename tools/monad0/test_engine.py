import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from monad0.engine import EnvironmentConfig, Monad0Experiment, Sandbox, run_comparison


class Monad0EngineTests(unittest.TestCase):
    def test_environment_is_deterministic_and_perturbable(self):
        first = Sandbox(EnvironmentConfig(seed=7, perturbations={2: {"energy": -0.4}}))
        second = Sandbox(EnvironmentConfig(seed=7, perturbations={2: {"energy": -0.4}}))
        a = [first.step("harvest_energy") for _ in range(5)]
        b = [second.step("harvest_energy") for _ in range(5)]
        self.assertEqual(a, b)
        self.assertEqual(a[2]["perturbation"]["energy"], -0.4)

    def test_seed_changes_stochastic_trial_but_replay_is_stable(self):
        first = run_comparison(seed=1, ticks=10)
        replay = run_comparison(seed=1, ticks=10)
        alternate = run_comparison(seed=2, ticks=10)
        self.assertEqual(first["run_hash"], replay["run_hash"])
        self.assertNotEqual(first["run_hash"], alternate["run_hash"])

    def test_comparative_matrix_has_four_systems_and_json_events(self):
        result = run_comparison(seed=11, ticks=12)
        self.assertEqual(set(result["systems"]), {"monad-0", "flat-adaptive", "decorative-self-model", "open-loop"})
        for run in result["systems"].values():
            self.assertEqual(len([event for event in run["events"] if event["type"] == "telemetry"]), 12)
            telemetry = next(event for event in run["events"] if event["type"] == "telemetry")["telemetry"]
            self.assertIn("multi_dimensional_self_opacity", telemetry["metrics"])
            self.assertIn("time_to_recovery", telemetry["metrics"])
            json.dumps(run["events"])

    def test_monad0_issues_bounded_contract_and_revises_model(self):
        result = Monad0Experiment(seed=3, ticks=40, perturbations={2: {"energy": -0.6}}).run()
        events = result["systems"]["monad-0"]["events"]
        issued = [event for event in events if event["type"] == "contract_issued"]
        resolved = [event for event in events if event["type"] == "contract_resolved"]
        self.assertTrue(issued)
        self.assertTrue(resolved)
        contract = issued[0]["contract"]
        self.assertGreater(contract["duration_ticks"], 0)
        self.assertEqual(contract["resolve_tick"], contract["issued_tick"] + contract["duration_ticks"])
        summary = result["systems"]["monad-0"]["summary"]
        self.assertGreater(summary["contracts_confirmed"] + summary["contracts_refuted"], 0)
        refuted = next(event for event in resolved if not event["confirmed"])
        self.assertEqual(refuted["contract"]["actual_outcome"].keys(), {"maintenance_delta"})
        self.assertEqual(refuted["parameter_after"], refuted["contract"]["baseline_value"])

    def test_recovery_definition_is_explicit(self):
        result = run_comparison(seed=4, ticks=8, perturbations={2: {"energy": -0.6}})
        telemetry = next(event for event in result["systems"]["monad-0"]["events"] if event["type"] == "telemetry" and event["tick"] == 2)["telemetry"]
        self.assertEqual(telemetry["metrics"]["recovery_target"], 0.5)

    def test_control_variants_preserve_declared_boundaries(self):
        result = run_comparison(seed=1, ticks=8)
        self.assertGreater(result["systems"]["monad-0"]["summary"]["topology_nodes"], 0)
        self.assertGreater(result["systems"]["monad-0"]["summary"]["topology_mutability"], 0)
        self.assertGreater(result["systems"]["decorative-self-model"]["summary"]["topology_nodes"], 0)
        self.assertEqual(result["systems"]["flat-adaptive"]["summary"]["topology_nodes"], 0)
        self.assertEqual(result["systems"]["open-loop"]["summary"]["contracts_confirmed"], 0)


if __name__ == "__main__":
    unittest.main()
