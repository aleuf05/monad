"""IntentForge v0.0 -- Design Intent Contract.

Deliberately narrow: this v0.0 contract only models the one part family
built so far (a flat plate with circular holes and one edge notch --
enough for the packet's own worked example, a fan-mount bracket). It is
not the full contract shape from the concept packet (5.1-5.9); it is the
smallest honest slice of it that a real generator behind it can back up
with actual geometry today.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Hole:
    cx: float
    cy: float
    diameter: float
    purpose: str  # why this hole exists -- the "intent trace" the packet requires


@dataclass
class EdgeNotch:
    """A rectangular cut into one edge of the outer boundary --
    v0.0's only supported keep-out shape (matches the packet's cable-
    clearance example, which sits at a panel edge)."""

    edge: str  # "north" | "south" | "east" | "west"
    center_offset: float  # distance along the edge from its midpoint
    width: float
    depth: float
    purpose: str


@dataclass
class Envelope:
    width: float
    height: float
    thickness: float


@dataclass
class ValidationStatus:
    """Mirrors the concept packet's truthfulness states directly in
    code, not just prose -- a generator run can only set the fields it
    actually earned. Defaults are all False; nothing here is assumed
    true by construction."""

    geometry_proposed: bool = False
    constraints_checked: bool = False
    printability_estimated: bool = False
    simulation_completed: bool = False
    prototype_manufactured: bool = False
    prototype_tested: bool = False
    externally_reviewed: bool = False
    validated_for_use: bool = False

    def as_dict(self) -> dict:
        return {
            "geometry_proposed": self.geometry_proposed,
            "constraints_checked": self.constraints_checked,
            "printability_estimated": self.printability_estimated,
            "simulation_completed": self.simulation_completed,
            "prototype_manufactured": self.prototype_manufactured,
            "prototype_tested": self.prototype_tested,
            "externally_reviewed": self.externally_reviewed,
            "validated_for_use": self.validated_for_use,
        }


@dataclass
class FanMountBracketIntent:
    """The concrete Design Intent Contract for v0.0's one supported
    demo: a flat bracket mounting a fan to two existing holes, with a
    cable keep-out and a minimum printable wall thickness."""

    purpose: str
    envelope: Envelope
    existing_holes: list[Hole]
    fan_center: tuple[float, float]
    fan_bolt_spacing: float
    fan_bolt_diameter: float
    fan_airflow_diameter: float
    cable_notch: EdgeNotch | None
    min_wall_thickness: float
    acceptance_criteria: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
