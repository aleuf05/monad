"""Lightweight daily turn-count ceiling.

Codex authenticates via saved ChatGPT auth -- there is no per-token API key
billed from this codebase's perspective (see codex_provider.py), so this
guards against runaway request loops rather than approximating dollar cost.
Durability idiom (temp-file + fsync + os.replace) copied from
tools/living-captain/usage_budget.py.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

MAX_DAILY_TURNS = int(os.environ.get("CHAT_CAPTAIN_MAX_DAILY_TURNS", "200"))
MAX_INPUT_CHARS = 40_000  # bounds the context sent to the provider each turn


class BudgetExceeded(RuntimeError):
    pass


class UsageBudget:
    def __init__(self, path: Path):
        self.path = path.resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.state = self._load()

    def reserve(self, input_text: str) -> None:
        if len(input_text) > MAX_INPUT_CHARS:
            raise BudgetExceeded(f"context is too large ({len(input_text)} chars)")
        today = time.strftime("%Y-%m-%d", time.gmtime())
        if self.state.get("day") != today:
            self.state = {
                "day": today,
                "turn_count": 0,
                "reported_input_tokens": 0,
                "reported_output_tokens": 0,
            }
        if self.state["turn_count"] >= MAX_DAILY_TURNS:
            raise BudgetExceeded(f"daily turn ceiling reached ({MAX_DAILY_TURNS})")
        self.state["turn_count"] += 1
        self._write()

    def record_usage(self, *, input_tokens: int | None, output_tokens: int | None) -> None:
        if input_tokens is not None:
            self.state["reported_input_tokens"] = self.state.get("reported_input_tokens", 0) + input_tokens
        if output_tokens is not None:
            self.state["reported_output_tokens"] = self.state.get("reported_output_tokens", 0) + output_tokens
        self._write()

    def status(self) -> dict[str, Any]:
        return {
            **self.state,
            "max_daily_turns": MAX_DAILY_TURNS,
            "remaining_turns": max(0, MAX_DAILY_TURNS - self.state.get("turn_count", 0)),
        }

    def _load(self) -> dict[str, Any]:
        defaults = {
            "day": time.strftime("%Y-%m-%d", time.gmtime()),
            "turn_count": 0,
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
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(self.state, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, self.path)
        os.chmod(self.path, 0o600)
