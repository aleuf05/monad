#!/usr/bin/env python3
"""Local terminal interface for Project Monad Live Captain Version 1."""

from __future__ import annotations

import hmac
import json
import os
import re
import sys
from pathlib import Path

from conversation import ConversationStore, utc_now
from gemini_provider import GeminiProvider
from model_provider import GenerationLimits, Message, ModelProvider, ProviderError
from usage_budget import BudgetExceeded, MAX_INPUT_TOKENS, MAX_OUTPUT_TOKENS, UsageBudget


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "living-captain"
PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "captain-system.md"
LOG_PATH = DATA_DIR / "live-captain.log"
SECRET_PATTERN = re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b")


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
    return bool(api_key) and len(text) >= len(api_key) and api_key in text and hmac.compare_digest(
        api_key,
        text[text.find(api_key) : text.find(api_key) + len(api_key)],
    )


def safe_log(kind: str, detail: str = "") -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(DATA_DIR, 0o700)
    entry = {"recorded_at": utc_now(), "kind": kind, "detail": detail[:300]}
    descriptor = os.open(LOG_PATH, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    with os.fdopen(descriptor, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def print_status(provider: ModelProvider, store: ConversationStore, budget: UsageBudget) -> None:
    status = budget.status()
    print(f"Provider: {provider.name} / {provider.model}")
    print(f"Session: {store.session_id}")
    print(
        "Usage: "
        f"{status['request_count']}/{status['max_requests']} requests; "
        f"${status['reserved_dollars']:.4f}/${status['max_dollars']:.2f} "
        "locally reserved estimate"
    )


def run_chat(
    provider: ModelProvider,
    store: ConversationStore,
    budget: UsageBudget,
    system_prompt: str,
    *,
    api_key_for_redaction: str = "",
) -> int:
    print("Project Monad — Live Captain — Version 1")
    print("Captain online. Local terminal conversation; no tools or shell access.")
    print_status(provider, store, budget)
    print("Commands: /status, /quit")
    safe_log("started", f"provider={provider.name} model={provider.model}")

    while True:
        try:
            user_text = input("\nAdmiral> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nCaptain> Standing down cleanly, Admiral.")
            safe_log("stopped", "operator interrupt")
            return 0
        if not user_text:
            continue
        if user_text == "/quit":
            print("Captain> Standing down cleanly, Admiral.")
            safe_log("stopped", "operator command")
            return 0
        if user_text == "/status":
            print_status(provider, store, budget)
            continue
        if user_text.startswith("/"):
            print("Captain> Unknown local command. Available: /status, /quit")
            continue
        if contains_secret(user_text, api_key_for_redaction):
            print("Captain> That appears to contain an API key. I did not store or send it.")
            safe_log("secret_rejected")
            continue

        store.append("user", user_text)
        try:
            messages = bounded_context(system_prompt, store.messages(), budget)
            request_text = system_prompt + "\n" + "\n".join(
                f"{message.role}: {message.content}" for message in messages
            )
            budget.reserve(request_text)
            response = provider.generate(
                system_prompt,
                messages,
                GenerationLimits(max_output_tokens=MAX_OUTPUT_TOKENS),
            )
            budget.record_usage(
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
            )
            store.append(
                "assistant",
                response.text,
                provider=response.provider,
                model=response.model,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
            )
            print(f"\nCaptain> {response.text}")
            print_status(provider, store, budget)
        except BudgetExceeded as error:
            print(f"Captain> Request blocked by the local usage boundary: {error}")
            safe_log("budget_blocked", str(error))
        except ProviderError as error:
            print(f"Captain> I could not reach the model: {error}")
            safe_log("provider_error", str(error))


def main() -> int:
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print(
            "Live Captain cannot start: GEMINI_API_KEY is not present in the process environment.",
            file=sys.stderr,
        )
        return 2
    try:
        system_prompt = PROMPT_PATH.read_text(encoding="utf-8").strip()
        if not system_prompt:
            raise ValueError("Captain system prompt is empty")
        store = ConversationStore(DATA_DIR)
        budget = UsageBudget(DATA_DIR / "usage.json")
        provider = GeminiProvider(api_key)
        return run_chat(
            provider,
            store,
            budget,
            system_prompt,
            api_key_for_redaction=api_key,
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Live Captain cannot start: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
