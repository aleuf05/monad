"""Append-only causal event log.

Every significant state transition is recorded as an Event with an explicit
`caused_by` list of prior event ids. The diagnostic-card lineage shown in the
viewer is built exclusively by traversing these records -- nothing is
generated from current state alone, and nothing is inferred by an LLM.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict


@dataclass
class Event:
    event_id: str
    tick: int
    event_type: str
    cell: list[int] | None
    inputs: dict
    caused_by: list[str] = field(default_factory=list)
    result: dict = field(default_factory=dict)
    authored_override: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class EventLog:
    def __init__(self):
        self._events: list[Event] = []
        self._by_id: dict[str, Event] = {}
        self._counter = 0

    def new_id(self, tick: int, cell: tuple[int, int] | None, kind: str) -> str:
        self._counter += 1
        if cell is not None:
            return f"evt_{kind}_{tick:06d}_{cell[0]:02d}{cell[1]:02d}_{self._counter}"
        return f"evt_{kind}_{tick:06d}_{self._counter}"

    def record(
        self,
        tick: int,
        event_type: str,
        cell: tuple[int, int] | None,
        inputs: dict,
        caused_by: list[str] | None = None,
        result: dict | None = None,
        authored_override: bool = False,
    ) -> Event:
        eid = self.new_id(tick, cell, event_type)
        evt = Event(
            event_id=eid,
            tick=tick,
            event_type=event_type,
            cell=list(cell) if cell is not None else None,
            inputs=inputs,
            caused_by=list(caused_by or []),
            result=result or {},
            authored_override=authored_override,
        )
        self._events.append(evt)
        self._by_id[eid] = evt
        return evt

    def get(self, event_id: str) -> Event | None:
        return self._by_id.get(event_id)

    def all(self) -> list[Event]:
        return list(self._events)

    def __len__(self) -> int:
        return len(self._events)

    def lineage(self, event_id: str, _seen: set[str] | None = None) -> list[Event]:
        """All ancestor events of `event_id` (inclusive), in causal order
        (oldest first), traversed strictly via stored `caused_by` links.
        Cycle-safe: a `_seen` guard makes this well-defined even if bad data
        somehow contained a cycle, though `is_acyclic` should always hold.
        """
        seen = _seen if _seen is not None else set()
        evt = self.get(event_id)
        if evt is None or event_id in seen:
            return []
        seen.add(event_id)
        out: list[Event] = []
        for parent_id in evt.caused_by:
            out.extend(self.lineage(parent_id, seen))
        out.append(evt)
        return out

    def is_acyclic(self) -> bool:
        for evt in self._events:
            visited: set[str] = set()
            stack = list(evt.caused_by)
            while stack:
                pid = stack.pop()
                if pid == evt.event_id:
                    return False
                if pid in visited:
                    continue
                visited.add(pid)
                parent = self.get(pid)
                if parent:
                    stack.extend(parent.caused_by)
        return True

    def to_jsonl(self) -> str:
        return "\n".join(json.dumps(e.to_dict(), sort_keys=True) for e in self._events)

    @classmethod
    def from_jsonl(cls, text: str) -> "EventLog":
        log = cls()
        max_counter = 0
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            evt = Event(
                event_id=d["event_id"],
                tick=d["tick"],
                event_type=d["event_type"],
                cell=d["cell"],
                inputs=d["inputs"],
                caused_by=d["caused_by"],
                result=d["result"],
                authored_override=d["authored_override"],
            )
            log._events.append(evt)
            log._by_id[evt.event_id] = evt
            max_counter += 1
        log._counter = max_counter
        return log
