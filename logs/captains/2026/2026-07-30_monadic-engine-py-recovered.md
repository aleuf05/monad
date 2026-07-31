# monadic_engine.py — Recovered Source (partial)

Date recovered: 2026-07-30
Source: Lt. cgl, pasted directly into chat from a file browser view (not
via scp as originally planned — appears to be a screenshot/copy of a code
viewer showing `monadic_engine.py`, not the binary file itself).
Epistemic label: **Direct recollection** — verbatim paste of visible
text, confirmed **partial**: cuts off mid-method at line 67 inside
`RunRecord.to_json()`. Not yet verified against a running/importable copy
of the actual file.

This is different in kind from the earlier ChatGPT transcript pastes —
it's real, syntactically checkable Python (dataclasses, hashlib, uuid),
not chat prose. Worth verifying by running/reading the rest, not just
archiving as historical color.

---

## Raw content, as pasted (lines 1-67 of an unknown total)

```python
#!/usr/bin/env python3
"""
monadic_engine.py

A minimal bounded monadic research engine.

Operational guarantees:
- Fixed identity keel
- Bounded recursive branching
- Complete provenance
- Deterministic replay from seed + inputs
- External test hooks
- Absolute shutdown switch
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from hashlib import sha256
from pathlib import Path
from typing import Callable, Generic, Iterable, TypeVar
import json
import random
import time
import uuid

T = TypeVar("T")


class ShutdownRequested(RuntimeError):
    """Raised when the hard shutdown switch is active."""


@dataclass(frozen=True)
class Transformation:
    name: str
    description: str


@dataclass
class Node(Generic[T]):
    node_id: str
    identity: str
    state: T
    depth: int
    parent_id: str | None
    transformation: Transformation | None
    state_hash: str
    created_at: float
    children: list[str] = field(default_factory=list)


@dataclass
class RunRecord(Generic[T]):
    run_id: str
    identity: str
    seed: int
    max_depth: int
    max_branches_per_node: int
    root_id: str
    nodes: dict[str, Node[T]]
    stopped: bool = False

    def to_json(self) -> str:
        return json.dumps(
            {
                "run_id": self.run_id,
```

## What this looks like, honestly

A bounded tree-search/exploration engine: nodes carry state + a content
hash + provenance (parent, transformation, depth), runs are seeded and
deterministic, there's an explicit hard-stop (`ShutdownRequested`) and
a `max_depth`/`max_branches_per_node` bound. Structurally sound Python so
far — real type hints, real dataclasses, nothing fabricated-looking in
what's visible. Whether it actually runs and does what the docstring
claims can't be confirmed from 67 lines; needs the rest of the file.
