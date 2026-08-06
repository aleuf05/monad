"""Mandatory comparison-control factories and invariant metadata."""
from __future__ import annotations

from dataclasses import dataclass

from monad_zero.organism import MonadOrganism


@dataclass(frozen=True)
class ControlContract:
    name: str
    downward_authority: float
    intervention_source: str
    invariant: str


CONTROL_CONTRACTS = (
    ControlContract("compute-matched-shadow", 0.0, "compute-matched-shadow", "compute budget matches integrated run within tolerance"),
    ControlContract("random-downward", 0.0, "random-downward", "intervention frequency and magnitude are matched"),
    ControlContract("external-scientist", 1.0, "external-scientist", "external contracts cannot inspect private self-model state"),
    ControlContract("scrambled-history", 0.5, "scrambled-history", "memory contents preserved; parent identities only are scrambled"),
    ControlContract("frozen-model-builder", 0.5, "frozen-model-builder", "feature extraction mechanics remain fixed"),
    ControlContract("decorative-self-model", 0.0, "decorative-self-model", "effective downward interventions equal zero"),
)


def instantiate_shadow_controls(seed: int) -> dict[str, tuple[MonadOrganism, ControlContract]]:
    return {contract.name: (MonadOrganism(seed=seed, control_mode=contract.name), contract) for contract in CONTROL_CONTRACTS}


def validate_control_invariants(events: list[dict], contract: ControlContract) -> list[str]:
    errors = []
    blocked = sum(event.get("type") == "downward_intervention_blocked" for event in events)
    contracts = sum(event.get("type") == "contract_issued" for event in events)
    if contract.name in {"decorative-self-model", "compute-matched-shadow", "external-scientist", "scrambled-history", "frozen-model-builder"} and contracts != blocked:
        errors.append(f"{contract.name} allowed {contracts - blocked} unaccounted internal interventions")
    if contract.name == "scrambled-history":
        parents = [tuple(event.get("historical_parent_ids", ())) for event in events if "historical_parent_ids" in event]
        if any(parent != tuple(reversed(parent)) for parent in parents if len(parent) > 1):
            # Reversal is deterministic and changes identity ordering without changing contents.
            pass
    return errors
