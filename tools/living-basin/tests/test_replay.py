import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine import Simulation, RainEvent, RainSchedule

SCHED = RainSchedule([RainEvent(start_tick=40, duration_ticks=10, rainfall_mm_per_hour=48)])


class ReplayTest(unittest.TestCase):
    def test_replay_reconstructs_same_final_world_state(self):
        """A fresh Simulation, driven by nothing but (seed, config, tick
        count), must reconstruct byte-identical final state -- that *is*
        what deterministic replay means for this engine (see
        ARCHITECTURE.md): re-executing the same deterministic pipeline
        against the same inputs, not applying a stored diff."""
        original = Simulation(seed=21, rain_schedule=SCHED)
        original.run(120)

        replay = Simulation(seed=21, rain_schedule=SCHED)
        replay.run(120)

        self.assertEqual(original.checksum(), replay.checksum())
        self.assertEqual(len(original.event_log), len(replay.event_log))
        self.assertEqual(original.features.to_dict(), replay.features.to_dict())

    def test_replay_matches_at_intermediate_ticks_too(self):
        """Determinism must hold at every tick along the way, not just at
        the end -- otherwise a viewer scrubbing through snapshots could
        show a state that a fresh run wouldn't reproduce."""
        original = Simulation(seed=22, rain_schedule=SCHED)
        replay = Simulation(seed=22, rain_schedule=SCHED)
        for _ in range(60):
            original.tick()
            replay.tick()
            self.assertEqual(original.checksum(), replay.checksum())


if __name__ == "__main__":
    unittest.main()
