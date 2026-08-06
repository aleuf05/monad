import unittest
import tempfile
from pathlib import Path

from monad_zero.harness.manifest import replay_digest
from monad_zero.harness.nexus import NexusHarness
from monad_zero.harness.perturbation_engine import PerturbationEngine
from monad_zero.harness.shadow_controls import instantiate_shadow_controls, validate_control_invariants
from monad_zero.harness.statistical_evaluator import StatisticalEvaluator
from monad_zero.harness.sweep_controller import SweepDirection, SweepRate, architecture_vector_for_q
from monad_zero.organism import ArchitectureVector, MonadOrganism, PerturbationBusyError, PerturbationType, TELEMETRY_FIELDS


class Phase2Tests(unittest.TestCase):
    def test_canonical_q_schedule_and_typed_vector(self):
        self.assertEqual(architecture_vector_for_q(0.1).R_d, 0)
        self.assertEqual(architecture_vector_for_q(0.4).R_d, 1)
        self.assertEqual(architecture_vector_for_q(0.6).R_d, 2)
        self.assertEqual(architecture_vector_for_q(0.9).R_d, 3)
        self.assertEqual(len(NexusHarness(points=3).sweeper.schedule(SweepDirection.REVERSE, SweepRate.FAST)), 3)

    def test_architecture_provenance_and_single_probe_occupancy(self):
        organism = MonadOrganism(seed=2, run_id="test-run")
        update_id = organism.request_architecture_update(ArchitectureVector(D_a=0.8), source="test", reason="q step")
        self.assertTrue(update_id.startswith("architecture-update-"))
        organism.tick()
        self.assertTrue(any(event["type"] == "architecture_update_effective" for event in organism.drain_events()))
        organism.inject_perturbation(PerturbationType.NO_OP)
        with self.assertRaises(PerturbationBusyError):
            organism.inject_perturbation(PerturbationType.NO_OP)

    def test_typed_telemetry_has_structural_schema_and_reversible_probe(self):
        organism = MonadOrganism(seed=3, run_id="schema-run")
        organism.tick()
        organism.drain_events()
        organism.inject_perturbation(PerturbationType.POLICY_BIAS_INJECTION, duration_ticks=2)
        event = organism.tick()
        self.assertEqual(set(event), set(TELEMETRY_FIELDS))
        self.assertEqual(event["schema_version"], "mc0.telemetry.v1")
        for _ in range(3):
            organism.tick()
        self.assertAlmostEqual(organism.worker.parameters.exploration_rate, 0.2)

    def test_harness_manifest_and_replay_digest(self):
        harness = NexusHarness(points=3, rate=SweepRate.FAST, ticks_per_step=1)
        first = harness.run(seed=5)
        second = harness.run(seed=5)
        self.assertEqual(first.replay_digest, second.replay_digest)
        self.assertEqual(first.manifest["config_hash"], second.manifest["config_hash"])
        self.assertEqual(first.replay_digest, replay_digest(first.events))
        self.assertNotEqual(first.manifest["code_commit"], "unknown")
        with tempfile.TemporaryDirectory() as directory:
            first.write(directory)
            self.assertTrue((Path(directory) / "nexus-integrated-5.events.jsonl").exists())

    def test_controls_and_phase_2a_evaluator(self):
        controls = instantiate_shadow_controls(seed=4)
        self.assertEqual(len(controls), 6)
        run = NexusHarness(points=3, ticks_per_step=1).run(seed=4)
        evaluator = StatisticalEvaluator()
        for field in TELEMETRY_FIELDS:
            self.assertTrue(all(field in row for row in run.events if "nexus_closure_index" in row))
        self.assertEqual(evaluator.fit(run.events, "M0").model_class, "M0")
        self.assertEqual(evaluator.fit(run.events, "M2").model_class, "M2")
        self.assertIsInstance(evaluator.regime_summary(run.events), dict)

    def test_decorative_control_blocks_internal_downward_causation(self):
        organism, contract = instantiate_shadow_controls(seed=4)["decorative-self-model"]
        organism.tick()
        organism.worker.predicted_viability = 1.0
        organism.tick()
        events = organism.drain_events()
        self.assertEqual(validate_control_invariants(events, contract), [])


if __name__ == "__main__":
    unittest.main()
