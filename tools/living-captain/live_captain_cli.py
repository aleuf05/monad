#!/usr/bin/env python3
"""Local terminal interface for Project Monad Live Captain Version 1."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from conversation import ConversationStore, utc_now
from gemini_provider import GeminiProvider
from live_captain_engine import (
    CaptainEngine,
    OwnershipError,
    SecretRejected,
    bounded_context,
    contains_secret,
)
from model_provider import ModelProvider, ProviderError
from usage_budget import BudgetExceeded, UsageBudget


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "living-captain"
PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "captain-system.md"
LOG_PATH = DATA_DIR / "live-captain.log"


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
    engine: CaptainEngine,
) -> int:
    print("Project Monad — Live Captain — Version 1")
    print("Captain online. Local terminal conversation; no tools or shell access.")
    print_status(engine.provider, engine.store, engine.budget)
    print("Commands: /status, /quit")
    safe_log(
        "started",
        f"provider={engine.provider.name} model={engine.provider.model}",
    )

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
            print_status(engine.provider, engine.store, engine.budget)
            continue
        if user_text.startswith("/"):
            print("Captain> Unknown local command. Available: /status, /quit")
            continue
        try:
            response = engine.reply(user_text)
            print(f"\nCaptain> {response.text}")
            print_status(engine.provider, engine.store, engine.budget)
        except SecretRejected:
            print("Captain> That appears to contain an API key. I did not store or send it.")
            safe_log("secret_rejected")
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
        with CaptainEngine(
            provider=provider,
            store=store,
            budget=budget,
            system_prompt=system_prompt,
            api_key_for_redaction=api_key,
        ) as engine:
            return run_chat(engine)
    except (OSError, ValueError, json.JSONDecodeError, OwnershipError) as error:
        print(f"Live Captain cannot start: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
