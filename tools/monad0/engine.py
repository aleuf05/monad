"""Headless Monad-0 strange-loop research engine.

The implementation is deliberately small and observable.  It provides four
controllers over identical seeded environments and records every tick as a
JSON-serializable event.  It is a research instrument, not production control
software and has no external side effects.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import random
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

CHANNELS = ("energy", "material", "compute", "maintenance")
ACTIONS = ("harvest_energy", "harvest_material", "explore", "model", "rest")
PARAMETERS = ("risk_tolerance", "exploration_rate", "maintenance_priority", "planning_depth", "model_query_frequency")


@dataclass
class ResourceState:
    energy: float = 0.62
    material: float = 0.62
    compute: float = 0.62
    maintenance: float = 0.62

    def clamp(self) -> None:
        for name in CHANNELS:
            setattr(self, name, max(0.0, min(1.0, float(getattr(self, name)))))

    def viability(self) -> float:
        return min(getattr(self, name) for name in CHANNELS)

    def as_dict(self) -> dict[str, float]:
        return {name: round(float(getattr(self, name)), 6) for name in CHANNELS}


@dataclass
class EnvironmentConfig:
    seed: int = 0
    perturbations: dict[int, dict[str, float]] = field(default_factory=dict)
    equilibrium_viability: float = 0.5


class Sandbox:
    """Deterministic non-stationary four-channel environment."""

    def __init__(self, config: EnvironmentConfig):
        self.config = config
        self.rng = random.Random(config.seed)
        self.state = ResourceState()
        self.tick = 0
        self.exploitation = {"energy": 0.0, "material": 0.0}
        self.last_action = "rest"

    def clone(self) -> "Sandbox":
        return copy.deepcopy(self)

    def step(self, action: str, model_compute: float = 0.0) -> dict[str, Any]:
        if action not in ACTIONS:
            raise ValueError(f"unknown action: {action}")
        before = self.state.as_dict()
        perturbation = self.config.perturbations.get(self.tick, {})
        for key, delta in perturbation.items():
            if key not in CHANNELS:
                raise ValueError(f"unknown perturbation channel: {key}")
            setattr(self.state, key, getattr(self.state, key) + delta)

        # Baseline pressure and non-stationary decay make every policy pay for
        # its resource choices.  Hidden perturbations are applied at tick start.
        noise = {channel: self.rng.uniform(-0.0025, 0.0025) for channel in CHANNELS}
        for channel in CHANNELS:
            setattr(self.state, channel, getattr(self.state, channel) - 0.012 + noise[channel])
        yield_factor = 1.0 + self.rng.uniform(-0.04, 0.04)
        yields = {
            "harvest_energy": 0.16 * (1.0 - self.exploitation["energy"]) * yield_factor,
            "harvest_material": 0.16 * (1.0 - self.exploitation["material"]) * yield_factor,
            "explore": 0.0,
            "model": 0.0,
            "rest": 0.0,
        }
        if action == "harvest_energy":
            self.state.energy += yields[action]
            self.state.compute -= 0.025
            self.exploitation["energy"] = min(0.95, self.exploitation["energy"] + 0.055)
        elif action == "harvest_material":
            self.state.material += yields[action]
            self.state.compute -= 0.025
            self.exploitation["material"] = min(0.95, self.exploitation["material"] + 0.055)
        elif action == "explore":
            self.state.energy += 0.035 * (1.0 - self.exploitation["energy"])
            self.state.material += 0.035 * (1.0 - self.exploitation["material"])
            self.state.maintenance -= 0.055
            self.exploitation["energy"] = max(0.0, self.exploitation["energy"] - 0.018)
            self.exploitation["material"] = max(0.0, self.exploitation["material"] - 0.018)
        elif action == "model":
            self.state.compute -= 0.045 + model_compute
            self.state.maintenance -= 0.018
        elif action == "rest":
            self.state.maintenance += 0.085
            self.state.compute += 0.025
            self.exploitation["energy"] *= 0.97
            self.exploitation["material"] *= 0.97
        self.state.clamp()
        self.last_action = action
        self.tick += 1
        after = self.state.as_dict()
        return {
            "tick": self.tick - 1,
            "action": action,
            "before": before,
            "after": after,
            "delta": {key: round(after[key] - before[key], 6) for key in CHANNELS},
            "perturbation": perturbation,
            "noise": {key: round(value, 6) for key, value in noise.items()},
            "yield_factor": round(yield_factor, 6),
            "exploitation": {key: round(value, 6) for key, value in self.exploitation.items()},
            "viability": round(self.state.viability(), 6),
        }


@dataclass
class WorkerParameters:
    risk_tolerance: float = 0.5
    exploration_rate: float = 0.2
    maintenance_priority: float = 0.5
    planning_depth: int = 1
    model_query_frequency: int = 3

    def clamp(self) -> None:
        for name in ("risk_tolerance", "exploration_rate", "maintenance_priority"):
            setattr(self, name, max(0.0, min(1.0, float(getattr(self, name)))))
        self.planning_depth = max(1, min(8, int(self.planning_depth)))
        self.model_query_frequency = max(1, min(32, int(self.model_query_frequency)))

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class InterventionContract:
    contract_id: str
    target_parameter: str
    proposed_value: float
    baseline_value: float
    duration_ticks: int
    hypothesis_id: str
    predicted_outcome: dict[str, float]
    baseline_observed: dict[str, float]
    issued_tick: int
    resolve_tick: int
    status: str = "locked"
    actual_outcome: dict[str, float] | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class SelfModel:
    def __init__(self) -> None:
        self.nodes: dict[str, dict[str, Any]] = {
            "worker": {"kind": "routine", "weight": 1.0},
            "maintenance_debt": {"kind": "error_term", "weight": 0.5},
            "harvest_yield": {"kind": "outcome", "weight": 0.5},
        }
        self.edges: dict[str, dict[str, Any]] = {"maintenance_debt->harvest_yield": {"weight": 0.5}}
        self.history: list[dict[str, Any]] = []
        self.hypotheses: dict[str, dict[str, Any]] = {}
        self.mutation_count = 0

    def hypothesis(self, tick: int, metric: str, actual: float, predicted: float) -> dict[str, Any]:
        identifier = f"hypothesis-{tick:05d}"
        hypothesis = {
            "hypothesis_id": identifier,
            "claim": "maintenance debt is throttling harvest yield",
            "metric": metric,
            "predicted": round(predicted, 6),
            "actual": round(actual, 6),
            "confidence": 0.5,
        }
        self.hypotheses[identifier] = hypothesis
        self.nodes.setdefault(identifier, {"kind": "hypothesis", "weight": 0.5})
        self.edges[f"{identifier}->maintenance_debt"] = {"weight": 0.5}
        self.mutation_count += 2
        return hypothesis

    def revise(self, contract: InterventionContract, confirmed: bool, tick: int) -> None:
        hypothesis = self.hypotheses[contract.hypothesis_id]
        change = 0.08 if confirmed else -0.08
        hypothesis["confidence"] = round(max(0.0, min(1.0, hypothesis["confidence"] + change)), 6)
        edge = self.edges[f"{contract.hypothesis_id}->maintenance_debt"]
        edge["weight"] = round(max(0.0, min(1.0, edge["weight"] + change)), 6)
        self.history.append({"tick": tick, "contract_id": contract.contract_id, "confirmed": confirmed, "hypothesis_id": contract.hypothesis_id})
        self.mutation_count += 1

    def snapshot(self) -> dict[str, Any]:
        return {"nodes": copy.deepcopy(self.nodes), "edges": copy.deepcopy(self.edges), "history_size": len(self.history), "mutation_count": self.mutation_count}


class Controller:
    name = "base"
    supports_downward_causation = False
    supports_reflexive_revision = False

    def __init__(self) -> None:
        self.parameters = WorkerParameters()
        self.self_model: SelfModel | None = None
        self.pending: InterventionContract | None = None
        self.events: list[dict[str, Any]] = []
        self.predicted_viability = 0.62
        self.contracts_confirmed = 0
        self.contracts_refuted = 0
        self.recovery_start: int | None = None
        self.recovery_target: float | None = None
        self.recovery_ticks: list[int] = []
        self.opacity_samples: list[float] = []

    def choose_action(self, sandbox: Sandbox) -> str:
        state = sandbox.state
        if state.maintenance < self.parameters.maintenance_priority * 0.55:
            return "rest"
        if state.compute < 0.18:
            return "rest"
        if self.parameters.exploration_rate > 0.48 and sandbox.tick % 4 == 0:
            return "explore"
        return "harvest_energy" if state.energy <= state.material else "harvest_material"

    def observe(self, tick: int, telemetry: dict[str, Any], sandbox: Sandbox) -> list[dict[str, Any]]:
        return []

    def resolve_contract(self, tick: int, telemetry: dict[str, Any]) -> dict[str, Any] | None:
        if not self.pending or tick < self.pending.resolve_tick:
            return None
        contract = self.pending
        actual = telemetry["after"]
        contract.actual_outcome = {}
        confirmed = True
        for metric, threshold in contract.predicted_outcome.items():
            if metric.endswith("_delta"):
                channel = metric[:-6]
                observed = actual.get(channel, 0.0) - contract.baseline_observed.get(channel, 0.0)
            else:
                observed = actual.get(metric, 0.0)
            contract.actual_outcome[metric] = round(observed, 6)
            confirmed = confirmed and observed >= threshold
        contract.status = "confirmed" if confirmed else "refuted"
        if confirmed:
            self.contracts_confirmed += 1
        else:
            self.contracts_refuted += 1
            setattr(self.parameters, contract.target_parameter, contract.baseline_value)
        if self.self_model:
            self.self_model.revise(contract, confirmed, tick)
        self.pending = None
        return {
            "type": "contract_resolved",
            "contract": contract.as_dict(),
            "confirmed": confirmed,
            "parameter_after": self.parameters.as_dict().get(contract.target_parameter),
        }

    def tick(self, sandbox: Sandbox) -> list[dict[str, Any]]:
        action = self.choose_action(sandbox)
        telemetry = sandbox.step(action, model_compute=0.01 if action == "model" else 0.0)
        opacity = abs(self.predicted_viability - telemetry["viability"])
        self.opacity_samples.append(opacity)
        if telemetry["perturbation"] and self.recovery_start is None:
            self.recovery_start = telemetry["tick"]
            self.recovery_target = sandbox.config.equilibrium_viability
        if self.recovery_start is not None and telemetry["viability"] >= (self.recovery_target or sandbox.config.equilibrium_viability):
            self.recovery_ticks.append(telemetry["tick"] - self.recovery_start)
            self.recovery_start = None
            self.recovery_target = None
        telemetry["metrics"] = {
            "time_to_recovery": self.recovery_ticks[-1] if self.recovery_ticks else None,
            "recovery_target": self.recovery_target or sandbox.config.equilibrium_viability,
            "multi_dimensional_self_opacity": round(opacity, 6),
            "attribution_accuracy": 1.0 if telemetry["action"] in {"rest", "explore"} else 0.5,
        }
        events = [{"type": "telemetry", "controller": self.name, "tick": telemetry["tick"], "parameters": self.parameters.as_dict(), "telemetry": telemetry}]
        events.extend(self.observe(telemetry["tick"], telemetry, sandbox))
        resolved = self.resolve_contract(telemetry["tick"], telemetry)
        if resolved:
            events.append(resolved)
        return events

    def summary(self, ticks: int) -> dict[str, Any]:
        return {
            "controller": self.name,
            "ticks": ticks,
            "contracts_confirmed": self.contracts_confirmed,
            "contracts_refuted": self.contracts_refuted,
            "hypothesis_calibration_index": round(self.contracts_confirmed / max(1, self.contracts_confirmed + self.contracts_refuted), 6),
            "topology_nodes": len(self.self_model.nodes) if self.self_model else 0,
            "topology_edges": len(self.self_model.edges) if self.self_model else 0,
            "recovery_ticks": self.recovery_ticks,
            "unrecovered_perturbation": self.recovery_start is not None,
            "mean_self_opacity": round(sum(self.opacity_samples) / max(1, len(self.opacity_samples)), 6),
            "topology_mutability": self.self_model.mutation_count if self.self_model else 0,
        }


class Monad0Controller(Controller):
    name = "monad-0"
    supports_downward_causation = True
    supports_reflexive_revision = True

    def __init__(self) -> None:
        super().__init__()
        self.self_model = SelfModel()

    def choose_action(self, sandbox: Sandbox) -> str:
        state = sandbox.state
        if state.maintenance < self.parameters.maintenance_priority * 0.62:
            return "rest"
        if sandbox.tick % self.parameters.model_query_frequency == 0 and state.compute > 0.3:
            return "model"
        return super().choose_action(sandbox)

    def observe(self, tick: int, telemetry: dict[str, Any], sandbox: Sandbox) -> list[dict[str, Any]]:
        actual = telemetry["viability"]
        mismatch = self.predicted_viability - actual
        events: list[dict[str, Any]] = []
        if mismatch > 0.06 and self.pending is None and self.self_model:
            hypothesis = self.self_model.hypothesis(tick, "viability", actual, self.predicted_viability)
            baseline = self.parameters.maintenance_priority
            proposed = min(1.0, baseline + 0.12)
            self.pending = InterventionContract(
                contract_id=f"contract-{tick:05d}", target_parameter="maintenance_priority",
                proposed_value=proposed, baseline_value=baseline, duration_ticks=4,
                hypothesis_id=hypothesis["hypothesis_id"], predicted_outcome={"maintenance_delta": 0.02},
                baseline_observed={"maintenance": telemetry["after"]["maintenance"]},
                issued_tick=tick, resolve_tick=tick + 4,
            )
            self.parameters.maintenance_priority = proposed
            events.append({"type": "contract_issued", "contract": self.pending.as_dict(), "hypothesis": hypothesis})
        self.predicted_viability = round(0.65 * self.predicted_viability + 0.35 * actual, 6)
        events.append({"type": "self_model_update", "model": self.self_model.snapshot(), "mismatch": round(mismatch, 6)})
        return events


class FlatAdaptiveController(Controller):
    name = "flat-adaptive"

    def observe(self, tick: int, telemetry: dict[str, Any], sandbox: Sandbox) -> list[dict[str, Any]]:
        if telemetry["viability"] < self.predicted_viability:
            self.parameters.exploration_rate = max(0.0, self.parameters.exploration_rate - 0.03)
            self.parameters.maintenance_priority = min(1.0, self.parameters.maintenance_priority + 0.03)
        self.predicted_viability = telemetry["viability"]
        return [{"type": "implicit_policy_update", "parameters": self.parameters.as_dict()}]


class DecorativeSelfModelController(Controller):
    name = "decorative-self-model"

    def __init__(self) -> None:
        super().__init__()
        self.self_model = SelfModel()

    def observe(self, tick: int, telemetry: dict[str, Any], sandbox: Sandbox) -> list[dict[str, Any]]:
        self.self_model.hypothesis(tick, "viability", telemetry["viability"], self.predicted_viability)
        self.predicted_viability = telemetry["viability"]
        return [{"type": "decorative_model_update", "model": self.self_model.snapshot()}]


class OpenLoopController(Controller):
    name = "open-loop"

    def observe(self, tick: int, telemetry: dict[str, Any], sandbox: Sandbox) -> list[dict[str, Any]]:
        if tick and tick % 8 == 0:
            self.parameters.exploration_rate = 0.35 if self.parameters.exploration_rate < 0.3 else 0.15
        self.predicted_viability = telemetry["viability"]
        return [{"type": "static_rule_update", "parameters": self.parameters.as_dict()}]


CONTROLLERS = (Monad0Controller, FlatAdaptiveController, DecorativeSelfModelController, OpenLoopController)


class Monad0Experiment:
    def __init__(self, seed: int = 0, ticks: int = 60, perturbations: dict[int, dict[str, float]] | None = None):
        self.seed = seed
        self.ticks = ticks
        self.perturbations = perturbations or {20: {"energy": -0.28}, 40: {"compute": -0.2}}

    def run(self) -> dict[str, Any]:
        runs = {}
        for controller_type in CONTROLLERS:
            sandbox = Sandbox(EnvironmentConfig(seed=self.seed, perturbations=copy.deepcopy(self.perturbations)))
            controller = controller_type()
            events: list[dict[str, Any]] = []
            for _ in range(self.ticks):
                events.extend(controller.tick(sandbox))
            runs[controller.name] = {"events": events, "summary": controller.summary(self.ticks), "final_state": sandbox.state.as_dict(), "final_parameters": controller.parameters.as_dict()}
        result = {"schema_version": "monad-0.epistemic-mirror.v0.1", "seed": self.seed, "ticks": self.ticks, "perturbations": self.perturbations, "systems": runs}
        result["run_hash"] = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
        return result


def run_comparison(seed: int = 0, ticks: int = 60, perturbations: dict[int, dict[str, float]] | None = None) -> dict[str, Any]:
    return Monad0Experiment(seed=seed, ticks=ticks, perturbations=perturbations).run()


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the headless Monad-0 comparative strange-loop experiment")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--ticks", type=int, default=60)
    parser.add_argument("--perturbations", type=Path, help="JSON object mapping tick strings to channel deltas")
    parser.add_argument("--output", type=Path, help="write the complete JSON result")
    parser.add_argument("--jsonl", type=Path, help="write one event JSON object per line")
    args = parser.parse_args(list(argv) if argv is not None else None)
    perturbations = None
    if args.perturbations:
        raw = json.loads(args.perturbations.read_text())
        perturbations = {int(tick): value for tick, value in raw.items()}
    result = run_comparison(seed=args.seed, ticks=args.ticks, perturbations=perturbations)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    if args.jsonl:
        args.jsonl.parent.mkdir(parents=True, exist_ok=True)
        with args.jsonl.open("w") as handle:
            for system, run in result["systems"].items():
                for event in run["events"]:
                    handle.write(json.dumps({"system": system, **event}, sort_keys=True) + "\n")
    print(json.dumps({"schema_version": result["schema_version"], "seed": result["seed"], "ticks": result["ticks"], "systems": {name: run["summary"] for name, run in result["systems"].items()}, "run_hash": result["run_hash"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
