"""64x64 basin grid state: field storage, elevation generation, neighbors."""

from __future__ import annotations

import hashlib
import math
import random

from . import config

Cell = tuple[int, int]


def _make_field(fill: float) -> list[list[float]]:
    return [[fill for _ in range(config.GRID_SIZE)] for _ in range(config.GRID_SIZE)]


def generate_elevation(seed: int) -> list[list[float]]:
    """Deterministic bowl-shaped basin with a ridge and a single low-elevation
    outflow slope, plus small seeded roughness. Not a real DEM -- a shape
    designed so water has somewhere consistent to go and a slope exists for
    the acceptance scenario's trail/gully to sit on.
    """
    n = config.GRID_SIZE
    cx, cy = n / 2.0, n / 2.0
    rng = random.Random(seed)
    elev = _make_field(0.0)
    for r in range(n):
        for c in range(n):
            dx, dy = (c - cx) / n, (r - cy) / n
            dist = math.sqrt(dx * dx + dy * dy)
            bowl = dist * dist * 18.0          # rim high, center low
            # A diagonal slope band (roughly NW->SE) that gives a consistent
            # downhill direction for the demonstration trail/gully.
            slope = (c - r) * 0.06
            roughness = rng.uniform(-0.15, 0.15)
            elev[r][c] = round(bowl + slope + roughness, 4)
    return elev


class World:
    """All per-cell field state for the basin, plus neighbor/flow helpers."""

    def __init__(self, seed: int):
        self.seed = seed
        n = config.GRID_SIZE
        self.n = n
        self.fields: dict[str, list[list[float]]] = {
            name: _make_field(0.0) for name in config.FIELD_NAMES
        }
        self.fields["elevation"] = generate_elevation(seed)
        self.fields["soil_cohesion"] = _make_field(config.COHESION_BASE)
        self.fields["organic_content"] = _make_field(0.15)
        self.fields["vegetation_biomass"] = _make_field(0.35)
        self.fields["root_density"] = _make_field(0.30)
        self.flow_direction: list[list[Cell | None]] = [[None] * n for _ in range(n)]
        self._recompute_flow_directions()

    def in_bounds(self, r: int, c: int) -> bool:
        return 0 <= r < self.n and 0 <= c < self.n

    def neighbors(self, r: int, c: int, diagonal: bool = True) -> list[Cell]:
        """4-neighbor by default call site controls; diagonal=True gives the
        8-neighbor set used throughout this engine (documented choice: flow
        and movement both use 8-neighbor connectivity so diagonal downhill
        paths are available, matching the diagonal slope band in the terrain).
        """
        offsets = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        if diagonal:
            offsets += [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        out = []
        for dr, dc in offsets:
            nr, nc = r + dr, c + dc
            if self.in_bounds(nr, nc):
                out.append((nr, nc))
        return out

    def effective_elevation(self, r: int, c: int) -> float:
        """Elevation plus accumulated erosion depth (erosion lowers the
        effective surface further, which is what water actually flows over).
        """
        return self.fields["elevation"][r][c] - self.fields["erosion_depth"][r][c]

    def _recompute_flow_directions(self) -> None:
        """Steepest-descent flow direction to an 8-neighbor, or None if the
        cell is a local minimum (a hollow that can retain water as a pool).
        """
        for r in range(self.n):
            for c in range(self.n):
                here = self.effective_elevation(r, c)
                best: Cell | None = None
                best_drop = 0.0
                for nr, nc in self.neighbors(r, c, diagonal=True):
                    drop = here - self.effective_elevation(nr, nc)
                    if drop > best_drop:
                        best_drop = drop
                        best = (nr, nc)
                self.flow_direction[r][c] = best

    def local_slope(self, r: int, c: int) -> float:
        """Elevation drop (meters) to the steepest downhill 8-neighbor, 0 if
        this cell is a local minimum."""
        target = self.flow_direction[r][c]
        if target is None:
            return 0.0
        nr, nc = target
        return max(0.0, self.effective_elevation(r, c) - self.effective_elevation(nr, nc))

    def inflow_slope(self, r: int, c: int) -> float:
        """Elevation drop (meters) from the steepest *uphill* 8-neighbor
        into this cell -- the gradient driving water INTO the cell, as
        opposed to `local_slope`'s gradient driving water OUT of it.

        Erosion in this engine is gated on whichever gradient is steeper
        (see erosion.py): a mid-slope cell erodes via its own outflow
        gradient (sheet/rill erosion), while a pit fed by a steep incoming
        flow can erode as a knickpoint even though it has no downhill
        neighbor of its own -- both are real gully morphologies, and a
        model that only recognized the first would let concentrated
        inflow into a hollow erode nothing, which is not the intended
        causal story.
        """
        here = self.effective_elevation(r, c)
        best = 0.0
        for nr, nc in self.neighbors(r, c, diagonal=True):
            drop = self.effective_elevation(nr, nc) - here
            if drop > best:
                best = drop
        return best

    def checksum(self) -> str:
        """Deterministic hash of all field values, for replay verification."""
        h = hashlib.sha256()
        for name in sorted(self.fields):
            grid = self.fields[name]
            for row in grid:
                h.update(",".join(f"{v:.6f}" for v in row).encode())
                h.update(b"|")
        return h.hexdigest()

    def snapshot(self, layers: list[str] | None = None) -> dict:
        """A JSON-serializable snapshot of the requested layers (rounded for
        compact storage); defaults to the layers the viewer renders."""
        layers = layers or [
            "elevation",
            "soil_moisture",
            "vegetation_biomass",
            "surface_water",
            "trail_intensity",
            "erosion_depth",
        ]
        return {
            name: [[round(v, 3) for v in row] for row in self.fields[name]]
            for name in layers
        }
