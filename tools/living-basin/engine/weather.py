"""Scripted rainfall events -- no general weather model in v0.

Each RainEvent is a fixed, config-declared block of ticks with a constant
rainfall rate. `active_rate(tick)` returns the mm/hr rate for the current
tick, or 0.0 if no rain event is active.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RainEvent:
    start_tick: int
    duration_ticks: int
    rainfall_mm_per_hour: float

    @property
    def end_tick(self) -> int:
        return self.start_tick + self.duration_ticks

    def active_at(self, tick: int) -> bool:
        return self.start_tick <= tick < self.end_tick


class RainSchedule:
    """Immutable and stateless by design: a single RainSchedule instance
    must be safe to hand to more than one Simulation (or to the same
    Simulation across a reset) without their histories interfering with
    each other -- so `just_started` is a pure function of `tick`, not a
    one-shot trigger with internal bookkeeping.
    """

    def __init__(self, events: list[RainEvent]):
        self.events = sorted(events, key=lambda e: e.start_tick)

    def active_rate(self, tick: int) -> float:
        for evt in self.events:
            if evt.active_at(tick):
                return evt.rainfall_mm_per_hour
        return 0.0

    def just_started(self, tick: int) -> RainEvent | None:
        """Returns the RainEvent if one begins exactly at `tick` (edge-
        triggered: Simulation.tick() calls this at most once per tick, so no
        internal "already fired" state is needed)."""
        for evt in self.events:
            if evt.start_tick == tick:
                return evt
        return None
