"""Preregistered bidirectional q sweeps."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from monad_zero.organism import ArchitectureVector, MonadOrganism


class SweepDirection(str, Enum):
    FORWARD = "FORWARD"
    REVERSE = "REVERSE"


class SweepRate(str, Enum):
    SLOW = "SLOW"
    MEDIUM = "MEDIUM"
    FAST = "FAST"


TICKS_PER_STEP = {SweepRate.SLOW: 500, SweepRate.MEDIUM: 200, SweepRate.FAST: 50}


def architecture_vector_for_q(q: float) -> ArchitectureVector:
    q = max(0.0, min(1.0, float(q)))
    return ArchitectureVector(
        D_a=q, H_p=q,
        R_d=0 if q < 0.25 else 1 if q < 0.50 else 2 if q < 0.75 else 3,
        O_c=q, A_s=q,
    )


@dataclass(frozen=True)
class SweepStep:
    index: int
    q: float
    direction: SweepDirection
    rate: SweepRate
    ticks: int


class SweepController:
    def __init__(self, points: int = 11):
        if points < 2:
            raise ValueError("points must be at least 2")
        self.points = points

    def schedule(self, direction: SweepDirection, rate: SweepRate) -> list[SweepStep]:
        values = [index / (self.points - 1) for index in range(self.points)]
        if direction == SweepDirection.REVERSE:
            values.reverse()
        return [SweepStep(index, q, direction, rate, TICKS_PER_STEP[rate]) for index, q in enumerate(values)]

    def run(self, organism: MonadOrganism, direction: SweepDirection, rate: SweepRate, *, ticks_per_step: int | None = None) -> list[dict]:
        events: list[dict] = []
        for step in self.schedule(direction, rate):
            organism.configure_sweep(step.direction.value, step.rate.value, step.q)
            organism.request_architecture_update(architecture_vector_for_q(step.q), source="sweep-controller", reason=f"{step.direction.value} q step {step.index}")
            for _ in range(ticks_per_step if ticks_per_step is not None else step.ticks):
                events.extend(organism.drain_events())
                events.append(organism.tick())
        events.extend(organism.drain_events())
        return events
