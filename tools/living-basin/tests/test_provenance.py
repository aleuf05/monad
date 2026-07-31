import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine import Simulation, RainEvent, RainSchedule
from engine.overrides import apply_override
from engine.lineage import diagnostic_card

SCHED = RainSchedule([RainEvent(start_tick=40, duration_ticks=10, rainfall_mm_per_hour=48)])


def _run(ticks=120, seed=7):
    sim = Simulation(seed=seed, rain_schedule=SCHED)
    sim.run(ticks)
    return sim


class ProvenanceTest(unittest.TestCase):
    def test_every_feature_has_a_genesis_event(self):
        sim = _run()
        self.assertGreater(len(sim.features.all()), 0)
        for feat in sim.features.all():
            genesis_id = feat.causal_event_ids[0]
            self.assertIsNotNone(sim.event_log.get(genesis_id))

    def test_all_displayed_causes_reference_existing_events(self):
        sim = _run()
        for evt in sim.event_log.all():
            for parent_id in evt.caused_by:
                self.assertIsNotNone(sim.event_log.get(parent_id), f"dangling cause {parent_id}")

    def test_lineage_is_acyclic(self):
        sim = _run()
        self.assertTrue(sim.event_log.is_acyclic())

    def test_authored_overrides_propagate_to_feature_status(self):
        sim = _run()
        self.assertGreater(len(sim.features.all()), 0)
        feat = sim.features.all()[0]
        cell = tuple(feat.cells[0])
        self.assertFalse(feat.authored_override)

        apply_override(
            sim.world, sim.event_log, sim.features,
            tick=sim.tick_count, cell=cell, field_name="soil_cohesion",
            new_value=0.9, actor="test-suite", reason="unit test",
        )
        self.assertTrue(feat.authored_override)
        card = diagnostic_card(sim.event_log, feat)
        self.assertNotEqual(card["authored_overrides"], "None")

    def test_no_override_reads_as_none(self):
        sim = _run()
        untouched = [f for f in sim.features.all() if not f.authored_override][0]
        card = diagnostic_card(sim.event_log, untouched)
        self.assertEqual(card["authored_overrides"], "None")

    def test_diagnostic_text_matches_recorded_values(self):
        sim = _run()
        feat = sim.features.all()[0]
        genesis_id = feat.causal_event_ids[0]
        genesis_evt = sim.event_log.get(genesis_id)
        card = diagnostic_card(sim.event_log, feat)
        # The card's genesis_inputs must be exactly the stored event's
        # inputs -- not a recomputation from current world state.
        self.assertEqual(card["genesis_inputs"], genesis_evt.inputs)
        self.assertEqual(card["genesis_tick"], feat.genesis_tick)


if __name__ == "__main__":
    unittest.main()
