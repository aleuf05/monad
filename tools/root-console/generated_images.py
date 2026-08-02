"""Shared generated-image trust-boundary mapping for browser event streams."""

from __future__ import annotations

import base64
import binascii
from pathlib import Path


GENERATED_IMAGE_DIR = Path.home() / ".codex" / "generated_images"
GENERATED_IMAGE_API_PREFIX = "/root-console-api/api/generated-image/"
MAX_GENERATED_IMAGE_BYTES = 25 * 1024 * 1024
IMAGE_TYPES = {
    ".avif": "image/avif",
    ".gif": "image/gif",
    ".jpeg": "image/jpeg",
    ".jpg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


class GeneratedImageError(ValueError):
    """A generated-image reference did not cross the browser trust boundary."""


def generated_image_token(path: Path) -> str:
    root = GENERATED_IMAGE_DIR.resolve()
    try:
        relative = path.resolve().relative_to(root)
    except ValueError as exc:
        raise GeneratedImageError("image is outside the generated-image store") from exc
    encoded = base64.urlsafe_b64encode(relative.as_posix().encode("utf-8")).decode("ascii")
    return encoded.rstrip("=")


def resolve_generated_image(token: str) -> tuple[Path, str, int]:
    if not token or len(token) > 2048:
        raise GeneratedImageError("invalid image artifact id")
    try:
        padding = "=" * (-len(token) % 4)
        relative_text = base64.b64decode(
            token + padding, altchars=b"-_", validate=True
        ).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError) as exc:
        raise GeneratedImageError("invalid image artifact id") from exc
    relative = Path(relative_text)
    if relative.is_absolute() or ".." in relative.parts:
        raise GeneratedImageError("invalid image artifact id")
    root = GENERATED_IMAGE_DIR.resolve()
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise GeneratedImageError("image is outside the generated-image store") from exc
    if not candidate.is_file():
        raise FileNotFoundError("generated image not found")
    content_type = IMAGE_TYPES.get(candidate.suffix.lower())
    if not content_type:
        raise GeneratedImageError("unsupported generated-image type")
    size = candidate.stat().st_size
    if size <= 0 or size > MAX_GENERATED_IMAGE_BYTES:
        raise GeneratedImageError("generated image has an invalid size")
    return candidate, content_type, size


def browser_generated_image_url(value: str) -> str | None:
    raw = value[7:] if value.startswith("file://") else value
    if not raw.startswith("/"):
        return None
    try:
        token = generated_image_token(Path(raw))
        resolve_generated_image(token)
    except (GeneratedImageError, FileNotFoundError, OSError):
        return None
    return GENERATED_IMAGE_API_PREFIX + token


def map_generated_images(value, depth: int = 0):
    """Copy an event while mapping exact local image artifact strings."""
    if depth > 12:
        return value
    if isinstance(value, str):
        return browser_generated_image_url(value) or value
    if isinstance(value, list):
        return [map_generated_images(item, depth + 1) for item in value]
    if isinstance(value, dict):
        return {key: map_generated_images(item, depth + 1) for key, item in value.items()}
    return value
