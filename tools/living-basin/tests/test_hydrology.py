import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.grid import World
from engine import hydrology


class HydrologyTest(unittest.TestCase):
    def test_water_moves_toward_lower_cells(self):
        world = World(seed=1)
        # Force a clean, known slope: (5,5) is high, its flow target (5,6)
        # is low, everything else flat and irrelevant to this check.
        world.fields["elevation"][5][5] = 10.0
        world.fields["elevation"][5][6] = 0.0
        world._recompute_flow_directions()
        self.assertEqual(world.flow_direction[5][5], (5, 6))

        world.fields["surface_water"][5][5] = 100.0
        world.fields["surface_water"][5][6] = 0.0
        outflow, inflow = hydrology.redistribute_flow(world)
        self.assertGreater(outflow[5][5], 0)
        self.assertGreater(inflow[5][6], 0)
        self.assertGreater(world.fields["surface_water"][5][6], 0)

    def test_closed_depressions_retain_water(self):
        world = World(seed=2)
        # Make (10,10) a strict local minimum among its 8-neighbors.
        r, c = 10, 10
        world.fields["elevation"][r][c] = -5.0
        for nr, nc in world.neighbors(r, c, diagonal=True):
            world.fields["elevation"][nr][nc] = 5.0
        world._recompute_flow_directions()
        self.assertIsNone(world.flow_direction[r][c])

        world.fields["surface_water"][r][c] = 50.0
        outflow, inflow = hydrology.redistribute_flow(world)
        self.assertEqual(outflow[r][c], 0.0)
        # Water conserved at the pit: nothing left, nothing arrived from
        # neighbors we didn't seed.
        self.assertEqual(world.fields["surface_water"][r][c], 50.0)

    def test_saturated_cells_produce_more_runoff(self):
        dry = World(seed=3)
        wet = World(seed=3)
        r, c = 20, 20
        for w in (dry, wet):
            w.fields["elevation"][r][c] = 10.0
            for nr, nc in w.neighbors(r, c, diagonal=True):
                w.fields["elevation"][nr][nc] = 0.0
            w._recompute_flow_directions()
            w.fields["surface_water"][r][c] = 100.0
        dry.fields["soil_moisture"][r][c] = 0.05
        wet.fields["soil_moisture"][r][c] = 0.95

        hydrology.infiltrate_and_evaporate(dry)
        hydrology.infiltrate_and_evaporate(wet)
        dry_outflow, _ = hydrology.redistribute_flow(dry)
        wet_outflow, _ = hydrology.redistribute_flow(wet)
        self.assertGreater(wet_outflow[r][c], dry_outflow[r][c])


if __name__ == "__main__":
    unittest.main()
