#!/usr/bin/env python3
"""Build the static Monad Watchbook log index."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

SUPPORTED_EXTENSIONS = {".md", ".markdown", ".txt", ".log"}
ROLE_ALIASES = {
    "captains": "Captains",
    "captain": "Captains",
    "agents": "Agents",
    "agent": "Agents",
    "admirals": "Admirals",
    "admiral": "Admirals",
}
DATE_RE = re.compile(r"(20\d{2})[-_](\d{2})[-_](\d{2})")


def read_text(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def title_from(path: Path, text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip() or path.stem
        if stripped:
            return stripped[:96]
    return path.stem.replace("_", " ").replace("-", " ").strip() or path.name


def role_from(parts: tuple[str, ...]) -> str:
    for part in parts:
        key = part.lower()
        if key in ROLE_ALIASES:
            return ROLE_ALIASES[key]
    return "Other"


def entity_from(parts: tuple[str, ...], role: str) -> str:
    lowered = [part.lower() for part in parts]
    role_keys = [key for key, value in ROLE_ALIASES.items() if value == role]
    for index, part in enumerate(lowered):
        if part in role_keys:
            for candidate in parts[index + 1 :]:
                if candidate.isdigit() or candidate.lower() == role.lower():
                    continue
                if '.' in candidate:
                    return role
                return candidate
            return role
    return role


def date_from(rel_path: str, stat_mtime: float) -> tuple[str | None, str]:
    match = DATE_RE.search(rel_path)
    if match:
        date = "-".join(match.groups())
        return date, f"{date}T00:00:00Z"
    fallback = datetime.fromtimestamp(stat_mtime, timezone.utc)
    return None, fallback.isoformat().replace("+00:00", "Z")


def excerpt(text: str, limit: int = 220) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "..."


def build_index(repo_root: Path, logs_dir: Path) -> dict:
    entries = []
    for path in sorted(logs_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        rel = path.relative_to(repo_root).as_posix()
        parts = Path(rel).parts
        stat = path.stat()
        text = read_text(path)
        role = role_from(parts)
        log_date, sort_ts = date_from(rel, stat.st_mtime)
        entries.append({
            "id": re.sub(r"[^a-zA-Z0-9_-]+", "-", rel).strip("-").lower(),
            "path": rel,
            "fetchPath": "../../" + rel,
            "title": title_from(path, text),
            "role": role,
            "entity": entity_from(parts, role),
            "year": log_date[:4] if log_date else str(datetime.fromtimestamp(stat.st_mtime).year),
            "date": log_date,
            "sortTimestamp": sort_ts,
            "fileType": path.suffix.lower().lstrip("."),
            "sizeBytes": stat.st_size,
            "modifiedAt": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat().replace("+00:00", "Z"),
            "excerpt": excerpt(text),
        })

    entries.sort(key=lambda item: (item["sortTimestamp"], item["path"]), reverse=True)
    counts_by_role: dict[str, int] = {}
    counts_by_entity: dict[str, int] = {}
    counts_by_year: dict[str, int] = {}
    for entry in entries:
        counts_by_role[entry["role"]] = counts_by_role.get(entry["role"], 0) + 1
        counts_by_entity[entry["entity"]] = counts_by_entity.get(entry["entity"], 0) + 1
        counts_by_year[entry["year"]] = counts_by_year.get(entry["year"], 0) + 1

    generated = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return {
        "schemaVersion": 1,
        "generatedAt": generated,
        "sourceRoot": "logs/",
        "entryCount": len(entries),
        "latestLogTimestamp": entries[0]["sortTimestamp"] if entries else None,
        "counts": {
            "byRole": dict(sorted(counts_by_role.items())),
            "byEntity": dict(sorted(counts_by_entity.items())),
            "byYear": dict(sorted(counts_by_year.items(), reverse=True)),
        },
        "entries": entries,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build toys/watchbook/log-index.json from logs/.")
    parser.add_argument("--repo-root", default=Path(__file__).resolve().parents[1], type=Path)
    parser.add_argument("--logs-dir", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    logs_dir = (args.logs_dir or repo_root / "logs").resolve()
    output = (args.output or repo_root / "toys" / "watchbook" / "log-index.json").resolve()
    if not logs_dir.is_dir():
        raise SystemExit(f"logs directory not found: {logs_dir}")

    manifest = build_index(repo_root, logs_dir)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Indexed {manifest['entryCount']} logs -> {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())