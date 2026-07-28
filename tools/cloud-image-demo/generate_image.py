#!/usr/bin/env python3
"""Generate one OpenAI image and save it with a provenance sidecar.

The default destination is outside Monad's live ``web/`` tree. Writing under
``web/`` requires the explicit ``--allow-live-target`` flag.
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.request


REPO_ROOT = Path(__file__).resolve().parents[2]
LIVE_ROOT = (REPO_ROOT / "web").resolve()
DEFAULT_OUTPUT = REPO_ROOT / "artifacts" / "cloud-image-demo" / "monad-actual.png"
API_URL = "https://api.openai.com/v1/images/generations"


def is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a cloud image and preserve prompt provenance."
    )
    parser.add_argument("--prompt-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--model", default="gpt-image-2")
    parser.add_argument("--size", default="1536x1024")
    parser.add_argument("--quality", choices=("low", "medium", "high"), default="low")
    parser.add_argument(
        "--allow-live-target",
        action="store_true",
        help="Allow output under web/. Requires separate production authorization.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = args.output.expanduser()
    if not output.is_absolute():
        output = REPO_ROOT / output
    output = output.resolve()

    if is_within(output, LIVE_ROOT) and not args.allow_live_target:
        print(
            "refusing live target: pass --allow-live-target only after production approval",
            file=sys.stderr,
        )
        return 2

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY is not set", file=sys.stderr)
        return 2

    prompt_path = args.prompt_file.expanduser().resolve()
    prompt = prompt_path.read_text(encoding="utf-8").strip()
    if not prompt:
        print("prompt file is empty", file=sys.stderr)
        return 2

    body = json.dumps(
        {
            "model": args.model,
            "prompt": prompt,
            "size": args.size,
            "quality": args.quality,
            "output_format": "png",
            "n": 1,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        API_URL,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            payload = json.load(response)
            request_id = response.headers.get("x-request-id")
    except urllib.error.HTTPError as error:
        error_body = error.read().decode("utf-8", errors="replace")
        print(f"OpenAI API returned HTTP {error.code}: {error_body}", file=sys.stderr)
        return 1
    except (urllib.error.URLError, TimeoutError) as error:
        print(f"OpenAI API request failed: {error}", file=sys.stderr)
        return 1

    try:
        image_bytes = base64.b64decode(payload["data"][0]["b64_json"], validate=True)
    except (KeyError, IndexError, TypeError, ValueError) as error:
        print(f"OpenAI API response did not contain a valid image: {error}", file=sys.stderr)
        return 1

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_bytes(image_bytes)
    temporary.replace(output)

    digest = hashlib.sha256(image_bytes).hexdigest()
    metadata = {
        "recorded_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source": "OpenAI Image API",
        "endpoint": API_URL,
        "model": args.model,
        "size": args.size,
        "quality": args.quality,
        "prompt_file": str(prompt_path.relative_to(REPO_ROOT)),
        "output_file": str(output.relative_to(REPO_ROOT)),
        "sha256": digest,
        "request_id": request_id,
        "status": "generated artifact; not evidence of live publication",
    }
    sidecar = output.with_suffix(output.suffix + ".json")
    sidecar.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"output": str(output), "sidecar": str(sidecar), "sha256": digest}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
