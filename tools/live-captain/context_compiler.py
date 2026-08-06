"""Minimal context compiler for the Live Captain bootstrap (packet section 8).

Pure concatenation: captain kernel + current bearing + whole recent
conversation, chronological + the current Admiral message. The compiler
makes no decisions about role, tool permission, harvest, project, mode,
or task type -- those are Captain judgments, not context-compiler
workflow classifications.
"""

from __future__ import annotations

import hashlib
from pathlib import Path


class ContextCompilerError(RuntimeError):
    pass


def load_required_text(path: Path, label: str) -> tuple[str, str]:
    """Read a required file and return (text, sha256 digest). Missing or
    empty required content is an explicit startup failure, not a silent
    default -- packet section 14."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ContextCompilerError(f"{label} is missing or unreadable: {path}") from exc
    if not text.strip():
        raise ContextCompilerError(f"{label} is empty: {path}")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return text, digest


def load_optional_text(path: Path, placeholder: str) -> tuple[str, str]:
    """Read optional context content. Unlike load_required_text, a missing or
    empty file is not a startup failure -- this source is allowed to be
    silent, and falls back to the placeholder so the digest is still stable."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        text = ""
    if not text.strip():
        text = placeholder
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return text, digest


def format_chronological_messages(messages: list[dict], omitted: int = 0) -> str:
    if not messages:
        lines = ["(no prior conversation yet)"]
    else:
        lines = []
        for message in messages:
            speaker = "Admiral" if message["role"] == "admiral" else "Captain"
            lines.append(f"{speaker}: {message['text']}")
    body = "\n\n".join(lines)
    if omitted > 0:
        body = (
            f"[{omitted} earlier message(s) omitted from this window -- "
            "not summarized, not retrieved, simply not included.]\n\n" + body
        )
    return body


def compile_live_captain_context(
    captain_kernel: str,
    current_bearing: str,
    continuity_ledger: str,
    recent_messages: list[dict],
    current_admiral_message: str,
    omitted: int = 0,
    claude_channel: str = "",
) -> str:
    if not captain_kernel or not captain_kernel.strip():
        raise ContextCompilerError("captain kernel is required and was empty")
    if not current_bearing or not current_bearing.strip():
        raise ContextCompilerError("current bearing is required and was empty")
    if not continuity_ledger or not continuity_ledger.strip():
        raise ContextCompilerError("continuity ledger is required and was empty")
    if not current_admiral_message or not current_admiral_message.strip():
        raise ContextCompilerError("current Admiral message is required and was empty")
    sections = [
        captain_kernel.strip(),
        current_bearing.strip(),
        continuity_ledger.strip(),
        "# Message from Claude\n\n" + (claude_channel.strip() or "(no message from Claude right now)"),
        "# Recent conversation\n\n" + format_chronological_messages(recent_messages, omitted),
        "# Current Admiral message\n\n" + current_admiral_message.strip(),
    ]
    return "\n\n---\n\n".join(sections)


def context_size_metrics(
    captain_kernel: str,
    current_bearing: str,
    continuity_ledger: str,
    recent_messages: list[dict],
    current_admiral_message: str,
    compiled_context: str,
) -> dict[str, int]:
    """Measure source sizes without adding a tokenizer dependency."""
    conversation = format_chronological_messages(recent_messages)
    return {
        "kernel_chars": len(captain_kernel),
        "bearing_chars": len(current_bearing),
        "ledger_chars": len(continuity_ledger),
        "conversation_chars": len(conversation),
        "current_message_chars": len(current_admiral_message),
        "compiled_chars": len(compiled_context),
        "compiled_bytes": len(compiled_context.encode("utf-8")),
    }
