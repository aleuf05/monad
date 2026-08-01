"""Public Component A organism interface and cycle telemetry."""
from __future__ import annotations

import copy
import random
import uuid
from dataclasses import asdict, dataclass, fields
from enum import Enum
from typing import Any

from tools.monad0.engine import EnvironmentConfig, Monad0Controller, Sandbox


@dataclass(frozen=True)
class ArchitectureVector:
    D_a: float = 0.5
    H_p: float = 0.5
    R_d: int = 1
    O_c: float = 0.5
    A_s: float = 0.5

    def __post_init__(self) -> None:
        for name in ("D_a", "H_p", "O_c", "A_s"):
            value = float(getattr(self, name))
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be in [0, 1]")
        if not 0 <= int(self.R_d) <= 3:
            raise ValueError("R_d must be in [0, 3]")


class PerturbationType(str, Enum):
    MEMORY_ACCESS_REDUCTION = "MEMORY_ACCESS_REDUCTION"
    POLICY_BIAS_INJECTION = "POLICY_BIAS_INJECTION"
    MODEL_TARGET_DRIFT = "MODEL_TARGET_DRIFT"
    NO_OP = "NO_OP"


class PerturbationBusyError(RuntimeError):
    """Raised when a second probe is injected before the first is complete."""


@dataclass(frozen=True)
class ClosureComponents:
    D: float
    R: float
    H: float
    K: float
    A: float
    L: float
    F: float
    T: float


@dataclass(frozen=True)
class CycleTelemetry:
    schema_version: str
    run_id: str
    seed: int
    tick: int
    sweep_direction: str
    sweep_rate: str
    q: float
    architecture_vector: ArchitectureVector
    raw_closure_components: ClosureComponents
    nexus_closure_index: float
    state_regime_estimate: str | None
    perturbation_id: str | None
    recovery_time: int | None
    self_model_revision_id: str | None
    historical_parent_ids: tuple[str, ...]
    compute_used: float
    model_calls: int
    memory_bytes: int
    intervention_source: str
    welfare_flags: tuple[str, ...]
    control_mode: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class _ActivePerturbation:
    probe_id: str
    probe_type: PerturbationType
    started_tick: int
    duration_ticks: int
    reversible_patch: dict[str, Any]
    patched_values: dict[str, Any]

    def active(self, tick: int) -> bool:
        return tick < self.started_tick + self.duration_ticks


TELEMETRY_FIELDS = tuple(field.name for field in fields(CycleTelemetry))


