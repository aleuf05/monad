#!/usr/bin/env python3
"""Narrow GLB-only intake for the Mike rocketry phone bridge."""

import argparse
import hashlib
import json
import os
import re
import struct
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

MAX_BYTES = 30 * 1024 * 1024
ROOT = Path(__file__).resolve().parents[2]
INTAKE = ROOT / "data" / "mike-rocketry-intake"


def validate_glb(data: bytes) -> dict:
    if len(data) < 20 or data[:4] != b"glTF":
        raise ValueError("not a binary glTF/GLB file")
    version, declared_length = struct.unpack_from("<II", data, 4)
    if version != 2 or declared_length != len(data):
        raise ValueError("invalid GLB version or declared length")
    json_length, json_type = struct.unpack_from("<II", data, 12)
    if json_type != 0x4E4F534A or 20 + json_length > len(data):
        raise ValueError("missing or invalid GLB JSON chunk")
    document = json.loads(data[20:20 + json_length].decode("utf-8").rstrip(" \x00"))
    primitives = sum(
        len(mesh.get("primitives", []))
        for mesh in document.get("meshes", [])
        if isinstance(mesh, dict)
    )
    if primitives < 1:
        raise ValueError("GLB contains no mesh primitives")
    return {"meshes": len(document.get("meshes", [])), "primitives": primitives}


def multipart_file(body: bytes, content_type: str) -> tuple[str, bytes]:
    match = re.search(r"boundary=(?:\"([^\"]+)\"|([^;]+))", content_type)
    if not match:
        raise ValueError("expected multipart/form-data")
    boundary = (match.group(1) or match.group(2)).encode()
    for part in body.split(b"--" + boundary):
        if b' name="file"' not in part:
            continue
        header_end = part.find(b"\r\n\r\n")
        if header_end < 0:
            continue
        headers = part[:header_end].decode("utf-8", "replace")
        name_match = re.search(r'filename="([^"]+)"', headers)
        if not name_match:
            continue
        return os.path.basename(name_match.group(1)), part[header_end + 4:].rstrip(b"\r\n")
    raise ValueError("no file field found")


class Handler(BaseHTTPRequestHandler):
    def reply(self, status: int, payload: dict) -> None:
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/health":
            self.reply(200, {"ok": True, "service": "mike-rocketry-glb-intake", "max_bytes": MAX_BYTES})
        else:
            self.reply(404, {"ok": False, "error": "not found"})

    def do_POST(self):
        if self.path != "/upload":
            return self.reply(404, {"ok": False, "error": "not found"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > MAX_BYTES + 8192:
                return self.reply(413, {"ok": False, "error": "GLB must be 30 MB or smaller"})
            filename, data = multipart_file(
                self.rfile.read(length),
                self.headers.get("Content-Type", ""),
            )
            if not filename.lower().endswith(".glb"):
                raise ValueError("only .glb files are accepted")
            details = validate_glb(data)
            digest = hashlib.sha256(data).hexdigest()
            INTAKE.mkdir(parents=True, exist_ok=True)
            stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
            stored_name = f"{stamp}-{digest[:12]}.glb"
            path = INTAKE / stored_name
            path.write_bytes(data)
            receipt = {
                "schema": "monad.mikeRockeryGlbIntake.v1",
                "received_at": stamp,
                "original_name": filename,
                "stored_name": stored_name,
                "sha256": digest,
                "bytes": len(data),
                "validation": details,
                "status": "quarantined-review-required",
            }
            path.with_suffix(".json").write_text(json.dumps(receipt, indent=2) + "\n")
            self.reply(201, {"ok": True, "receipt": receipt})
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            self.reply(400, {"ok": False, "error": str(exc)})

    def log_message(self, fmt, *args):
        print(f"[mike-glb-intake] {self.address_string()} {fmt % args}", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4789)
    args = parser.parse_args()
    ThreadingHTTPServer((args.host, args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
