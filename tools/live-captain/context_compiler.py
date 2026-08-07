"""Minimal context compiler for the Live Captain bootstrap (packet section 8).

Pure concatenation: captain kernel + current bearing + whole recent
conversation, chronological + the current Admiral message. The compiler
makes no decisions about role, tool permission, harvest, project, mode,
or task type -- those are Captain judgments, not context-compiler
workflow classifications.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


class ContextCompilerError(RuntimeError):
    pass


def compact_runtime_sources(
    current_bearing: str, continuity_ledger: str, claude_channel: str
) -> tuple[str, str, str]:
    """Strip audit history from the hot prompt without altering its source files.

    The full files remain authoritative and digestible on disk.  A turn needs the
    current operating course, durable commitments/open proofs, and the latest
    inter-Captain dispatch—not every superseded commissioning detail and receipt.
    Unknown/synthetic inputs pass through unchanged so this stays inspectable.
    """
    bearing_markers = (
        "## Current operational bearing, 2026-08-06",
        "## Living Captain Master Page course, 2026-08-05",
    )
    bearing_marker = next((marker for marker in bearing_markers if marker in current_bearing), None)
    if bearing_marker:
        current_bearing = (
            "# Current Bearing — Hot Context\n\n"
            + bearing_marker
            + current_bearing.split(bearing_marker, 1)[1]
        )

    ledger_marker = "## Verified state"
    if ledger_marker in continuity_ledger:
        continuity_ledger = continuity_ledger.split(ledger_marker, 1)[0].rstrip() + (
            "\n\nVerified-state receipts remain in the authoritative ledger on disk; "
            "load them only for a relevant inspection."
        )

    dispatch_marker = "\n---\n"
    if dispatch_marker in claude_channel:
        claude_channel = claude_channel.rsplit(dispatch_marker, 1)[1].strip()
    return current_bearing, continuity_ledger, claude_channel


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
    interaction_mode: str = "bridge",
) -> str:
    if not captain_kernel or not captain_kernel.strip():
        raise ContextCompilerError("captain kernel is required and was empty")
    if not current_bearing or not current_bearing.strip():
        raise ContextCompilerError("current bearing is required and was empty")
    if not continuity_ledger or not continuity_ledger.strip():
        raise ContextCompilerError("continuity ledger is required and was empty")
    if not current_admiral_message or not current_admiral_message.strip():
        raise ContextCompilerError("current Admiral message is required and was empty")
    current_bearing, continuity_ledger, claude_channel = compact_runtime_sources(
        current_bearing, continuity_ledger, claude_channel
    )
    if interaction_mode not in {"bridge", "command_draft"}:
        raise ContextCompilerError(f"unsupported interaction mode: {interaction_mode}")
    interaction_contract = ""
    if interaction_mode == "command_draft":
        interaction_contract = """# Interaction contract — Command Draft

The current Admiral message was deliberately composed and dispatched in Command Draft posture. Interpret it as one coherent high-level command. Any direct action stated in it is intended and authorized for immediate implementation within the established private Monad scope. Resolve routine sequencing yourself, act through the real system, test and inspect the result, and report completed evidence. Questions, conditionals, explicit pauses, and established authority boundaries remain questions, conditionals, pauses, and boundaries; do not manufacture authorization beyond the text."""
    sections = [
        captain_kernel.strip(),
        current_bearing.strip(),
        continuity_ledger.strip(),
        "# Message from Claude\n\n" + (claude_channel.strip() or "(no message from Claude right now)"),
        "# Recent conversation\n\n" + format_chronological_messages(recent_messages, omitted),
        interaction_contract,
        "# Current Admiral message\n\n" + current_admiral_message.strip(),
    ]
    return "\n\n---\n\n".join(section for section in sections if section)


def compile_watch_context(
    captain_kernel: str,
    current_bearing: str,
    continuity_ledger: str,
    recent_messages: list[dict],
    objective: dict,
    move_number: int,
    omitted: int = 0,
    claude_channel: str = "",
) -> str:
    """Compile an autonomous Captain move without fabricating an Admiral message."""
    if objective.get("state") not in {"APPROVED", "ACTIVE"}:
        raise ContextCompilerError("watch objective is not Admiral-approved")
    instruction = f"""# Captain Watch Move

This is autonomous move {move_number} of {objective['move_budget']} under the persisted Admiral-approved objective below. It is not a new Admiral message.

Objective: {objective['objective']}
Authorized scope: {objective['scope']}
Success criteria: {json.dumps(objective['success_criteria'])}
Prior move result: {objective.get('last_result') or '(first move)'}

Choose and complete one useful bounded move now. Use real tools when needed. Test or inspect the result. Stay within scope. End with a concise evidence checkpoint containing what changed or was learned and the best next move. Do not ask the Admiral to perform routine mechanics."""
    current_bearing, continuity_ledger, claude_channel = compact_runtime_sources(
        current_bearing, continuity_ledger, claude_channel
    )
    sections = [
        captain_kernel.strip(), current_bearing.strip(), continuity_ledger.strip(),
        "# Message from Claude\n\n" + (claude_channel.strip() or "(no message from Claude right now)"),
        "# Recent conversation\n\n" + format_chronological_messages(recent_messages, omitted),
        instruction,
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
    current_bearing, continuity_ledger, _ = compact_runtime_sources(
        current_bearing, continuity_ledger, ""
    )
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
