"""Durable, append-only conversation storage for Live Captain Version 1."""

from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any

from model_provider import Message


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class ConversationStore:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir.resolve()
        self.transcript_path = self.data_dir / "conversation.jsonl"
        self.state_path = self.data_dir / "conversation-state.json"
        self.data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.data_dir, 0o700)
        self.state = self._load_or_create_state()

    @property
    def session_id(self) -> str:
        return str(self.state["session_id"])

    def append(
        self,
        role: str,
        content: str,
        *,
        provider: str | None = None,
        model: str | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
    ) -> dict[str, Any]:
        if role not in {"user", "assistant"}:
            raise ValueError("role must be user or assistant")
        self.state["sequence"] += 1
        entry = {
            "session_id": self.session_id,
            "sequence": self.state["sequence"],
            "recorded_at": utc_now(),
            "role": role,
            "content": content,
            "provider": provider,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        }
        self._append_jsonl(entry)
        self._write_state()
        return entry

    def messages(self) -> list[Message]:
        if not self.transcript_path.exists():
            return []
        messages: list[Message] = []
        with self.transcript_path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                if entry.get("session_id") != self.session_id:
                    continue
                role = entry.get("role")
                content = entry.get("content")
                if role in {"user", "assistant"} and isinstance(content, str):
                    messages.append(Message(role=role, content=content))
        return messages

    def _load_or_create_state(self) -> dict[str, Any]:
        if self.state_path.exists():
            state = json.loads(self.state_path.read_text(encoding="utf-8"))
            if (
                isinstance(state, dict)
                and isinstance(state.get("session_id"), str)
                and isinstance(state.get("sequence"), int)
            ):
                return state
            raise ValueError("conversation state is malformed")
        state = {
            "version": 1,
            "session_id": str(uuid.uuid4()),
            "sequence": 0,
            "created_at": utc_now(),
        }
        self.state = state
        self._write_state()
        return state

    def _append_jsonl(self, entry: dict[str, Any]) -> None:
        flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
        descriptor = os.open(self.transcript_path, flags, 0o600)
        try:
            with os.fdopen(descriptor, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(entry, sort_keys=True) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
        finally:
            # fdopen owns the descriptor, except if it failed before wrapping.
            try:
                os.close(descriptor)
            except OSError:
                pass

    def _write_state(self) -> None:
        temporary = self.state_path.with_suffix(".json.tmp")
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
        os.replace(temporary, self.state_path)
        os.chmod(self.state_path, 0o600)
