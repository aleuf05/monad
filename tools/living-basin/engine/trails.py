"""Trail accumulation from repeated herbivore passage, with slow decay."""

from __future__ import annotations

from . import config


def accumulate(world, visited_cells: list[tuple[int, int]]) -> None:
    trail = world.fields["trail_intensity"]
    for r in range(world.n):
        row = trail[r]
        for c in range(world.n):
            row[c] = max(0.0, row[c] - config.TRAIL_DECAY)
    for r, c in visited_cells:
        trail[r][c] = min(1.0, trail[r][c] + config.TRAIL_GAIN_PER_PASS)