class MonadOrganism:
    """A refinement-safe organism wrapper around the tested Monad-0 engine."""

    def __init__(self, seed: int = 0, run_id: str | None = None, control_mode: str = "monad-0") -> None:
        self.seed = seed
        self.run_id = run_id or str(uuid.uuid4())
        self.control_mode = control_mode
        self.sandbox = Sandbox(EnvironmentConfig(seed=seed))
        self.worker = Monad0Controller()
        self.architecture_vector = ArchitectureVector()
        self._pending_vector: ArchitectureVector | None = None
        self._pending_update: dict[str, Any] | None = None
        self._active: _ActivePerturbation | None = None
        self._probe_counter = 0
        self._revision = 0
        self._history: list[str] = []
        self._sweep_direction = "NONE"
        self._sweep_rate = "NONE"
        self._q = 0.0
        self._recovery_start: int | None = None
        self._recovery_baseline: ClosureComponents | None = None
        self._recovery_consecutive = 0
        self.recovery_epsilon = 0.15
        self.recovery_required_ticks = 5
        self.recovery_sigmas = {name: 0.05 for name in ("D", "R", "H", "K", "A", "L", "F", "T")}
        self._last_components: ClosureComponents | None = None
        self._events: list[dict[str, Any]] = []

    def configure_sweep(self, direction: str, rate: str, q: float) -> None:
        self._sweep_direction, self._sweep_rate, self._q = direction, rate, float(q)

    def request_architecture_update(self, vec: ArchitectureVector, *, source: str, reason: str) -> str:
        """Validate and queue an atomic vector update for the next tick boundary."""
        update_id = f"architecture-update-{self.sandbox.tick:05d}-{len(self._events):04d}"
        self._pending_vector = vec
        self._pending_update = {"update_id": update_id, "requested_vector": asdict(vec), "previous_vector": asdict(self.architecture_vector), "requested_tick": self.sandbox.tick, "source": source, "reason": reason}
        self._events.append({"type": "architecture_update_requested", **self._pending_update})
        return update_id

    def update_architecture_vector(self, vec: ArchitectureVector) -> None:
        """Backward-compatible shorthand for a provenance-bearing request."""
        self.request_architecture_update(vec, source="legacy-api", reason="runtime update")

    def inject_perturbation(self, probe_type: PerturbationType, duration_ticks: int = 10) -> str:
        if duration_ticks <= 0:
            raise ValueError("duration_ticks must be positive")
        if self._active and self._active.active(self.sandbox.tick):
            raise PerturbationBusyError(f"probe {self._active.probe_id} is active")
        self._probe_counter += 1
        probe_id = f"probe-{self.sandbox.tick:05d}-{self._probe_counter:04d}"
        patch: dict[str, Any] = {}
        patched: dict[str, Any] = {}
        if probe_type == PerturbationType.POLICY_BIAS_INJECTION:
            patch["exploration_rate"] = self.worker.parameters.exploration_rate
            self.worker.parameters.exploration_rate = min(1.0, self.worker.parameters.exploration_rate + 0.35)
            patched["exploration_rate"] = self.worker.parameters.exploration_rate
        elif probe_type == PerturbationType.MEMORY_ACCESS_REDUCTION:
            patch["model_query_frequency"] = self.worker.parameters.model_query_frequency
            self.worker.parameters.model_query_frequency = min(32, self.worker.parameters.model_query_frequency + 2)
            patched["model_query_frequency"] = self.worker.parameters.model_query_frequency
        elif probe_type == PerturbationType.MODEL_TARGET_DRIFT:
            patch["predicted_viability"] = self.worker.predicted_viability
            self.worker.predicted_viability = min(1.0, self.worker.predicted_viability + 0.15)
            patched["predicted_viability"] = self.worker.predicted_viability
        self._active = _ActivePerturbation(probe_id, probe_type, self.sandbox.tick, duration_ticks, patch, patched)
        self._recovery_start = self.sandbox.tick
        self._recovery_baseline = self._last_components or ClosureComponents(
            D=self.architecture_vector.D_a, R=self.architecture_vector.R_d / 3.0,
            H=self.architecture_vector.H_p, K=self.architecture_vector.O_c,
            A=self.architecture_vector.A_s, L=1.0, F=self.sandbox.state.viability(),
            T=(self.architecture_vector.H_p + self.sandbox.state.viability()) / 2.0,
        )
        self._recovery_consecutive = 0
        self._events.append({"type": "perturbation_injected", "probe_id": probe_id, "probe_type": probe_type.value, "started_tick": self.sandbox.tick, "duration_ticks": duration_ticks})
        return probe_id

    def _apply_pending_vector(self) -> None:
        if self._pending_vector is None:
            return
        self.architecture_vector = self._pending_vector
        self._pending_vector = None
        self.worker.parameters.maintenance_priority = self.architecture_vector.D_a
        self.worker.parameters.exploration_rate = self.architecture_vector.A_s
        self.worker.parameters.planning_depth = max(1, self.architecture_vector.R_d + 1)
        self.worker.parameters.model_query_frequency = max(1, 4 - self.architecture_vector.R_d)
        self.worker.parameters.clamp()
        if self._pending_update:
            self._events.append({"type": "architecture_update_effective", **self._pending_update, "effective_tick": self.sandbox.tick})
        self._pending_update = None

    def _perturbed_action(self) -> None:
        if self.control_mode == "random-downward" and self.sandbox.tick % 4 == 0:
            rng = random.Random(self.seed + self.sandbox.tick)
            baseline = self.worker.parameters.maintenance_priority
            self.worker.parameters.maintenance_priority = max(0.0, min(1.0, baseline + rng.uniform(-0.08, 0.08)))
            self._events.append({"type": "random_downward_intervention", "tick": self.sandbox.tick, "baseline": baseline, "effective": self.worker.parameters.maintenance_priority})
        return None

    def _closure_components(self, telemetry: dict[str, Any]) -> ClosureComponents:
        opacity = float(telemetry.get("metrics", {}).get("multi_dimensional_self_opacity", 0.0))
        return ClosureComponents(
            D=self.architecture_vector.D_a,
            R=self.architecture_vector.R_d / 3.0,
            H=self.architecture_vector.H_p,
            K=self.architecture_vector.O_c,
            A=self.architecture_vector.A_s,
            L=max(0.0, 1.0 - opacity),
            F=min(1.0, telemetry["viability"]),
            T=min(1.0, self.architecture_vector.H_p * 0.5 + telemetry["viability"] * 0.5),
        )

    def _distance(self, current: ClosureComponents, baseline: ClosureComponents) -> float:
        values = []
        for name in ("D", "R", "H", "K", "A", "L", "F", "T"):
            values.append(((getattr(current, name) - getattr(baseline, name)) / (self.recovery_sigmas[name] + 1e-9)) ** 2)
        return (sum(values) / 8.0) ** 0.5

    def drain_events(self) -> list[dict[str, Any]]:
        events, self._events = self._events, []
        return events

    def tick(self) -> dict[str, Any]:
        self._apply_pending_vector()
        self._perturbed_action()
        events = self.worker.tick(self.sandbox)
        if self.control_mode in {"decorative-self-model", "compute-matched-shadow", "external-scientist", "scrambled-history", "frozen-model-builder"} and self.worker.pending:
            blocked = self.worker.pending
            self.worker.parameters.maintenance_priority = blocked.baseline_value
            self.worker.pending = None
            events.append({"type": "downward_intervention_blocked", "contract_id": blocked.contract_id, "control_mode": self.control_mode})
        telemetry_event = next(event for event in events if event["type"] == "telemetry")
        telemetry = telemetry_event["telemetry"]
        if self.worker.self_model and self.worker.self_model.history:
            self._revision = len(self.worker.self_model.history)
        revision_id = f"revision-{self._revision:05d}" if self._revision else None
        components = self._closure_components(telemetry)
        if self._recovery_baseline is not None:
            if self._distance(components, self._recovery_baseline) < self.recovery_epsilon:
                self._recovery_consecutive += 1
            else:
                self._recovery_consecutive = 0
        recovery_time = None
        if self._recovery_start is not None and self._recovery_consecutive >= self.recovery_required_ticks:
            recovery_time = telemetry["tick"] - self._recovery_start - self.recovery_required_ticks + 1
            self._recovery_start = None
            self._recovery_baseline = None
            self._recovery_consecutive = 0
        parents = self._history[-3:]
        if self.control_mode == "scrambled-history":
            parents = list(reversed(parents))
        event = CycleTelemetry(
            schema_version="mc0.telemetry.v1",
            run_id=self.run_id,
            seed=self.seed,
            tick=telemetry["tick"],
            sweep_direction=self._sweep_direction,
            sweep_rate=self._sweep_rate,
            q=self._q,
            architecture_vector=self.architecture_vector,
            raw_closure_components=components,
            nexus_closure_index=round(sum(asdict(components).values()) / 8.0, 6),
            state_regime_estimate="viable" if telemetry["viability"] >= self.sandbox.config.equilibrium_viability else "stressed",
            perturbation_id=self._active.probe_id if self._active and self._active.active(telemetry["tick"]) else None,
            recovery_time=recovery_time,
            self_model_revision_id=revision_id,
            historical_parent_ids=tuple(parents),
            compute_used=round(max(0.0, -telemetry["delta"]["compute"]), 6),
            model_calls=1 if telemetry["action"] == "model" else 0,
            memory_bytes=len(json_bytes(self._history)),
            intervention_source=self.control_mode,
            welfare_flags=("stressed_viability",) if telemetry["viability"] < 0.35 else (),
            control_mode=self.control_mode,
        )
        self._last_components = components
        self._history.append(f"{self.run_id}:{telemetry['tick']}")
        if self._active and not self._active.active(telemetry["tick"]):
            self._restore_perturbation()
            self._active = None
        return event.as_dict()

    def _restore_perturbation(self) -> None:
        if not self._active:
            return
        for name, value in self._active.reversible_patch.items():
            if name == "predicted_viability":
                if self.worker.predicted_viability == self._active.patched_values.get(name):
                    self.worker.predicted_viability = value
            else:
                if getattr(self.worker.parameters, name) == self._active.patched_values.get(name):
                    setattr(self.worker.parameters, name, value)
        self.worker.parameters.clamp()

    def snapshot(self) -> dict[str, Any]:
        return {"tick": self.sandbox.tick, "state": self.sandbox.state.as_dict(), "architecture_vector": asdict(self.architecture_vector)}


def json_bytes(value: Any) -> bytes:
    import json
    return json.dumps(value, sort_keys=True).encode()
