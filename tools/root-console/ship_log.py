"""Read-only ship's log panel data.

Reads five live sources fresh from disk on every call -- no caching, no
duplicate store, exactly what's on disk right now: docs/logs/*.md, the
live-captain continuity ledger and current bearing, and the tail of
data/live-captain/test-runs.jsonl and instruction-sources.log. Entries are
sorted newest-first by file mtime (markdown) or their own timestamp field
(the two JSONL sources).
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

TAIL_LINES = 20
MD_EXCERPT_CHARS = 4000


def _title_from_markdown(text: str, fallback: str) -> str:
    for line in text.splitlines():
        stripped = line.strip().lstrip("#").strip()
        if stripped:
            return stripped
    return fallback


def _md_glob_entries(directory: Path, source: str) -> list[dict]:
    entries: list[dict] = []
    if not directory.is_dir():
        return entries
    for path in directory.glob("*.md"):
        try:
            text = path.read_text(encoding="utf-8")
            mtime = path.stat().st_mtime
        except OSError:
            continue
        entries.append(
            {
                "source": source,
                "file": path.name,
                "title": _title_from_markdown(text, path.name),
                "timestamp": mtime,
                "excerpt": text[:MD_EXCERPT_CHARS],
            }
        )
    return entries


def _single_md_entry(path: Path, source: str) -> list[dict]:
    if not path.is_file():
        return []
    try:
        text = path.read_text(encoding="utf-8")
        mtime = path.stat().st_mtime
    except OSError:
        return []
    return [
        {
            "source": source,
            "file": path.name,
            "title": _title_from_markdown(text, path.name),
            "timestamp": mtime,
            "excerpt": text[:MD_EXCERPT_CHARS],
        }
    ]


def _summarize_jsonl(source: str, record: dict) -> str:
    if source == "test-runs":
        return f"{record.get('result', '?')} · {record.get('tests_run', '?')} tests · {record.get('duration_seconds', '?')}s"
    if source == "instruction-sources":
        metrics = record.get("context_metrics", {}) or {}
        return f"turn {str(record.get('thread_id', '?'))[:8]} · {metrics.get('compiled_chars', '?')} chars compiled"
    return source


def _jsonl_tail_entries(path: Path, source: str, ts_field: str, ts_kind: str) -> list[dict]:
    if not path.is_file():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        fallback_ts = path.stat().st_mtime
    except OSError:
        return []
    entries: list[dict] = []
    for line in lines[-TAIL_LINES:]:
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        raw_ts = record.get(ts_field)
        timestamp = fallback_ts
        if raw_ts is not None:
            try:
                timestamp = float(raw_ts) if ts_kind == "epoch" else datetime.fromisoformat(str(raw_ts)).timestamp()
            except (TypeError, ValueError):
                timestamp = fallback_ts
        entries.append(
            {
                "source": source,
                "file": path.name,
                "title": _summarize_jsonl(source, record),
                "timestamp": timestamp,
                "excerpt": json.dumps(record),
            }
        )
    return entries


def collect(repo_root: Path) -> list[dict]:
    entries: list[dict] = []
    entries += _md_glob_entries(repo_root / "docs" / "logs", "ship-log")
    entries += _single_md_entry(
        repo_root / "tools" / "live-captain" / "context" / "continuity-ledger.md", "continuity-ledger"
    )
    entries += _single_md_entry(
        repo_root / "tools" / "live-captain" / "context" / "current-bearing.md", "current-bearing"
    )
    entries += _jsonl_tail_entries(
        repo_root / "data" / "live-captain" / "test-runs.jsonl", "test-runs", "timestamp", "iso"
    )
    entries += _jsonl_tail_entries(
        repo_root / "data" / "live-captain" / "instruction-sources.log", "instruction-sources", "ts", "epoch"
    )
    entries.sort(key=lambda entry: entry["timestamp"], reverse=True)
    return entries
