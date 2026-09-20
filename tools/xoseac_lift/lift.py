"""Smallest executable lift over a represented XOSEAC instance.

The external boundary is a strict JSON-shaped mapping with exactly six
component keys: x, o, s, e, a, c.  Internally the six components are typed
immutable tuples/records.  The implementation deliberately performs no
search or optimization; it validates one requested local mutation, applies
it, validates the complete successor, and records every causal step.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Generic, Literal, Mapping, TypeVar


class XOSEACError(ValueError):
    """A boundary, typing, mutation, or successor well-formedness failure."""


Json = dict[str, Any]
T = TypeVar("T")


@dataclass(frozen=True)
class X:
    """Object identity/type boundary for the represented instance."""

    kind: str
    identifier: str


@dataclass(frozen=True)
class O:
    """Object-level observations available to the instance."""

    labels: tuple[str, ...]


@dataclass(frozen=True)
class S:
    """Finite state vocabulary used by the instance."""

    states: tuple[str, ...]


@dataclass(frozen=True)
class E:
    """Directed typed successor relation over S."""

    edges: tuple[tuple[str, str, str], ...]


@dataclass(frozen=True)
class A:
    """Allowed action names; this minimal lift does not execute actions."""

    actions: tuple[str, ...]


@dataclass(frozen=True)
class C:
    """Cross-component constraints for a represented instance."""

    initial: str
    terminal: tuple[str, ...]


@dataclass(frozen=True)
class XOSEACInstance:
    """The internal, validated representation of an Inst(M) object."""

    x: X
    o: O
    s: S
    e: E
    a: A
    c: C

    def to_dict(self) -> Json:
        return {
            "x": {"kind": self.x.kind, "identifier": self.x.identifier},
            "o": {"labels": list(self.o.labels)},
            "s": {"states": list(self.s.states)},
            "e": {"edges": [list(edge) for edge in self.e.edges]},
            "a": {"actions": list(self.a.actions)},
            "c": {"initial": self.c.initial, "terminal": list(self.c.terminal)},
        }


@dataclass(frozen=True)
class Lifted(Generic[T]):
    """A typed component after crossing the M -> M^up boundary."""

    value: T
    source_component: Literal["x", "o", "s", "e", "a", "c"]


XUp = Lifted[X]
OUp = Lifted[O]
SUp = Lifted[S]
EUp = Lifted[E]
AUp = Lifted[A]
CUp = Lifted[C]


@dataclass(frozen=True)
class LiftedInstance:
    """The six lifted components consumed by the successor constructor."""

    x: XUp
    o: OUp
    s: SUp
    e: EUp
    a: AUp
    c: CUp

    def instance(self) -> XOSEACInstance:
        return XOSEACInstance(
            x=self.x.value,
            o=self.o.value,
            s=self.s.value,
            e=self.e.value,
            a=self.a.value,
            c=self.c.value,
        )


@dataclass(frozen=True)
class AddState:
    state: str


@dataclass(frozen=True)
class AddEdge:
    source: str
    target: str
    label: str


Mutation = AddState | AddEdge


@dataclass(frozen=True)
class ProvenanceEvent:
    sequence: int
    phase: str
    claim: str
    data: Mapping[str, Any]


@dataclass(frozen=True)
class LiftResult:
    accepted: bool
    before: XOSEACInstance
    successor: XOSEACInstance | None
    provenance: tuple[ProvenanceEvent, ...]
    error: str | None = None


def _require_string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value:
        raise XOSEACError(f"{path} must be a non-empty string")
    return value


def _require_string_list(value: Any, path: str) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise XOSEACError(f"{path} must be a list of non-empty strings")
    if len(set(value)) != len(value):
        raise XOSEACError(f"{path} must not contain duplicates")
    return tuple(value)


def instance_from_dict(raw: Mapping[str, Any]) -> XOSEACInstance:
    """Cross the representation boundary and enforce WellFormedInst."""

    if not isinstance(raw, Mapping):
        raise XOSEACError("Inst(M) must be a mapping")
    required = {"x", "o", "s", "e", "a", "c"}
    if set(raw) != required:
        raise XOSEACError(f"Inst(M) keys must be exactly {sorted(required)}")
    for key in required:
        if not isinstance(raw[key], Mapping):
            raise XOSEACError(f"Inst(M).{key} must be a mapping")

    xraw, oraw, sraw, eraw, araw, craw = (raw[k] for k in ("x", "o", "s", "e", "a", "c"))
    x = X(_require_string(xraw.get("kind"), "x.kind"), _require_string(xraw.get("identifier"), "x.identifier"))
    o = O(_require_string_list(oraw.get("labels"), "o.labels"))
    states = _require_string_list(sraw.get("states"), "s.states")
    if not states:
        raise XOSEACError("s.states must contain at least one state")

    edges_raw = eraw.get("edges")
    if not isinstance(edges_raw, list):
        raise XOSEACError("e.edges must be a list")
    edges: list[tuple[str, str, str]] = []
    for index, edge in enumerate(edges_raw):
        if not isinstance(edge, list) or len(edge) != 3:
            raise XOSEACError(f"e.edges[{index}] must be [source, target, label]")
        edges.append(tuple(_require_string(part, f"e.edges[{index}]") for part in edge))  # type: ignore[arg-type]
    e = E(tuple(edges))
    a = A(_require_string_list(araw.get("actions"), "a.actions"))
    terminal = _require_string_list(craw.get("terminal"), "c.terminal")
    c = C(_require_string(craw.get("initial"), "c.initial"), terminal)
    instance = XOSEACInstance(x, o, S(states), e, a, c)
    validate_instance(instance)
    return instance


def validate_instance(instance: XOSEACInstance) -> None:
    """WellFormedInst: all local types and cross-links must agree."""

    states = set(instance.s.states)
    if instance.c.initial not in states:
        raise XOSEACError("c.initial must name a state in s.states")
    if not set(instance.c.terminal) <= states:
        raise XOSEACError("c.terminal must name only states in s.states")
    seen_edges: set[tuple[str, str, str]] = set()
    for edge in instance.e.edges:
        if edge in seen_edges:
            raise XOSEACError("e.edges must not contain duplicate edges")
        seen_edges.add(edge)
        source, target, _label = edge
        if source not in states or target not in states:
            raise XOSEACError("every e.edge endpoint must name a state in s.states")


def _canonical(instance: XOSEACInstance) -> str:
    return json.dumps(instance.to_dict(), sort_keys=True, separators=(",", ":"))


def _digest(instance: XOSEACInstance) -> str:
    return sha256(_canonical(instance).encode("utf-8")).hexdigest()


def _event(events: list[ProvenanceEvent], phase: str, claim: str, **data: Any) -> None:
    events.append(ProvenanceEvent(len(events), phase, claim, data))


def apply_lift(instance: XOSEACInstance, mutation: Mutation) -> LiftResult:
    """Apply one typed legal mutation or return a fully traced rejection."""

    events: list[ProvenanceEvent] = []
    try:
        validate_instance(instance)
        before = _digest(instance)
        _event(events, "boundary", "accepted validated Inst(M)", before_digest=before)
        _event(events, "request", "received typed mutation", mutation=mutation.__class__.__name__, payload=mutation.__dict__)

        states = list(instance.s.states)
        edges = list(instance.e.edges)
        if isinstance(mutation, AddState):
            if not mutation.state:
                raise XOSEACError("S mutation requires a non-empty state")
            if mutation.state in states:
                raise XOSEACError(f"S mutation would duplicate state {mutation.state!r}")
            states.append(mutation.state)
            _event(events, "mutation", "added one state to S", state=mutation.state)
        elif isinstance(mutation, AddEdge):
            candidate = (mutation.source, mutation.target, mutation.label)
            if not all(candidate):
                raise XOSEACError("E mutation requires non-empty source, target, and label")
            if mutation.source not in states or mutation.target not in states:
                raise XOSEACError("E mutation would reference a state absent from S")
            if candidate in edges:
                raise XOSEACError("E mutation would duplicate an existing edge")
            edges.append(candidate)
            _event(events, "mutation", "added one edge to E", edge=list(candidate))
        else:
            raise XOSEACError(f"unsupported mutation type {type(mutation).__name__}")

        lifted = LiftedInstance(
            XUp(instance.x, "x"), OUp(instance.o, "o"), SUp(S(tuple(states)), "s"),
            EUp(E(tuple(edges)), "e"), AUp(instance.a, "a"), CUp(instance.c, "c"),
        )
        successor = lifted.instance()
        validate_instance(successor)
        after = _digest(successor)
        _event(events, "successor", "WellFormedInst(M') accepted", after_digest=after)
        _event(events, "causal", "M' differs from M only by the requested typed component", changed_component="s" if isinstance(mutation, AddState) else "e")
        return LiftResult(True, instance, successor, tuple(events))
    except XOSEACError as error:
        _event(events, "rejection", "WellFormedInst(M') rejected", reason=str(error))
        return LiftResult(False, instance, None, tuple(events), str(error))
