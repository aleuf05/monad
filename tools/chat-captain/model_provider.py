"""Provider-neutral inference contract for Chat Captain.

Copied from tools/living-captain/model_provider.py -- the contract is
schema-agnostic and has no coupling to conversation storage, so it is
reused verbatim rather than re-derived.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Message:
    role: str
    content: str


@dataclass(frozen=True)
class GenerationLimits:
    max_output_tokens: int
    temperature: float = 0.4


@dataclass(frozen=True)
class ProviderResponse:
    text: str
    provider: str
    model: str
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    finish_reason: str | None


class ProviderError(RuntimeError):
    """Safe, operator-facing provider failure."""


class ModelProvider(Protocol):
    name: str
    model: str

    def generate(
        self,
        system_prompt: str,
        messages: list[Message],
        limits: GenerationLimits,
    ) -> ProviderResponse:
        ...
