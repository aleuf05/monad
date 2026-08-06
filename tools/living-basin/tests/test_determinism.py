import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine import Simulation, RainEvent, RainSchedule

SHORT_TICKS = 80
SCHED = RainSchedule([RainEvent(start_tick=40, duration_ticks=10, rainfall_mm_per_hour=48)])


class DeterminismTest(unittest.TestCase):
    def test_same_seed_same_config_same_final_state(self):
        a = Simulation(seed=7, rain_schedule=SCHED)
        a.run(SHORT_TICKS)
        b = Simulation(seed=7, rain_schedule=SCHED)
        b.run(SHORT_TICKS)
        self.assertEqual(a.checksum(), b.checksum())

    def test_same_seed_same_config_same_event_lineage(self):
        a = Simulation(seed=7, rain_schedule=SCHED)
        a.run(SHORT_TICKS)
        b = Simulation(seed=7, rain_schedule=SCHED)
        b.run(SHORT_TICKS)
        a_events = [e.to_dict() for e in a.event_log.all()]
        b_events = [e.to_dict() for e in b.event_log.all()]
        self.assertEqual(a_events, b_events)

    def test_different_seed_diverges(self):
        a = Simulation(seed=7, rain_schedule=SCHED)
        a.run(SHORT_TICKS)
        b = Simulation(seed=8, rain_schedule=SCHED)
        b.run(SHORT_TICKS)
        self.assertNotEqual(a.checksum(), b.checksum())

    def test_rain_schedule_instance_is_safely_reusable(self):
        """A RainSchedule handed to two Simulations (or the same seed run
        twice) must not carry state between them."""
        shared = SCHED
        a = Simulation(seed=11, rain_schedule=shared)
        a.run(SHORT_TICKS)
        b = Simulation(seed=11, rain_schedule=shared)
        b.run(SHORT_TICKS)
        self.assertEqual(a.checksum(), b.checksum())
        self.assertEqual(len(a.event_log), len(b.event_log))


if __name__ == "__main__":
    unittest.main()
