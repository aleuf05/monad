"""Standardized probes and persistent, normalized recovery measurement."""
from __future__ import annotations

from dataclasses import dataclass

from monad_zero.organism import MonadOrganism, PerturbationType


@dataclass(frozen=True)
class RecoveryPolicy:
    epsilon: float = 0.15
    consecutive_ticks: int = 5


class PerturbationEngine:
    def __init__(self, policy: RecoveryPolicy | None = None):
        self.policy = policy or RecoveryPolicy()

    def fire_probe(self, organism: MonadOrganism, probe_type: PerturbationType, duration_ticks: int = 10) -> tuple[str, list[dict]]:
        organism.recovery_epsilon = self.policy.epsilon
        organism.recovery_required_ticks = self.policy.consecutive_ticks
        probe_id = organism.inject_perturbation(probe_type, duration_ticks)
        events = []
        for _ in range(duration_ticks + self.policy.consecutive_ticks):
            events.extend(organism.drain_events())
            events.append(organism.tick())
        events.extend(organism.drain_events())
        return probe_id, events
