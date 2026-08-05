#!/usr/bin/env python3
"""Public, unauthenticated, always-on live view of Captain-generated images.

No sync step, no copy into web/, no manifest file, no cron job. Every
GET /api/images call globs ~/.codex/generated_images fresh at that exact
instant; every GET /api/images/<token> streams the image bytes live from
that same source directory. Reuses generated_images.py's token scheme
(the same one root-console.service's authenticated endpoint uses) purely
for safe path resolution -- these images are already public via the
Captain's Images gallery, so serving them live carries no new exposure.
"""

from __future__ import annotations

import datetime
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))
from generated_images import (  # noqa: E402
    GENERATED_IMAGE_DIR,
    GeneratedImageError,
    generated_image_token,
    resolve_generated_image,
)

HOST = "127.0.0.1"
PORT = 4795
IMAGE_SUFFIXES = {".avif", ".gif", ".jpeg", ".jpg", ".png", ".webp"}
KEEP_COUNT = 24
API_PREFIX = "/api/images/"


def _live_image_list() -> list[dict]:
    if not GENERATED_IMAGE_DIR.is_dir():
        return []
    candidates = [
        path
        for path in GENERATED_IMAGE_DIR.glob("*/*")
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    ]
    candidates.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    entries = []
    for path in candidates[:KEEP_COUNT]:
        try:
            token = generated_image_token(path)
        except GeneratedImageError:
            continue
        mtime = path.stat().st_mtime
        entries.append(
            {
                "file": path.name,
                "url": f"/public-images-api{API_PREFIX}{token}",
                "generated_at": datetime.datetime.fromtimestamp(
                    mtime, tz=datetime.timezone.utc
                ).isoformat().replace("+00:00", "Z"),
            }
        )
    return entries


class PublicImagesHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:  # noqa: A002
        sys.stderr.write("%s - %s\n" % (self.address_string(), format % args))

    def do_GET(self) -> None:  # noqa: N802
        path = urlsplit(self.path).path
        if path == "/api/images":
            body = json.dumps({"images": _live_image_list()}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path.startswith(API_PREFIX):
            token = path[len(API_PREFIX):]
            try:
                image_path, content_type, size = resolve_generated_image(token)
            except FileNotFoundError:
                self.send_error(404)
                return
            except (GeneratedImageError, OSError):
                self.send_error(400)
                return
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(size))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            with image_path.open("rb") as image_file:
                while chunk := image_file.read(64 * 1024):
                    self.wfile.write(chunk)
            return
        self.send_error(404)


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), PublicImagesHandler)
    print(f"public-images-api listening on {HOST}:{PORT}", file=sys.stderr)
    server.serve_forever()


if __name__ == "__main__":
    main()
