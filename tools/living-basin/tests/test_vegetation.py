import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.grid import World
from engine import config, herbivores, vegetation


class VegetationTest(unittest.TestCase):
    def test_grazing_reduces_biomass(self):
        world = World(seed=4)
        r, c = 30, 30
        candidates = [(r, c)] + world.neighbors(r, c, diagonal=True)
        for cr, cc in candidates:
            world.fields["vegetation_biomass"][cr][cc] = 0.9
        before = {cell: world.fields["vegetation_biomass"][cell[0]][cell[1]] for cell in candidates}

        herd = herbivores.spawn_herbivores(world, random.Random(0), (r, r, c, c))[:1]
        herd[0].position = (r, c)
        herbivores.step(world, herd, random.Random(0))

        hr, hc = herd[0].position
        self.assertLess(world.fields["vegetation_biomass"][hr][hc], before[(hr, hc)])
        self.assertGreater(world.fields["grazing_pressure"][hr][hc], 0.0)

    def test_reduced_biomass_lowers_root_density_over_time(self):
        world = World(seed=5)
        r, c = 15, 15
        world.fields["vegetation_biomass"][r][c] = 0.0
        world.fields["root_density"][r][c] = 0.8
        previous_low = [[False] * world.n for _ in range(world.n)]

        readings = []
        for _ in range(60):
            vegetation.update_root_density(world, previous_low)
            readings.append(world.fields["root_density"][r][c])

        self.assertLess(readings[-1], readings[0])
        self.assertLess(readings[-1], config.LOW_ROOT_THRESHOLD)

    def test_root_density_edge_triggers_only_once(self):
        world = World(seed=6)
        r, c = 16, 16
        world.fields["vegetation_biomass"][r][c] = 0.0
        world.fields["root_density"][r][c] = config.LOW_ROOT_THRESHOLD + 0.01
        previous_low = [[False] * world.n for _ in range(world.n)]

        fired_ticks = 0
        for _ in range(20):
            crossed = vegetation.update_root_density(world, previous_low)
            if (r, c) in crossed:
                fired_ticks += 1
        self.assertEqual(fired_ticks, 1)


if __name__ == "__main__":
    unittest.main()
