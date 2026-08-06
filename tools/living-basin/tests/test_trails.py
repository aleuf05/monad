import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.grid import World
from engine import config, trails


class TrailsTest(unittest.TestCase):
    def test_repeated_passage_increases_trail_intensity(self):
        world = World(seed=8)
        cell = (12, 12)
        readings = []
        for _ in range(6):
            trails.accumulate(world, [cell])
            readings.append(world.fields["trail_intensity"][cell[0]][cell[1]])
        for a, b in zip(readings, readings[1:]):
            self.assertGreater(b, a)

    def test_single_passage_does_not_immediately_create_mature_trail(self):
        world = World(seed=9)
        cell = (13, 13)
        trails.accumulate(world, [cell])
        self.assertLess(world.fields["trail_intensity"][cell[0]][cell[1]], config.TRAIL_MATURE_THRESHOLD)

    def test_repeated_passage_can_reach_maturity(self):
        world = World(seed=10)
        cell = (14, 14)
        for _ in range(20):
            trails.accumulate(world, [cell])
        self.assertGreaterEqual(world.fields["trail_intensity"][cell[0]][cell[1]], config.TRAIL_MATURE_THRESHOLD)

    def test_unused_trail_decays(self):
        world = World(seed=11)
        cell = (15, 15)
        world.fields["trail_intensity"][cell[0]][cell[1]] = 0.5
        trails.accumulate(world, [])  # nobody passes through
        self.assertLess(world.fields["trail_intensity"][cell[0]][cell[1]], 0.5)


if __name__ == "__main__":
    unittest.main()
