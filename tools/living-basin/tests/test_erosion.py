import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.grid import World
from engine import config, erosion
from engine.simulation import Simulation
from engine.weather import RainSchedule


def _sloped_world(seed, root_density, cohesion, moisture):
    world = World(seed=seed)
    r, c = 20, 20
    world.fields["elevation"][r][c] = 10.0
    for nr, nc in world.neighbors(r, c, diagonal=True):
        world.fields["elevation"][nr][nc] = 0.0
    world._recompute_flow_directions()
    world.fields["root_density"][r][c] = root_density
    world.fields["soil_cohesion"][r][c] = cohesion
    world.fields["soil_moisture"][r][c] = moisture
    world.fields["surface_water"][r][c] = 500.0  # plenty to produce runoff
    return world, (r, c)


class ErosionTest(unittest.TestCase):
    def test_high_runoff_weak_soil_can_erode(self):
        world, cell = _sloped_world(1, root_density=0.05, cohesion=0.1, moisture=0.95)
        outflow, inflow = _redistribute(world)
        before = world.fields["erosion_depth"][cell[0]][cell[1]]
        accrued = erosion.apply_erosion(world, outflow, inflow, rainfall_rate=48)
        after = world.fields["erosion_depth"][cell[0]][cell[1]]
        self.assertGreater(after, before)
        self.assertTrue(any(a["cell"] == cell for a in accrued))

    def test_strong_root_density_reduces_erosion_likelihood(self):
        weak, cell = _sloped_world(2, root_density=0.05, cohesion=0.1, moisture=0.95)
        strong, _ = _sloped_world(2, root_density=0.95, cohesion=0.85, moisture=0.95)

        weak_outflow, weak_inflow = _redistribute(weak)
        strong_outflow, strong_inflow = _redistribute(strong)

        weak_accrued = erosion.apply_erosion(weak, weak_outflow, weak_inflow, rainfall_rate=48)
        strong_accrued = erosion.apply_erosion(strong, strong_outflow, strong_inflow, rainfall_rate=48)

        self.assertTrue(any(a["cell"] == cell for a in weak_accrued))
        self.assertFalse(any(a["cell"] == cell for a in strong_accrued))

    def test_gully_cannot_form_without_threshold_conditions(self):
        """No rain at all -> saturation never crosses -> no gully, no matter
        how many ticks run."""
        sim = Simulation(seed=99, rain_schedule=RainSchedule([]))
        sim.run(150)
        gullies = [f for f in sim.features.all() if f.feature_type == "ErosiveGully"]
        self.assertEqual(gullies, [])

    def test_gully_requires_all_four_conditions_not_just_saturation(self):
        """High saturation alone, with strong cohesion and no slope, must
        not erode."""
        world = World(seed=3)
        r, c = 25, 25
        # Flat neighborhood: no slope in any direction.
        for nr, nc in [(r, c)] + world.neighbors(r, c, diagonal=True):
            world.fields["elevation"][nr][nc] = 5.0
        world._recompute_flow_directions()
        world.fields["soil_moisture"][r][c] = 0.95
        world.fields["soil_cohesion"][r][c] = 0.05
        world.fields["surface_water"][r][c] = 500.0
        outflow, inflow = _redistribute(world)
        accrued = erosion.apply_erosion(world, outflow, inflow, rainfall_rate=48)
        self.assertFalse(any(a["cell"] == (r, c) for a in accrued))


def _redistribute(world):
    from engine import hydrology

    return hydrology.redistribute_flow(world)


if __name__ == "__main__":
    unittest.main()
