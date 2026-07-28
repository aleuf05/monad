"""Persistent conservative usage ceiling for Live Captain Version 1."""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any


MAX_DOLLARS = 2.00
MAX_REQUESTS = 25
MAX_INPUT_TOKENS = 8_000
MAX_OUTPUT_TOKENS = 512

# Deliberately conservative local accounting rates, not a pricing claim.
# They are higher than this prototype expects to pay and create headroom for
# provider pricing changes and token-estimation error.
INPUT_DOLLARS_PER_MILLION = 1.00
OUTPUT_DOLLARS_PER_MILLION = 5.00


class BudgetExceeded(RuntimeError):
    pass


class UsageBudget:
    def __init__(self, path: Path):
        self.path = path.resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.state = self._load()

    def estimate_input_tokens(self, text: str) -> int:
        # Three characters/token is intentionally conservative for English.
        return max(1, math.ceil(len(text) / 3))

    def reserve(self, input_text: str) -> dict[str, Any]:
        estimated_input = self.estimate_input_tokens(input_text)
        if estimated_input > MAX_INPUT_TOKENS:
            raise BudgetExceeded(
                f"context estimate {estimated_input} exceeds the {MAX_INPUT_TOKENS}-token ceiling"
            )
        if self.state["request_count"] >= MAX_REQUESTS:
            raise BudgetExceeded(f"request ceiling reached ({MAX_REQUESTS})")
        estimated_cost = (
            estimated_input * INPUT_DOLLARS_PER_MILLION
            + MAX_OUTPUT_TOKENS * OUTPUT_DOLLARS_PER_MILLION
        ) / 1_000_000
        if self.state["reserved_dollars"] + estimated_cost > MAX_DOLLARS:
            raise BudgetExceeded("local $2.00 prototype ceiling would be exceeded")
        self.state["request_count"] += 1
        self.state["reserved_dollars"] += estimated_cost
        self.state["estimated_input_tokens"] += estimated_input
        self.state["reserved_output_tokens"] += MAX_OUTPUT_TOKENS
        self._write()
        return {
            "estimated_input_tokens": estimated_input,
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "reserved_cost": estimated_cost,
        }

    def record_usage(
        self,
        *,
        input_tokens: int | None,
        output_tokens: int | None,
    ) -> None:
        if input_tokens is not None:
            self.state["reported_input_tokens"] += input_tokens
        if output_tokens is not None:
            self.state["reported_output_tokens"] += output_tokens
        self._write()

    def status(self) -> dict[str, Any]:
        return {
            **self.state,
            "max_dollars": MAX_DOLLARS,
            "max_requests": MAX_REQUESTS,
            "max_input_tokens_per_request": MAX_INPUT_TOKENS,
            "max_output_tokens_per_request": MAX_OUTPUT_TOKENS,
            "remaining_requests": max(0, MAX_REQUESTS - self.state["request_count"]),
        }

    def _load(self) -> dict[str, Any]:
        defaults = {
            "version": 1,
            "request_count": 0,
            "reserved_dollars": 0.0,
            "estimated_input_tokens": 0,
            "reserved_output_tokens": 0,
            "reported_input_tokens": 0,
            "reported_output_tokens": 0,
        }
        if not self.path.exists():
            self.state = defaults
            self._write()
            return defaults
        value = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("usage state is malformed")
        for key, default in defaults.items():
            value.setdefault(key, default)
        return value

    def _write(self) -> None:
        temporary = self.path.with_suffix(".json.tmp")
        descriptor = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
            0o600,
        )
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(self.state, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, self.path)
        os.chmod(self.path, 0o600)
