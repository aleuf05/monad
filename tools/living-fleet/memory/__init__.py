"""Effort B: Captain Memory & Identity. See tools/living-fleet/memory/service.py
for the public MemoryService API and the plan at the top of this package's
sibling docs for the full design rationale.
"""

from .models import ContextBundle, RecordResult
from .service import MemoryService

__all__ = ["MemoryService", "ContextBundle", "RecordResult"]
