"""Soil cohesion relaxation and threshold-gated erosion / gully formation.

Erosion at a cell only accumulates when *all* of these hold simultaneously
(the "combination of conditions" the build packet calls for):

  - runoff leaving the cell this tick   > EROSION_RUNOFF_THRESHOLD
  - soil_moisture (saturation)          >= EROSION_SATURATION_THRESHOLD
  - soil_cohesion                       <= EROSION_COHESION_THRESHOLD
  - local slope (drop to downhill nbr)  >= EROSION_SLOPE_THRESHOLD

Erosion is gradual (a fraction of the excess runoff/weakness per tick), so
"repeated flow persistence" is naturally required to cross the gully
threshold -- a single qualifying tick is not enough. erosion_depth is
monotonic non-decreasing; once a cell crosses GULLY_DEPTH_THRESHOLD it stays
a gully (current_status may still change, e.g. to "Stabilizing").
"""

from __future__ import annotations

from . import config


def _cohesion_target(world, r: int, c: int) -> float:
    roots = world.fields["root_density"][r][c]
    organic = world.fields["organic_content"][r][c]
    sm = world.fields["soil_moisture"][r][c]
    sat_excess = max(0.0, sm - config.SATURATION_THRESHOLD) / max(1e-6, 1.0 - config.SATURATION_THRESHOLD)
    target = (
        config.COHESION_BASE
        + config.COHESION_ROOT_WEIGHT * roots
        + config.COHESION_ORGANIC_WEIGHT * organic
        - config.COHESION_SATURATION_PENALTY * sat_excess
    )
    return max(0.0, min(1.0, target))


def update_cohesion(world, previous_low_cohesion: list[list[bool]]) -> list[tuple[int, int]]:
    """Relaxes soil_cohesion toward its target; returns cells whose cohesion
    just crossed COHESION_DEGRADED_THRESHOLD downward this tick."""
    cohesion = world.fields["soil_cohesion"]
    out = []
    for r in range(world.n):
        for c in range(world.n):
            target = _cohesion_target(world, r, c)
            cohesion[r][c] += (target - cohesion[r][c]) * config.COHESION_RELAX_RATE
            now_low = cohesion[r][c] <= config.COHESION_DEGRADED_THRESHOLD
            if now_low and not previous_low_cohesion[r][c]:
                out.append((r, c))
            previous_low_cohesion[r][c] = now_low
    return out


def apply_erosion(
    world,
    outflow: list[list[float]],
    inflow: list[list[float]],
    rainfall_rate: float,
) -> list[dict]:
    """Applies this tick's erosion and returns a list of per-cell input
    dicts (one per cell where erosion actually accrued), for use both by
    gully-threshold checks and, when a gully forms, as the event's
    `inputs` block."""
    depth = world.fields["erosion_depth"]
    cohesion = world.fields["soil_cohesion"]
    sm = world.fields["soil_moisture"]
    roots = world.fields["root_density"]
    accrued: list[dict] = []

    for r in range(world.n):
        for c in range(world.n):
            # Whichever flow is stronger drives erosion here: outflow for
            # ordinary mid-slope cells, inflow for a pit being actively fed.
            ro = max(outflow[r][c], inflow[r][c])
            if ro <= config.EROSION_RUNOFF_THRESHOLD:
                continue
            if sm[r][c] < config.EROSION_SATURATION_THRESHOLD:
                continue
            if cohesion[r][c] > config.EROSION_COHESION_THRESHOLD:
                continue
            # Steeper of the outflow gradient (mid-slope erosion) and the
            # inflow gradient (knickpoint erosion at a fed hollow) -- see
            # World.inflow_slope's docstring.
            slope = max(world.local_slope(r, c), world.inflow_slope(r, c))
            if slope < config.EROSION_SLOPE_THRESHOLD:
                continue

            excess_runoff = ro - config.EROSION_RUNOFF_THRESHOLD
            weakness = 1.0 - cohesion[r][c]
            gain = config.EROSION_RATE * excess_runoff * weakness * 0.08
            depth[r][c] += gain
            # Self-reinforcing feedback: erosion further degrades local
            # cohesion, a documented, deliberate modeling choice.
            cohesion[r][c] = max(0.0, cohesion[r][c] - gain * 0.5)

            accrued.append(
                {
                    "cell": (r, c),
                    "rainfall_mm_per_hour": rainfall_rate,
                    "soil_saturation": round(sm[r][c], 4),
                    "soil_cohesion": round(cohesion[r][c], 4),
                    "root_density": round(roots[r][c], 4),
                    "local_slope": round(slope, 4),
                    "runoff": round(ro, 4),
                    "erosion_depth": round(depth[r][c], 4),
                    "erosion_depth_delta": round(gain, 4),
                }
            )
    return accrued
