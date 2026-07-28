#!/usr/bin/env python3
"""Validate a phone-uploaded image and move it into Monad's private intake."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
INTAKE_ROOT = REPO_ROOT / "data" / "image-intake"
INCOMING = INTAKE_ROOT / "incoming"
PENDING = INTAKE_ROOT / "pending"
MAX_BYTES = 25 * 1024 * 1024
SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,199}$")


def detect_format(data: bytes) -> tuple[str, str] | None:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png", "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg", "image/jpeg"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp", "image/webp"
    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Receive one private image upload.")
    parser.add_argument("--incoming-name", required=True)
    parser.add_argument("--source", default="ChatGPT phone download")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not SAFE_NAME.fullmatch(args.incoming_name):
        print("invalid incoming filename", file=sys.stderr)
        return 2

    source_path = INCOMING / args.incoming_name
    if not source_path.is_file():
        print(f"incoming file not found: {source_path}", file=sys.stderr)
        return 2

    size = source_path.stat().st_size
    if size == 0 or size > MAX_BYTES:
        print(f"invalid image size: {size} bytes", file=sys.stderr)
        return 2

    with source_path.open("rb") as handle:
        header = handle.read(16)
    detected = detect_format(header)
    if detected is None:
        print("unsupported image content; expected PNG, JPEG, or WebP", file=sys.stderr)
        return 2

    suffix, media_type = detected
    digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
    recorded_at = dt.datetime.now(dt.timezone.utc)
    asset_id = f"{recorded_at:%Y%m%dT%H%M%SZ}-{digest[:12]}"
    PENDING.mkdir(parents=True, exist_ok=True)
    destination = PENDING / f"{asset_id}{suffix}"
    sidecar = PENDING / f"{asset_id}.json"

    if destination.exists() or sidecar.exists():
        print("refusing to overwrite an existing intake artifact", file=sys.stderr)
        return 2

    shutil.move(str(source_path), destination)
    metadata = {
        "asset_id": asset_id,
        "recorded_at": recorded_at.isoformat(),
        "source": args.source,
        "original_upload_name": args.incoming_name,
        "media_type": media_type,
        "size_bytes": size,
        "sha256": digest,
        "status": "pending human review; not public; not canon",
        "path": str(destination.relative_to(REPO_ROOT)),
    }
    sidecar.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(metadata))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
