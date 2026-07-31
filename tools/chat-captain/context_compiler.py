"""Compiles the compact per-turn context envelope described in the Live
Captain MVP packet, section 8: identity, current situation, a bounded
recent message window, duties, and the structured output contract. Never
sends the entire database or full transcript to the provider.
"""

from __future__ import annotations

import json
from typing import Any, Optional

import database
from model_provider import Message

RECENT_MESSAGE_LIMIT = 20
RECENT_HARVEST_LIMIT = 5

OUTPUT_CONTRACT_INSTRUCTIONS = """
## Output contract

End every reply with exactly one fenced ```captain-json code block containing
a single JSON object of this shape (use null / [] for anything that does not
apply this turn -- do not omit keys):

{
  "reply": "Natural-language Captain response (should match your prose reply above)",
  "mode_suggestion": null,
  "project_suggestion": null,
  "harvest_proposals": [],
  "state_notes": [],
  "safety_signal": null
}

Rules:
- mode_suggestion, if not null, must be one of: master, project_formation,
  design, review, associative_lab, record.
- Each harvest_proposals entry must have: type, title, summary, confidence
  (0.0-1.0), provenance_note. type must be one of: vision, principle,
  project_candidate, decision, design, engineering_handoff, experiment,
  open_question, safety_rule, communication_rule, next_action,
  incident_note, captain_brief. Propose harvest items only for durable
  consequences worth preserving -- do not over-harvest routine remarks.
- Never mark a harvest item accepted or canonical yourself; you only ever
  propose candidates. The Admiral approves or rejects them.
- safety_signal is null unless something in this turn genuinely warrants
  elevated care; if set, use a short label such as "red_alert" or "concern".
"""


def load_seed_instruction(prompt_path: str) -> str:
    with open(prompt_path, "r", encoding="utf-8") as handle:
        return handle.read().strip()


def _format_harvest_item(item: dict[str, Any]) -> str:
    return f"- [{item['type']}] {item['title']}: {item['summary']}"


def compile_system_prompt(
    conn,
    *,
    seed_instruction: str,
    state: dict[str, Any],
    project: Optional[dict[str, Any]],
    last_brief: Optional[str],
) -> str:
    mode = state.get("current_mode", database.DEFAULT_MODE)
    accepted_recent = database.list_harvest_items(conn, status="accepted")[:RECENT_HARVEST_LIMIT]
    open_questions = database.list_harvest_items(conn, status="unresolved")[:RECENT_HARVEST_LIMIT]

    sections = [seed_instruction, "\n## Current situation\n"]
    sections.append(f"- Active mode: {mode}")
    if project:
        sections.append(f"- Active project: {project['title']} ({project['id']})")
        if project.get("purpose"):
            sections.append(f"  Purpose: {project['purpose']}")
        if project.get("current_summary"):
            sections.append(f"  Current summary: {project['current_summary']}")
        if project.get("next_action"):
            sections.append(f"  Next action: {project['next_action']}")
    else:
        sections.append("- Active project: none selected")

    if last_brief:
        sections.append(f"- Last session brief: {last_brief}")
    else:
        sections.append("- Last session brief: none yet (this is a fresh ship)")

    if accepted_recent:
        sections.append("- Recently accepted harvest items:")
        sections.extend(f"  {_format_harvest_item(item)}" for item in accepted_recent)
    if open_questions:
        sections.append("- Open questions still unresolved:")
        sections.extend(f"  {_format_harvest_item(item)}" for item in open_questions)

    sections.append(OUTPUT_CONTRACT_INSTRUCTIONS)
    return "\n".join(sections)


def bounded_messages(conn, session_id: str, limit: int = RECENT_MESSAGE_LIMIT) -> list[Message]:
    rows = database.list_messages(conn, session_id, limit=10_000)
    recent = rows[-limit:]
    return [Message(role=row["role"], content=row["content"]) for row in recent]


def extract_structured_reply(raw_text: str) -> dict[str, Any]:
    """Parse the ```captain-json block. Falls back to a bare-reply shape if
    the provider's structured output is missing or malformed -- the packet
    requires this fallback so a parsing hiccup never drops the reply."""
    marker = "```captain-json"
    start = raw_text.find(marker)
    fallback = {
        "reply": raw_text.strip(),
        "mode_suggestion": None,
        "project_suggestion": None,
        "harvest_proposals": [],
        "state_notes": [],
        "safety_signal": None,
    }
    if start == -1:
        return fallback
    body_start = start + len(marker)
    end = raw_text.find("```", body_start)
    if end == -1:
        return fallback
    block = raw_text[body_start:end].strip()
    prose = raw_text[:start].strip()
    try:
        parsed = json.loads(block)
    except json.JSONDecodeError:
        return fallback
    if not isinstance(parsed, dict):
        return fallback
    result = dict(fallback)
    result.update(parsed)
    if prose:
        result["reply"] = prose
    elif not result.get("reply"):
        result["reply"] = fallback["reply"]
    return result
