#!/usr/bin/env python3
"""Minimal native Google Drive/Docs bridge for MONAD HEART.

Requires Google Cloud ADC authorized for Drive + Docs scopes.  No provider
model is involved; the bridge talks directly to the Google APIs.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

HEART_ID = "1ttkvgyLRJlrQToPhYji2oF8ef1hiNkdtEM8p1w-uifA"
DRIVE_EXPORT = "https://www.googleapis.com/drive/v3/files/{}/export?{}"
DOCS_GET = "https://docs.googleapis.com/v1/documents/{}"
DOCS_BATCH = "https://docs.googleapis.com/v1/documents/{}:batchUpdate"


def token() -> str:
    try:
        return subprocess.check_output(
            ["gcloud", "auth", "application-default", "print-access-token"],
            text=True, stderr=subprocess.STDOUT,
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise SystemExit("Google ADC unavailable; run install-gcloud-and-authorize.sh") from exc


def request(url: str, method: str = "GET", body: dict | None = None):
    req = urllib.request.Request(url, method=method)
    req.add_header("Authorization", f"Bearer {token()}")
    if body is not None:
        req.add_header("Content-Type", "application/json")
        req.data = json.dumps(body).encode()
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            raw = response.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        raise SystemExit(f"Google API HTTP {exc.code}: {detail}") from exc


def read_heart() -> str:
    url = DRIVE_EXPORT.format(HEART_ID, urllib.parse.urlencode({"mimeType": "text/plain"}))
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token()}")
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return response.read().decode("utf-8-sig")
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"Drive export HTTP {exc.code}: {exc.read().decode(errors='replace')}") from exc


def append_heart(text: str) -> None:
    if not text.strip():
        raise SystemExit("append text must not be empty")
    document = request(DOCS_GET.format(HEART_ID))
    end_index = document.get("body", {}).get("content", [])[-1].get("endIndex")
    if not isinstance(end_index, int) or end_index < 2:
        raise SystemExit("could not determine HEART document end index")
    request(DOCS_BATCH.format(HEART_ID), "POST", {
        "requests": [{"insertText": {"location": {"index": end_index - 1}, "text": "\n\n" + text.strip() + "\n"}}]
    })


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("read")
    append = sub.add_parser("append")
    append.add_argument("text")
    verify = sub.add_parser("verify")
    verify.add_argument("text")
    args = parser.parse_args()
    if args.command == "read":
        print(read_heart(), end="")
    elif args.command == "append":
        append_heart(args.text)
        print("HEART append completed; run verify with the same text.")
    elif args.command == "verify":
        content = read_heart()
        if args.text not in content:
            raise SystemExit("HEART read-back verification failed: marker not found")
        print("HEART read-back verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
