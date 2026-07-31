"""Simulation orchestrator: the explicit, ordered, deterministic tick pipeline.

Tick order (fixed, tested in tests/test_determinism.py):

  1. weather                     (scripted rain schedule lookup)
  2. rainfall deposition
  3. water infiltration + evaporation
  4. flow-direction recompute + surface-water redistribution (runoff)
  5. vegetation growth / stress
  6. root-density update (lags biomass)
  7. herbivore movement
  8. grazing (folded into herbivore movement -- an agent grazes the cell it
     moves onto, so movement and grazing are inseparable per-agent per-tick)
  9. trail accumulation
  10. soil cohesion update
  11. erosion
  12. feature detection
  13. provenance recording

All randomness (herbivore movement; elevation roughness, generated once at
World construction) is drawn from `random.Random` instances seeded from the
simulation seed -- no other source of nondeterminism is used anywhere in
this pipeline.
"""

from __future__ import annotations

import random

from . import config, erosion, herbivores, hydrology, trails, vegetation
from .events import EventLog
from .features import FeatureRegistry
from .grid import World
from .weather import RainSchedule


class Simulation:
    def __init__(
        self,
        seed: int,
        rain_schedule: RainSchedule | None = None,
        herbivore_start_band: tuple[int, int, int, int] = (12, 50, 12, 50),
    ):
        self.seed = seed
        self.world = World(seed)
        self.event_log = EventLog()
        self.features = FeatureRegistry()
        self.tick_count = 0
        self.rng = random.Random(seed ^ 0x5EED_F00D)
        self.rain_schedule = rain_schedule or RainSchedule([])
        self.herds = herbivores.spawn_herbivores(self.world, self.rng, herbivore_start_band)

        n = self.world.n
        self._previous_saturation = [[False] * n for _ in range(n)]
        self._previous_low_root = [[False] * n for _ in range(n)]
        self._previous_low_cohesion = [[False] * n for _ in range(n)]
        self._pool_persist = [[0] * n for _ in range(n)]

        self._last_rain_event_id: str | None = None
        self._last_saturation_event: dict[tuple[int, int], str] = {}
        self._last_root_loss_event: dict[tuple[int, int], str] = {}
        self._last_cohesion_event: dict[tuple[int, int], str] = {}

    # -- pipeline ------------------------------------------------------

    def tick(self) -> None:
        t = self.tick_count
        world = self.world

        rate = self.rain_schedule.active_rate(t)
        started = self.rain_schedule.just_started(t)
        if started is not None:
            evt = self.event_log.record(
                tick=t,
                event_type="rain_started",
                cell=None,
                inputs={
                    "rainfall_mm_per_hour": started.rainfall_mm_per_hour,
                    "duration_ticks": started.duration_ticks,
                },
            )
            self._last_rain_event_id = evt.event_id

        hydrology.apply_rainfall(world, rate)
        hydrology.infiltrate_and_evaporate(world)
        world._recompute_flow_directions()
        outflow, inflow = hydrology.redistribute_flow(world)
        newly_sat = hydrology.newly_saturated_cells(world, self._previous_saturation)

        vegetation.grow_and_build_organics(world)
        newly_low_root = vegetation.update_root_density(world, self._previous_low_root)

        visited, grazed = herbivores.step(world, self.herds, self.rng)
        herbivores.decay_grazing_pressure(world)

        trails.accumulate(world, visited)

        newly_low_cohesion = erosion.update_cohesion(world, self._previous_low_cohesion)
        erosion_inputs = erosion.apply_erosion(world, outflow, inflow, rate)

        self._record_saturation_events(t, newly_sat)
        self._record_root_loss_events(t, newly_low_root)
        self._record_cohesion_events(t, newly_low_cohesion)
        self._detect_trails(t, visited)
        self._detect_grazed_patches(t, grazed)
        self._detect_pools(t)
        self._detect_gullies(t, erosion_inputs)

        self.tick_count += 1

    def run(self, num_ticks: int) -> None:
        for _ in range(num_ticks):
            self.tick()

    # -- provenance / feature detection --------------------------------

    def _record_saturation_events(self, t, cells):
        sm = self.world.fields["soil_moisture"]
        for cell in cells:
            evt = self.event_log.record(
                tick=t,
                event_type="saturation_exceeded",
                cell=cell,
                inputs={"soil_saturation": round(sm[cell[0]][cell[1]], 4)},
                caused_by=[self._last_rain_event_id] if self._last_rain_event_id else [],
            )
            self._last_saturation_event[cell] = evt.event_id

    def _record_root_loss_events(self, t, cells):
        roots = self.world.fields["root_density"]
        for cell in cells:
            evt = self.event_log.record(
                tick=t,
                event_type="root_loss",
                cell=cell,
                inputs={"root_density": round(roots[cell[0]][cell[1]], 4)},
            )
            self._last_root_loss_event[cell] = evt.event_id

    def _record_cohesion_events(self, t, cells):
        coh = self.world.fields["soil_cohesion"]
        for cell in cells:
            causes = []
            if cell in self._last_root_loss_event:
                causes.append(self._last_root_loss_event[cell])
            if cell in self._last_saturation_event:
                causes.append(self._last_saturation_event[cell])
            evt = self.event_log.record(
                tick=t,
                event_type="cohesion_degraded",
                cell=cell,
                inputs={"soil_cohesion": round(coh[cell[0]][cell[1]], 4)},
                caused_by=causes,
            )
            self._last_cohesion_event[cell] = evt.event_id

    def _detect_trails(self, t, visited_cells):
        trail = self.world.fields["trail_intensity"]
        seen = set()
        for cell in visited_cells:
            if cell in seen:
                continue
            seen.add(cell)
            if (
                trail[cell[0]][cell[1]] >= config.TRAIL_MATURE_THRESHOLD
                and self.features.feature_of_type_at(cell, "HerbivoreTrail") is None
            ):
                evt = self.event_log.record(
                    tick=t,
                    event_type="trail_formed",
                    cell=cell,
                    inputs={"trail_intensity": round(trail[cell[0]][cell[1]], 4)},
                )
                self.features.create("HerbivoreTrail", [cell], t, evt.event_id)

    def _detect_grazed_patches(self, t, grazed_cells):
        pressure = self.world.fields["grazing_pressure"]
        seen = set()
        for cell in grazed_cells:
            if cell in seen:
                continue
            seen.add(cell)
            if (
                pressure[cell[0]][cell[1]] >= config.GRAZED_PATCH_THRESHOLD
                and self.features.feature_of_type_at(cell, "GrazedPatch") is None
            ):
                evt = self.event_log.record(
                    tick=t,
                    event_type="grazed_patch_formed",
                    cell=cell,
                    inputs={"grazing_pressure": round(pressure[cell[0]][cell[1]], 4)},
                )
                self.features.create("GrazedPatch", [cell], t, evt.event_id)

    def _detect_pools(self, t):
        sw = self.world.fields["surface_water"]
        n = self.world.n
        for r in range(n):
            for c in range(n):
                # Only true local minima (nowhere downhill to flow) can
                # register as a WaterPool -- a saturated slope is not a
                # "pool", it's just wet ground mid-storm.
                if self.world.flow_direction[r][c] is None and sw[r][c] >= config.POOL_WATER_THRESHOLD:
                    self._pool_persist[r][c] += 1
                else:
                    self._pool_persist[r][c] = 0
                if (
                    self._pool_persist[r][c] == config.POOL_PERSIST_TICKS
                    and self.features.feature_of_type_at((r, c), "WaterPool") is None
                ):
                    evt = self.event_log.record(
                        tick=t,
                        event_type="pool_formed",
                        cell=(r, c),
                        inputs={"surface_water": round(sw[r][c], 4)},
                        caused_by=[self._last_rain_event_id] if self._last_rain_event_id else [],
                    )
                    self.features.create("WaterPool", [(r, c)], t, evt.event_id)

    def _detect_gullies(self, t, erosion_inputs):
        for info in erosion_inputs:
            cell = info["cell"]
            if info["erosion_depth"] < config.GULLY_DEPTH_THRESHOLD:
                continue
            if self.features.feature_of_type_at(cell, "ErosiveGully") is not None:
                continue
            causes = []
            if self._last_rain_event_id:
                causes.append(self._last_rain_event_id)
            if cell in self._last_saturation_event:
                causes.append(self._last_saturation_event[cell])
            if cell in self._last_root_loss_event:
                causes.append(self._last_root_loss_event[cell])
            if cell in self._last_cohesion_event:
                causes.append(self._last_cohesion_event[cell])

            inputs = {k: v for k, v in info.items() if k not in ("cell", "erosion_depth_delta")}
            evt = self.event_log.record(
                tick=t,
                event_type="gully_formed",
                cell=cell,
                inputs=inputs,
                caused_by=causes,
                result={"erosion_depth_delta": info["erosion_depth_delta"]},
            )
            feat = self.features.create("ErosiveGully", [cell], t, evt.event_id)
            evt.result["feature_id"] = feat.feature_id

    def checksum(self) -> str:
        return self.world.checksum()
