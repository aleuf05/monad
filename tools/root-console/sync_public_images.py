#!/usr/bin/env python3
"""Sync the Captain's most recent Codex-generated images to the public site.

Source of truth is ~/.codex/generated_images/<session>/<file>, the same
directory tools/root-console/generated_images.py serves (password-gated) into
the private console. This script copies the newest N of those images into
web/captain-images/ -- plain static files Caddy already serves from web/ --
and writes web/data/captain-images.json so the public front page can render
a gallery with no backend involved. Old copies outside the newest N are
pruned so the folder doesn't grow without bound.
"""

from __future__ import annotations

import datetime
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = Path.home() / ".codex" / "generated_images"
DEST_DIR = REPO_ROOT / "web" / "captain-images"
MANIFEST_PATH = REPO_ROOT / "web" / "data" / "captain-images.json"
IMAGE_SUFFIXES = {".avif", ".gif", ".jpeg", ".jpg", ".png", ".webp"}
KEEP_COUNT = 24


def newest_source_images(limit: int) -> list[Path]:
    if not SOURCE_DIR.is_dir():
        return []
    candidates = [
        path
        for path in SOURCE_DIR.glob("*/*")
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    ]
    candidates.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    return candidates[:limit]


def dest_name(source: Path) -> str:
    session = source.parent.name
    return f"{session}-{source.name}"


def sync() -> dict:
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    sources = newest_source_images(KEEP_COUNT)
    wanted_names = {dest_name(path) for path in sources}

    for existing in DEST_DIR.iterdir():
        if existing.is_file() and existing.name not in wanted_names:
            existing.unlink()

    manifest_images = []
    for source in sources:
        name = dest_name(source)
        dest = DEST_DIR / name
        if not dest.exists() or dest.stat().st_mtime < source.stat().st_mtime:
            dest.write_bytes(source.read_bytes())
            os.utime(dest, (source.stat().st_atime, source.stat().st_mtime))
        mtime = source.stat().st_mtime
        manifest_images.append(
            {
                "file": name,
                "url": f"/captain-images/{name}",
                "generated_at": datetime.datetime.fromtimestamp(
                    mtime, tz=datetime.timezone.utc
                ).isoformat().replace("+00:00", "Z"),
            }
        )

    manifest = {
        "schema_version": "monad.captainImages.v1",
        "synced_at": datetime.datetime.now(tz=datetime.timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        "images": manifest_images,
    }
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = MANIFEST_PATH.with_suffix(".json.tmp")
    with tmp_path.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp_path, MANIFEST_PATH)
    return manifest


if __name__ == "__main__":
    result = sync()
    print(f"synced {len(result['images'])} image(s) to {DEST_DIR}", file=sys.stderr)
