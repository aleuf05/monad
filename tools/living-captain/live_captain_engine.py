"""Single-owner conversation engine shared by terminal and web interfaces."""

from __future__ import annotations

import fcntl
import hmac
import os
import re
from pathlib import Path

from conversation import ConversationStore
from model_provider import GenerationLimits, Message, ModelProvider, ProviderResponse
from usage_budget import MAX_INPUT_TOKENS, MAX_OUTPUT_TOKENS, BudgetExceeded, UsageBudget


SECRET_PATTERN = re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b")


class OwnershipError(RuntimeError):
    pass


class SecretRejected(ValueError):
    pass


def bounded_context(
    system_prompt: str,
    messages: list[Message],
    budget: UsageBudget,
) -> list[Message]:
    selected: list[Message] = []
    remaining = MAX_INPUT_TOKENS - budget.estimate_input_tokens(system_prompt)
    if remaining <= 0:
        raise BudgetExceeded("local system prompt exceeds the input ceiling")
    for index, message in enumerate(reversed(messages)):
        cost = budget.estimate_input_tokens(message.content)
        if cost > remaining:
            if index == 0:
                raise BudgetExceeded("current message exceeds the available context ceiling")
            break
        selected.append(message)
        remaining -= cost
    selected.reverse()
    return selected


def contains_secret(text: str, api_key: str) -> bool:
    if SECRET_PATTERN.search(text):
        return True
    if not api_key or len(text) < len(api_key) or api_key not in text:
        return False
    start = text.find(api_key)
    return hmac.compare_digest(api_key, text[start : start + len(api_key)])


class CaptainEngine:
    def __init__(
        self,
        *,
        provider: ModelProvider,
        store: ConversationStore,
        budget: UsageBudget,
        system_prompt: str,
        api_key_for_redaction: str = "",
        acquire_owner_lock: bool = True,
    ):
        self.provider = provider
        self.store = store
        self.budget = budget
        self.system_prompt = system_prompt
        self.api_key_for_redaction = api_key_for_redaction
        self._lock_handle = None
        if acquire_owner_lock:
            self._acquire_owner_lock(store.data_dir / "owner.lock")

    def reply(self, user_text: str) -> ProviderResponse:
        user_text = user_text.strip()
        if not user_text:
            raise ValueError("message is empty")
        if contains_secret(user_text, self.api_key_for_redaction):
            raise SecretRejected("message appears to contain an API key")
        self.store.append("user", user_text)
        messages = bounded_context(self.system_prompt, self.store.messages(), self.budget)
        request_text = self.system_prompt + "\n" + "\n".join(
            f"{message.role}: {message.content}" for message in messages
        )
        self.budget.reserve(request_text)
        response = self.provider.generate(
            self.system_prompt,
            messages,
            GenerationLimits(max_output_tokens=MAX_OUTPUT_TOKENS),
        )
        self.budget.record_usage(
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
        )
        self.store.append(
            "assistant",
            response.text,
            provider=response.provider,
            model=response.model,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
        )
        return response

    def status(self) -> dict:
        return {
            "version": 1,
            "captain": "Captain",
            "provider": self.provider.name,
            "model": self.provider.model,
            "session_id": self.store.session_id,
            "usage": self.budget.status(),
        }

    def transcript(self, limit: int = 50) -> list[dict]:
        messages = self.store.messages()
        start = max(0, len(messages) - max(1, min(limit, 100)))
        return [
            {"role": message.role, "content": message.content}
            for message in messages[start:]
        ]

    def close(self) -> None:
        if self._lock_handle is not None:
            fcntl.flock(self._lock_handle, fcntl.LOCK_UN)
            self._lock_handle.close()
            self._lock_handle = None

    def _acquire_owner_lock(self, path: Path) -> None:
        descriptor = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
        handle = os.fdopen(descriptor, "r+")
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            handle.close()
            raise OwnershipError(
                "another Live Captain interface already owns the conversation"
            ) from None
        handle.seek(0)
        handle.truncate()
        handle.write(str(os.getpid()))
        handle.flush()
        os.fsync(handle.fileno())
        self._lock_handle = handle

    def __enter__(self) -> "CaptainEngine":
        return self

    def __exit__(self, *args) -> None:
        self.close()
