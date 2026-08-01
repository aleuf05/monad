"""Component B orchestration: manifest, sweep, probes, and replay digest."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from monad_zero.organism import MonadOrganism
from .manifest import make_manifest, replay_digest
from .sweep_controller import SweepController, SweepDirection, SweepRate


@dataclass
class NexusRun:
    manifest: dict[str, Any]
    events: list[dict[str, Any]]
    replay_digest: str

    def as_dict(self) -> dict[str, Any]:
        return {"manifest": self.manifest, "events": self.events, "replay_digest": self.replay_digest}

    def write(self, directory: str) -> None:
        from pathlib import Path
        import json
        target = Path(directory)
        target.mkdir(parents=True, exist_ok=True)
        (target / f"{self.manifest['run_id']}.manifest.json").write_text(json.dumps(self.manifest, indent=2, sort_keys=True) + "\n")
        (target / f"{self.manifest['run_id']}.events.jsonl").write_text("".join(json.dumps(event, sort_keys=True) + "\n" for event in self.events))
        (target / f"{self.manifest['run_id']}.digest.txt").write_text(self.replay_digest + "\n")


class NexusHarness:
    def __init__(self, *, points: int = 11, rate: SweepRate = SweepRate.FAST, ticks_per_step: int = 1):
        self.sweeper = SweepController(points=points)
        self.rate = rate
        self.ticks_per_step = ticks_per_step

    def run(self, seed: int = 0, control: str = "integrated", direction: SweepDirection = SweepDirection.FORWARD) -> NexusRun:
        run_id = f"nexus-{control}-{seed}"
        organism = MonadOrganism(seed=seed, run_id=run_id, control_mode=control)
        schedule = self.sweeper.schedule(direction, self.rate)
        manifest = make_manifest(
            run_id=run_id, seed=seed, mode=f"{direction.value.lower()}_sweep", control=control,
            q_schedule=[step.q for step in schedule], perturbation_schedule=[], compute_budget={"ticks_per_step": self.ticks_per_step},
        )
        events = self.sweeper.run(organism, direction, self.rate, ticks_per_step=self.ticks_per_step)
        return NexusRun(manifest=manifest, events=events, replay_digest=replay_digest(events))
