"""Vegetation biomass, organic content, and root-density lag.

Root density approaches biomass exponentially rather than tracking it
instantly -- this lag is what lets "herbivore clearing" show up as a *prior*
cause of a *later* root-density crossing, which the acceptance scenario
depends on.
"""

from __future__ import annotations

from . import config


def grow_and_build_organics(world) -> None:
    biomass = world.fields["vegetation_biomass"]
    organic = world.fields["organic_content"]
    sm = world.fields["soil_moisture"]
    for r in range(world.n):
        for c in range(world.n):
            # Growth peaks at VEG_MOISTURE_OPTIMAL soil_moisture and falls
            # off (too dry or waterlogged) -- a documented triangular
            # response curve, not a real physiological model.
            m = sm[r][c]
            moisture_factor = max(0.0, 1.0 - abs(m - config.VEG_MOISTURE_OPTIMAL) / config.VEG_MOISTURE_OPTIMAL)
            headroom = 1.0 - biomass[r][c]
            biomass[r][c] = min(1.0, biomass[r][c] + config.VEG_GROWTH_RATE * moisture_factor * headroom)
            if biomass[r][c] > 0.5:
                organic[r][c] = min(1.0, organic[r][c] + config.ORGANIC_GROWTH_RATE * (biomass[r][c] - 0.5))


def update_root_density(world, previous_low_root: list[list[bool]]) -> list[tuple[int, int]]:
    """Root density relaxes toward biomass; returns cells whose root_density
    just crossed LOW_ROOT_THRESHOLD downward this tick (edge-triggered)."""
    roots = world.fields["root_density"]
    biomass = world.fields["vegetation_biomass"]
    out = []
    for r in range(world.n):
        for c in range(world.n):
            roots[r][c] += (biomass[r][c] - roots[r][c]) * config.ROOT_APPROACH_RATE
            roots[r][c] = max(0.0, min(1.0, roots[r][c]))
            now_low = roots[r][c] < config.LOW_ROOT_THRESHOLD
            if now_low and not previous_low_root[r][c]:
                out.append((r, c))
            previous_low_root[r][c] = now_low
    return out
