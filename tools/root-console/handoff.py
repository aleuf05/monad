"""Captain handoff inbox.

Structured, file-based records of completed agent tasks, written by whatever
process ran the task (a Claude or Codex session, run from anywhere -- this
module does not assume it is imported by the process that wrote a given
file) and read by the Root Console server so the Live Captain can inspect
results without a manual clipboard copy. One markdown file per completed
task; the inbox directory is the single canonical location, per
docs/doctrine/009-live-captain-authority-contract.md and the packet that
authorized it.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

INBOX_DIR = Path.home() / ".monad" / "handoffs" / "captain_inbox"

_FIELD_PREFIXES = {
    "Task ID": "taskId",
    "Agent": "agent",
    "Timestamp": "timestamp",
    "Repository": "repository",
    "Branch": "branch",
    "Push status": "pushStatus",
    "Commit SHA": "commitSha",
}


class HandoffError(Exception):
    pass


def ensure_inbox() -> Path:
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    return INBOX_DIR


def _section(title: str, items: list[str] | None) -> list[str]:
    body = list(items) if items else ["none"]
    return [f"## {title}", "", *(f"- {line}" for line in body), ""]


def write_handoff(
    *,
    agent: str,
    task_id: str,
    repository: str,
    branch: str,
    requested_outcome: str,
    completed_outcome: str,
    files_changed: list[str] | None = None,
    commands_executed: list[str] | None = None,
    tests_and_results: list[str] | None = None,
    git_status: str = "",
    commit_sha: str | None = None,
    push_status: str | None = None,
    known_limitations: list[str] | None = None,
    questions_for_captain: list[str] | None = None,
) -> Path:
    """Write one structured handoff file and return its path."""
    ensure_inbox()
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_task_id = "".join(c if c.isalnum() or c in "-_." else "-" for c in task_id) or "task"
    safe_agent = "".join(c if c.isalnum() or c in "-_." else "-" for c in agent) or "agent"
    filename = f"{ts}_{safe_agent}_{safe_task_id}_handoff.md"
    path = INBOX_DIR / filename

    lines = [
        f"# Captain Handoff — {task_id}",
        "",
        f"- Task ID: {task_id}",
        f"- Agent: {agent}",
        f"- Timestamp: {ts}",
        f"- Repository: {repository}",
        f"- Branch: {branch}",
        f"- Commit SHA: {commit_sha or 'none (not committed)'}",
        f"- Push status: {push_status or 'none (not pushed)'}",
        "",
        *_section("Requested outcome", [requested_outcome]),
        *_section("Completed outcome", [completed_outcome]),
        *_section("Files changed", files_changed),
        *_section("Commands executed", [f"`{c}`" for c in commands_executed] if commands_executed else None),
        *_section("Tests and results", tests_and_results),
        "## Git status",
        "",
        "```text",
        git_status or "(not recorded)",
        "```",
        "",
        *_section("Known limitations", known_limitations),
        *_section("Questions requiring Captain judgment", questions_for_captain),
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _parse_fields(text: str) -> dict:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if not line.startswith("- "):
            continue
        if ":" not in line:
            continue
        label, _, value = line[2:].partition(":")
        key = _FIELD_PREFIXES.get(label.strip())
        if key:
            fields[key] = value.strip()
    return fields


def list_handoffs() -> list[dict]:
    """Newest-first summaries of every handoff currently in the inbox."""
    ensure_inbox()
    items = []
    for path in INBOX_DIR.glob("*_handoff.md"):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        fields = _parse_fields(text)
        push_status = fields.get("pushStatus", "")
        published = bool(push_status) and not push_status.lower().startswith("none")
        items.append(
            {
                "file": path.name,
                "path": str(path),
                "agent": fields.get("agent", "unknown"),
                "taskId": fields.get("taskId", "unknown"),
                "timestamp": fields.get("timestamp", ""),
                "repository": fields.get("repository", ""),
                "branch": fields.get("branch", ""),
                "commitSha": fields.get("commitSha", ""),
                "publicationState": "PUBLISHED" if published else "LOCAL_ONLY",
                "mtime": path.stat().st_mtime,
            }
        )
    items.sort(key=lambda item: (item["timestamp"], item["mtime"]), reverse=True)
    for item in items:
        del item["mtime"]
    return items


def read_handoff(filename: str) -> str:
    """Full contents of one handoff file, given its bare filename."""
    ensure_inbox()
    if "/" in filename or filename in ("", ".", ".."):
        raise HandoffError("invalid handoff filename")
    candidate = (INBOX_DIR / filename).resolve()
    if candidate.parent != INBOX_DIR.resolve():
        raise HandoffError("invalid handoff filename")
    if not candidate.is_file():
        raise HandoffError("handoff not found")
    return candidate.read_text(encoding="utf-8")
