"""Water: rainfall deposition, infiltration, runoff, downhill flow.

Deliberately simple and documented as such (see ARCHITECTURE.md): this is
not a physically accurate fluid model. Flow uses 8-neighbor steepest descent
(`world.flow_direction`, computed in grid.py). Infiltration capacity rises
with root_density (root channels), consistent with the vegetation/erosion
causal chain the prototype is built to demonstrate.
"""

from __future__ import annotations

from . import config


def apply_rainfall(world, rate_mm_per_hour: float) -> None:
    """Adds this tick's rainfall to surface_water uniformly (one tick is
    treated as one hour of simulated time for unit simplicity)."""
    if rate_mm_per_hour <= 0:
        return
    sw = world.fields["surface_water"]
    deposit = rate_mm_per_hour * config.RAINFALL_DT_HOURS
    for r in range(world.n):
        row = sw[r]
        for c in range(world.n):
            row[c] += deposit


def infiltrate_and_evaporate(world) -> None:
    sw = world.fields["surface_water"]
    sm = world.fields["soil_moisture"]
    roots = world.fields["root_density"]
    for r in range(world.n):
        for c in range(world.n):
            capacity = config.INFILTRATION_BASE + config.INFILTRATION_ROOT_BONUS * roots[r][c]
            # Already-saturated soil has little pore space left to accept
            # more water, so its infiltration capacity is throttled by its
            # current soil_moisture -- this is what makes a saturated cell
            # shed more of its rain as runoff instead of absorbing it.
            capacity *= 1.0 - 0.6 * sm[r][c]
            infiltrated = min(sw[r][c], sw[r][c] * capacity + 0.02)
            sw[r][c] -= infiltrated
            # soil_moisture as a 0..1 fractional store; infiltrated mm feed it
            # at a fixed conversion (documented, provisional). The store is
            # deliberately large relative to a single rain tick's typical
            # infiltration, so only cells that keep receiving inflow --
            # genuine flow-convergence zones -- accumulate enough over many
            # ticks to saturate; an ordinary slope cell sheds most of its
            # rain as runoff/evaporation before that happens.
            sm[r][c] = min(1.0, sm[r][c] + infiltrated * config.MOISTURE_CONVERSION)
            # Deep drainage: water leaving to groundwater, distinct from
            # evaporation -- the only true outflow for a closed basin.
            sm[r][c] = max(0.0, sm[r][c] * (1.0 - config.EVAPORATION_RATE) - config.DEEP_DRAINAGE_RATE * sm[r][c])
            sw[r][c] = max(0.0, sw[r][c] * (1.0 - config.SURFACE_WATER_LOSS_RATE))


def redistribute_flow(world) -> tuple[list[list[float]], list[list[float]]]:
    """Moves a fraction of each cell's surface_water to its downhill
    neighbor (or leaves it in place if the cell is a local minimum, forming
    a pool). Returns (outflow, inflow) per-cell grids -- water leaving vs.
    arriving at each cell this tick, both used by erosion.py: outflow drives
    ordinary mid-slope erosion, inflow drives knickpoint erosion at a pit
    that is being actively fed (see World.inflow_slope).
    """
    sw = world.fields["surface_water"]
    n = world.n
    outflow = [[0.0] * n for _ in range(n)]
    inflow = [[0.0] * n for _ in range(n)]
    for r in range(n):
        for c in range(n):
            target = world.flow_direction[r][c]
            if target is None or sw[r][c] <= 0:
                continue
            moved = sw[r][c] * config.RUNOFF_FLOW_FRACTION
            outflow[r][c] = moved
            tr, tc = target
            inflow[tr][tc] += moved
    for r in range(n):
        for c in range(n):
            sw[r][c] = sw[r][c] - outflow[r][c] + inflow[r][c]
    return outflow, inflow


def newly_saturated_cells(world, previous_saturation: list[list[bool]]) -> list[tuple[int, int]]:
    """Edge-triggered: cells whose soil_moisture just crossed
    SATURATION_THRESHOLD upward this tick. Mutates `previous_saturation` in
    place to the new state for next tick's comparison."""
    sm = world.fields["soil_moisture"]
    out = []
    for r in range(world.n):
        for c in range(world.n):
            now = sm[r][c] >= config.SATURATION_THRESHOLD
            if now and not previous_saturation[r][c]:
                out.append((r, c))
            previous_saturation[r][c] = now
    return out
