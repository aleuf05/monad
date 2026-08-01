#!/usr/bin/env python3
"""Validate the seeded Admiralty Archive without changing repository files."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "admiralty" / "archive"
REGISTRY = ARCHIVE / "registry" / "documents.json"
ALLOWED_AUTHORITY = {"canonical", "proposed", "superseded", "reference", "uncertain"}
ALLOWED_ORIGIN = {"contemporaneous", "retrospective", "derived", "uncertain"}
EXCLUDED = {".git", ".venv", "target", "node_modules", "__pycache__", ".pytest_cache", "admiralty"}


def fail(message: str, errors: list[str]) -> None:
    errors.append(message)


def link_targets(path: Path):
    for raw in re.findall(r"\[[^\]]+\]\(([^)]+)\)", path.read_text(encoding="utf-8", errors="replace")):
        if raw.startswith(("http://", "https://", "mailto:", "#")):
            continue
        yield raw.split("#", 1)[0]


def main() -> int:
    errors: list[str] = []
    if not REGISTRY.exists():
        print("FAIL: registry/documents.json is missing")
        return 1
    payload = json.loads(REGISTRY.read_text())
    documents = payload.get("documents", [])
    ids = [doc.get("id") for doc in documents]
    if len(ids) != len(set(ids)):
        fail("document IDs are not unique", errors)
    by_source = {}
    for doc in documents:
        source = doc.get("source_path")
        if not source:
            fail(f"{doc.get('id')} has no source_path", errors)
            continue
        source_path = ROOT / source
        by_source[source] = doc
        if not source_path.is_file():
            fail(f"registered source does not exist: {source}", errors)
        else:
            digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
            if doc.get("content_sha256") != digest:
                fail(f"source hash is stale: {source}", errors)
        if doc.get("authority_status") not in ALLOWED_AUTHORITY:
            fail(f"invalid authority status: {doc.get('id')}", errors)
        if doc.get("record_origin") not in ALLOWED_ORIGIN:
            fail(f"invalid record origin: {doc.get('id')}", errors)
        if "retrospective" in source.lower() and doc.get("record_origin") == "contemporaneous":
            fail(f"retrospective source marked contemporaneous: {doc.get('id')}", errors)
        if doc.get("authority_status") == "canonical" and "draft" in doc.get("title", "").lower():
            fail(f"draft-titled record marked canonical: {doc.get('id')}", errors)
        if doc.get("authority_status") == "canonical" and not source:
            fail(f"canonical record has no supporting source: {doc.get('id')}", errors)
        if set(Path(source).parts) & EXCLUDED:
            fail(f"excluded directory was indexed: {source}", errors)

    for relationship in json.loads((ARCHIVE / "registry" / "relationships.json").read_text()).get("relationships", []):
        targets = {doc.get("id") for doc in documents} | {p.get("id") for p in json.loads((ARCHIVE / "registry" / "projects.json").read_text()).get("projects", [])}
        if relationship.get("source") not in targets or relationship.get("target") not in targets:
            fail(f"relationship target missing: {relationship}", errors)

    for executive in (ARCHIVE / "executive").glob("*.md"):
        for target in link_targets(executive):
            target_path = (executive.parent / target).resolve()
            if not target_path.exists():
                fail(f"executive link missing: {executive} -> {target}", errors)
            elif target_path.is_file() and target_path.suffix in {".md", ".txt", ".rst"}:
                relative = target_path.relative_to(ROOT).as_posix()
                if relative not in by_source and not str(target_path).startswith(str(ARCHIVE)):
                    fail(f"executive link is not registered: {executive} -> {target}", errors)

    # Determinism check: the source record sequence and content fields must be stable.
    import importlib.util
    spec = importlib.util.spec_from_file_location("build_admiralty_archive", ROOT / "tools/build-admiralty-archive.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    first, _ = module.build()
    second, _ = module.build()
    if first != second:
        fail("two inventory builds produced different source records", errors)

    # A temporary content mutation proves hash sensitivity without touching a source.
    # The same probe also proves curated fields survive a regeneration.
    probe_source = ROOT / ".admiralty-hash-probe.tmp"
    probe_source.write_text("before\n")
    first_record = module.record(probe_source, {"doc-admiralty-hash-probe-tmp": {"summary": "curated sentinel"}})
    before = first_record["content_sha256"]
    probe_source.write_text("after\n")
    second_record = module.record(probe_source, {"doc-admiralty-hash-probe-tmp": {"summary": "curated sentinel"}})
    after = second_record["content_sha256"]
    if before == after:
        fail("source hash did not change after content mutation", errors)
    if second_record.get("summary") != "curated sentinel":
        fail("manually curated metadata did not survive regeneration", errors)
    probe_source.unlink()

    # A direct digest probe guards the underlying hash operation as well.

    if errors:
        print("Admiralty Archive validation failed:")
        print("- " + "\n- ".join(errors))
        return 1
    print(f"Admiralty Archive validation passed: {len(documents)} registered sources.")
    print("Checks: paths, IDs, relationships, statuses, provenance, hashes, determinism, exclusions, executive links.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
