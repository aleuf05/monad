"""Single-owner turn engine shared by the web service. Owns the exclusive
lock on the ship's SQLite state and drives one full conversational turn:
persist the user message, compile context, call the provider, validate the
structured reply, persist the assistant message and any valid harvest
proposals. Mirrors the shape of tools/living-captain/live_captain_engine.py
(owner lock, reply()) but threaded through modes/projects/harvest instead
of a single implicit session.
"""

from __future__ import annotations

import fcntl
import os
from pathlib import Path
from typing import Any, Optional

import database
import harvest
from context_compiler import bounded_messages, compile_system_prompt, extract_structured_reply
from model_provider import GenerationLimits, ModelProvider, ProviderError
from usage_budget import UsageBudget

MAX_OUTPUT_TOKENS = 1024  # Codex ignores this; kept to satisfy the ModelProvider contract.
BRIEF_CLOSE_INSTRUCTION = (
    "\n\nThe Admiral is closing this session. Produce a compact operational "
    "brief in plain prose (no JSON block for this reply) covering: what "
    "happened, what changed, accepted results, candidate results still "
    "awaiting review, unresolved questions, the active project and mode, "
    "the next useful move, and any safety or communication issue worth "
    "carrying forward."
)


class OwnershipError(RuntimeError):
    pass


class CaptainEngine:
    def __init__(
        self,
        *,
        provider: ModelProvider,
        conn,
        budget: UsageBudget,
        seed_instruction: str,
        data_dir: Path,
        acquire_owner_lock: bool = True,
    ):
        self.provider = provider
        self.conn = conn
        self.budget = budget
        self.seed_instruction = seed_instruction
        self._lock_handle = None
        if acquire_owner_lock:
            self._acquire_owner_lock(Path(data_dir) / "owner.lock")
        self._ensure_open_session()

    def _ensure_open_session(self) -> dict[str, Any]:
        state = database.get_state(self.conn)
        session_id = state.get("current_session_id")
        if session_id:
            session = database.get_session(self.conn, session_id)
            if session and session["status"] == "open":
                return session
        return self.start_session()

    def start_session(self) -> dict[str, Any]:
        state = database.get_state(self.conn)
        mode = state.get("current_mode", database.DEFAULT_MODE)
        project_id = state.get("active_project_id")
        session = database.create_session(self.conn, mode=mode, project_id=project_id)
        database.update_state(self.conn, current_session_id=session["id"])
        return session

    def close_session(self) -> dict[str, Any]:
        state = database.get_state(self.conn)
        session_id = state["current_session_id"]
        brief = self._generate_brief(session_id)
        session = database.close_session(
            self.conn, session_id, mode_at_end=state["current_mode"], brief=brief
        )
        database.update_state(
            self.conn,
            last_session_brief=brief,
            last_successful_harvest_at=state.get("last_successful_harvest_at"),
            current_session_id=None,
        )
        return session

    def _generate_brief(self, session_id: str) -> str:
        messages = bounded_messages(self.conn, session_id, limit=60)
        if not messages:
            return "Session closed with no conversation recorded."
        state = database.get_state(self.conn)
        project_id = state.get("active_project_id")
        project = database.get_project(self.conn, project_id) if project_id else None
        # Ground the brief in actual ship state (accepted harvest items,
        # project facts) rather than letting the model free-narrate from
        # the transcript alone -- a transcript-only brief can confabulate
        # facts (e.g. describing an already-accepted item as still
        # pending) that the ship's own state already contradicts.
        instruction = compile_system_prompt(
            self.conn,
            seed_instruction=self.seed_instruction,
            state=state,
            project=project,
            last_brief=state.get("last_session_brief"),
        ) + BRIEF_CLOSE_INSTRUCTION
        try:
            response = self.provider.generate(
                instruction, messages, GenerationLimits(max_output_tokens=MAX_OUTPUT_TOKENS)
            )
        except ProviderError:
            return "Session closed; brief generation failed, full transcript preserved."
        return response.text

    def reply(self, user_text: str) -> dict[str, Any]:
        user_text = user_text.strip()
        if not user_text:
            raise ValueError("message is empty")

        state = database.get_state(self.conn)
        session_id = state["current_session_id"]
        active_project_id = state.get("active_project_id")
        project = database.get_project(self.conn, active_project_id) if active_project_id else None

        database.append_message(
            self.conn,
            session_id=session_id,
            role="user",
            content=user_text,
            mode=state["current_mode"],
            project_id=active_project_id,
        )

        system_prompt = compile_system_prompt(
            self.conn,
            seed_instruction=self.seed_instruction,
            state=state,
            project=project,
            last_brief=state.get("last_session_brief"),
        )
        messages = bounded_messages(self.conn, session_id)

        self.budget.reserve(system_prompt + "".join(message.content for message in messages))
        response = self.provider.generate(
            system_prompt, messages, GenerationLimits(max_output_tokens=MAX_OUTPUT_TOKENS)
        )
        self.budget.record_usage(input_tokens=response.input_tokens, output_tokens=response.output_tokens)

        structured = extract_structured_reply(response.text)

        database.append_message(
            self.conn,
            session_id=session_id,
            role="assistant",
            content=structured["reply"],
            mode=state["current_mode"],
            project_id=active_project_id,
            provider=response.provider,
            model=response.model,
        )

        stored_harvest = []
        for candidate in structured.get("harvest_proposals") or []:
            cleaned = harvest.validate_proposal(candidate)
            if cleaned is None:
                continue
            item = database.create_harvest_item(
                self.conn,
                type=cleaned["type"],
                title=cleaned["title"],
                summary=cleaned["summary"],
                project_id=active_project_id,
                session_id=session_id,
                provenance_note=cleaned.get("provenance_note"),
                confidence=cleaned.get("confidence"),
            )
            stored_harvest.append(item)

        mode_suggestion = structured.get("mode_suggestion")
        if mode_suggestion not in database.MODES:
            mode_suggestion = None

        database.update_state(
            self.conn,
            last_successful_interaction_at=database.now(),
            provider_name=response.provider,
            provider_model=response.model,
        )

        return {
            "reply": structured["reply"],
            "mode_suggestion": mode_suggestion,
            "project_suggestion": structured.get("project_suggestion"),
            "harvest_proposals": stored_harvest,
            "state_notes": structured.get("state_notes") or [],
            "safety_signal": structured.get("safety_signal"),
            "provider": response.provider,
            "model": response.model,
        }

    def status(self) -> dict[str, Any]:
        state = database.get_state(self.conn)
        return {
            "state": state,
            "provider": self.provider.name,
            "model": self.provider.model,
            "usage": self.budget.status(),
        }

    def close(self) -> None:
        if self._lock_handle is not None:
            fcntl.flock(self._lock_handle, fcntl.LOCK_UN)
            self._lock_handle.close()
            self._lock_handle = None

    def _acquire_owner_lock(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
        handle = os.fdopen(descriptor, "r+")
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            handle.close()
            raise OwnershipError("another Chat Captain process already owns the ship state") from None
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
