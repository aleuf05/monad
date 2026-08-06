"""Small herbivore agents: weighted rules-based movement, grazing.

No path planning or memory -- each tick, each agent picks its next cell from
its current 8-neighborhood (plus "stay put") via a weight combining local
vegetation biomass (attractive) and slope (steep climbs discouraged), with
seeded randomness breaking ties. This is enough to produce repeated passage
along the same accessible, vegetated route -- which is what the trail/
grazing/erosion causal chain needs, without any real cognition.
"""

from __future__ import annotations

import random

from . import config


class Herbivore:
    def __init__(self, herbivore_id: int, start: tuple[int, int]):
        self.herbivore_id = herbivore_id
        self.position = start


def spawn_herbivores(world, rng: random.Random, start_band: tuple[int, int, int, int]) -> list[Herbivore]:
    """start_band = (row_min, row_max, col_min, col_max): herbivores spawn
    at random cells within this rectangle (inclusive), a scenario-level
    choice, not a general placement policy."""
    r0, r1, c0, c1 = start_band
    herds = []
    for i in range(config.HERBIVORE_COUNT):
        start = (rng.randint(r0, r1), rng.randint(c0, c1))
        herds.append(Herbivore(i, start))
    return herds


def _weight(world, r: int, c: int, cur_elev: float) -> float:
    biomass = world.fields["vegetation_biomass"][r][c]
    elev = world.effective_elevation(r, c)
    climb_penalty = max(0.0, elev - cur_elev)
    w = 0.4 + 3.0 * biomass - 1.2 * climb_penalty
    return max(0.02, w)


def step(world, herds: list[Herbivore], rng: random.Random) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    """Advances each herbivore one move and grazes its new cell. Returns
    (visited_cells, grazed_cells) for this tick (both are the agents'
    post-move positions; grazing only occurs where biomass > 0)."""
    biomass = world.fields["vegetation_biomass"]
    pressure = world.fields["grazing_pressure"]
    visited: list[tuple[int, int]] = []
    grazed: list[tuple[int, int]] = []

    for h in herds:
        r, c = h.position
        cur_elev = world.effective_elevation(r, c)
        options = [(r, c)] + world.neighbors(r, c, diagonal=True)
        weights = [_weight(world, orr, occ, cur_elev) for orr, occ in options]
        total = sum(weights)
        pick = rng.uniform(0, total)
        acc = 0.0
        chosen = options[-1]
        for opt, w in zip(options, weights):
            acc += w
            if pick <= acc:
                chosen = opt
                break
        h.position = chosen
        visited.append(chosen)

        vr, vc = chosen
        if biomass[vr][vc] > 0.01:
            grazed_amount = min(biomass[vr][vc], config.GRAZE_RATE)
            biomass[vr][vc] -= grazed_amount
            pressure[vr][vc] = min(1.0, pressure[vr][vc] + config.GRAZING_PRESSURE_GAIN)
            grazed.append(chosen)

    return visited, grazed


def decay_grazing_pressure(world) -> None:
    pressure = world.fields["grazing_pressure"]
    for r in range(world.n):
        for c in range(world.n):
            pressure[r][c] = max(0.0, pressure[r][c] - config.GRAZING_PRESSURE_DECAY)
