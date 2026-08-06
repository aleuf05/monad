"""Live corpus for the Semantic Document Viewer (console/documents.html).

Reads four real markdown sources fresh from disk on every call -- no
manifest, no sync job, no cache -- matching this project's live-only rule
(see docs/reports/2026-08-03-semantic-kernel-engineering-principles.md's
own point that this is already how ship_log.py works). Categories map
directly onto the MVP's "packet list / chronicle / engineering notes"
left-pane grouping.
"""

from __future__ import annotations

import re
from pathlib import Path

EXCERPT_CHARS = 240
LINK_PATTERN = re.compile(r"\[\[([^\]]+)\]\]")
COMPLETION_PATTERN = re.compile(r"##\s*Completion state\s*\n+\*\*([a-zA-Z \-]+)\*\*", re.IGNORECASE)
EPISTEMIC_PATTERN = re.compile(r"Epistemic label:\**\s*\**([^*\n]+)\**", re.IGNORECASE)

STATUS_NEUTRAL = "neutral"
STATUS_REFUSED = "refused"
STATUS_CONFIRMED = "confirmed"
STATUS_PROPOSAL = "proposal"
STATUS_RECONSTRUCTION = "reconstruction"
STATUS_STAGED = "staged"

STAGED_PATTERN = re.compile(r"Status:\s*\**\s*staged, awaiting evaluation", re.IGNORECASE)

SOURCES = (
    ("incoming", "docs/incoming"),
    ("query", "docs/engineering-orders/queries"),
    ("packet", "docs/engineering-orders/packets"),
    ("chronicle", "docs/reports"),
    ("notes", "docs/logs"),
    ("doctrine", "docs/doctrine"),
)

# Directory-level READMEs describe a folder's convention; they aren't
# documents in the corpus sense and clutter the list if treated as such.
SKIP_FILENAMES = {"README.md", "template-refused.md"}


def _title_from_markdown(text: str, fallback: str) -> str:
    for line in text.splitlines():
        stripped = line.strip().lstrip("#").strip()
        if stripped:
            return stripped
    return fallback


def _slug(path: Path) -> str:
    return path.stem.lower()


def _infer_status(title: str, text: str) -> str:
    """Provenance status, read from conventions this repo already uses
    (bracketed title tags, "Completion state" sections, "Epistemic
    label" lines) -- not a new schema, just naming what's already there
    so the viewer can reflect it visually."""
    if "[REFUSED]" in title.upper():
        return STATUS_REFUSED

    # Drop-box material announces itself as staged in its own header. That
    # is a real provenance state -- transported but not yet evaluated --
    # and deserves to look different from a doc that has been filed.
    if STAGED_PATTERN.search(text):
        return STATUS_STAGED

    completion = COMPLETION_PATTERN.search(text)
    if completion:
        value = completion.group(1).strip().lower()
        if "reject" in value or "refus" in value:
            return STATUS_REFUSED
        if value in ("recorded", "accepted", "active", "confirmed"):
            return STATUS_CONFIRMED

    epistemic = EPISTEMIC_PATTERN.search(text)
    if epistemic:
        value = epistemic.group(1).strip().lower()
        if any(word in value for word in ("speculative", "proposal", "design")):
            return STATUS_PROPOSAL
        if any(word in value for word in ("reconstruction", "recollection", "partial", "secondhand")):
            return STATUS_RECONSTRUCTION
        if any(word in value for word in ("direct", "verified", "canon", "confirmed")):
            return STATUS_CONFIRMED

    return STATUS_NEUTRAL


def collect(repo_root: Path) -> list[dict]:
    entries: list[dict] = []
    for category, rel_dir in SOURCES:
        directory = repo_root / rel_dir
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.md")):
            if path.name in SKIP_FILENAMES:
                continue
            try:
                text = path.read_text(encoding="utf-8")
                mtime = path.stat().st_mtime
            except OSError:
                continue
            title = _title_from_markdown(text, path.stem)
            entries.append(
                {
                    "id": f"{category}/{path.stem}",
                    "category": category,
                    "file": path.name,
                    "path": str(path.relative_to(repo_root)),
                    "title": title,
                    "mtime": mtime,
                    "excerpt": text[:EXCERPT_CHARS],
                    "content": text,
                    "links": sorted(set(LINK_PATTERN.findall(text))),
                    "status": _infer_status(title, text),
                }
            )
    entries.sort(key=lambda e: e["mtime"], reverse=True)
    return entries


def related(entries: list[dict], entry_id: str) -> list[dict]:
    """Docs that either link to entry_id's slug, or that entry_id links to."""
    by_id = {e["id"]: e for e in entries}
    target = by_id.get(entry_id)
    if not target:
        return []
    target_slug = _slug(Path(target["file"]))
    out = []
    seen = set()
    for e in entries:
        if e["id"] == entry_id:
            continue
        e_slug = _slug(Path(e["file"]))
        linked_by_target = any(_norm(link) == e_slug or _norm(link) in e["title"].lower() for link in target["links"])
        links_to_target = any(_norm(link) == target_slug or _norm(link) in target["title"].lower() for link in e["links"])
        if linked_by_target or links_to_target:
            if e["id"] not in seen:
                seen.add(e["id"])
                out.append({"id": e["id"], "title": e["title"], "category": e["category"]})
    return out


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
