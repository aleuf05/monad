#!/usr/bin/env python3
"""Build the deterministic, source-preserving Admiralty Archive inventory.

This first pass inventories documentary files only. It never moves, edits, or
classifies source documents as canonical; hand-authored archive records remain
separate from generated registry/documents.json.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "admiralty" / "archive"
REGISTRY = ARCHIVE / "registry" / "documents.json"

INCLUDE_DIRS = ("docs", "logs", "archive", "fleetcore", "projects", "intentforge", "tools", "toys")
TOP_LEVEL = ("000_HIGHEST_PRIORITY_MONAD_CHARTER_2026-07-14.md", "001_MONAD_COMMAND_CHARTER_2026-07-15.md", "002_CHRONICLE_OF_VESSEL_MONAD_2026-07-16.md", "README.md", "CLAUDE.md", "AGENTS.md")
EXCLUDED_PARTS = {".git", ".venv", "target", "node_modules", "__pycache__", ".pytest_cache", "admiralty"}
EXTENSIONS = {".md", ".mdx", ".rst", ".txt"}


def source_files() -> list[Path]:
    files = {ROOT / name for name in TOP_LEVEL if (ROOT / name).is_file()}
    for dirname in INCLUDE_DIRS:
        base = ROOT / dirname
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_file() and path.suffix.lower() in EXTENSIONS and not (set(path.parts) & EXCLUDED_PARTS):
                files.add(path)
    return sorted(files, key=lambda p: p.relative_to(ROOT).as_posix())


def title_for(text: str, path: Path) -> str:
    match = re.search(r"^#\s+(.+?)\s*$", text, re.MULTILINE)
    return match.group(1).strip() if match else path.stem.replace("_", " ").replace("-", " ")


def doc_type(path: Path, text: str) -> str:
    lower = path.as_posix().lower()
    if "charter" in lower:
        return "charter"
    if "/doctrine/" in lower or "doctrine" in lower:
        return "doctrine"
    if "/research/" in lower or "research" in lower:
        return "research"
    if "/report" in lower or "report" in lower:
        return "report"
    if "/log" in lower or "log" in lower:
        return "log"
    if "/architecture/" in lower or "architecture" in lower:
        return "architecture"
    if "readme" in path.name.lower():
        return "readme"
    return "document"


def status(text: str) -> str:
    header = text[:1200]
    explicit = re.search(r"(?im)^\s*\*{0,2}(?:status|authority status)\*{0,2}\s*[:—-]\s*([^\n]+)", header)
    value = explicit.group(1).upper() if explicit else ""
    if "CANONICAL" in value or "ADOPTED" in value or "ACTIVE STANDING ORDER" in value:
        return "canonical"
    if "SUPERSEDED" in value or "RETIRED" in value or "DEPRECATED" in value:
        return "superseded"
    if "DRAFT" in value or "PROPOSAL" in value or "PROVISIONAL" in value:
        return "proposed"
    return "reference"


def origin_for(path: Path, text: str) -> str:
    lower = path.as_posix().lower()
    if "retrospective" in lower or "retrospective" in text[:1200].lower():
        return "retrospective"
    if "derived" in text[:1200].lower() and "origin" in text[:1200].lower():
        return "derived"
    return "contemporaneous"


def record(path: Path, prior: dict[str, dict]) -> dict:
    relative = path.relative_to(ROOT).as_posix()
    raw = path.read_bytes()
    text = raw.decode("utf-8", errors="replace")
    stat = path.stat()
    stable_id = "doc-" + re.sub(r"[^a-z0-9]+", "-", relative.lower()).strip("-")
    old = prior.get(stable_id, {})
    return {
        "id": stable_id,
        "title": title_for(text, path),
        "source_path": relative,
        "document_type": doc_type(path, text),
        "domain": relative.split("/", 1)[0] if "/" in relative else "root",
        "project": old.get("project"),
        "created_date": old.get("created_date"),
        "date_confidence": old.get("date_confidence", "unknown"),
        "record_origin": old.get("record_origin", origin_for(path, text)),
        "authority_status": old.get("authority_status", status(text)),
        "lifecycle_status": old.get("lifecycle_status", "active"),
        "summary": old.get("summary", ""),
        "significance": old.get("significance", ""),
        "requires_decision": old.get("requires_decision", False),
        "tags": old.get("tags", []),
        "related_documents": old.get("related_documents", []),
        "registered_at": old.get("registered_at", ""),
        "registered_by": "codex",
        "provenance_notes": old.get("provenance_notes", "Generated inventory; source remains canonical evidence."),
        "content_sha256": hashlib.sha256(raw).hexdigest(),
        "byte_size": stat.st_size,
        "headings": re.findall(r"^#{1,3}\s+(.+?)\s*$", text, re.MULTILINE),
    }


def build() -> tuple[list[dict], list[str]]:
    prior = {}
    if REGISTRY.exists():
        try:
            prior = {item["id"]: item for item in json.loads(REGISTRY.read_text()).get("documents", [])}
        except (ValueError, KeyError):
            prior = {}
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    records = [record(path, prior) for path in source_files()]
    for item in records:
        if not item["registered_at"]:
            item["registered_at"] = now
    return records, now


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scan", action="store_true", help="write the inventory")
    parser.add_argument("--check", action="store_true", help="verify inventory matches sources")
    parser.add_argument("--dry-run", action="store_true", help="report counts without writing")
    args = parser.parse_args()
    records, built_at = build()
    payload = {"schema_version": "monad.admiralty.documents.v0.1", "generated_at": built_at, "source_root": ".", "documents": records}
    if args.check:
        if not REGISTRY.exists() or json.loads(REGISTRY.read_text()).get("documents") != records:
            print("Archive inventory is stale; run --scan.")
            return 1
        print(f"Archive inventory is current: {len(records)} documents.")
        return 0
    if args.dry_run or not args.scan:
        print(f"Would inventory {len(records)} documentary files.")
        return 0
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {REGISTRY.relative_to(ROOT)} with {len(records)} documents.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
