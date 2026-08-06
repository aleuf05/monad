"""The one deterministic acceptance-demonstration scenario.

Seed 42, this exact rain schedule, this exact herbivore start band: tuned
(see ARCHITECTURE.md) so that herbivores graze down a real slope, a trail
and grazed patches mature, a heavy rain event saturates the area, cohesion
collapses where roots were already thin, and at least one ErosiveGully
forms with a full multi-node causal lineage (rain -> saturation -> root
loss / cohesion degradation -> erosion). No gully is placed by hand --
this file only chooses the *conditions*; engine/erosion.py decides whether
and where thresholds are crossed.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from engine import Simulation, RainEvent, RainSchedule  # noqa: E402

DEMO_SEED = 42
DEMO_TICKS = 300
DEMO_HERBIVORE_BAND = (12, 50, 12, 50)
DEMO_RAIN = RainSchedule(
    [RainEvent(start_tick=100, duration_ticks=20, rainfall_mm_per_hour=48)]
)
SNAPSHOT_INTERVAL = 5


def build_simulation() -> Simulation:
    return Simulation(
        seed=DEMO_SEED,
        rain_schedule=DEMO_RAIN,
        herbivore_start_band=DEMO_HERBIVORE_BAND,
    )
