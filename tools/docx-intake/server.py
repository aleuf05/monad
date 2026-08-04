#!/usr/bin/env python3
"""Drop a .docx packet onto the Root Console and have its text land in the repo.

Why this exists: packets have been arriving as pasted chat text, which is
fine for short ones and miserable for long formatted documents. This gives
the Operator a box to drop a .docx into -- from an iPhone (Files / iCloud
Drive / "Browse" sheet) or from a Mac (drag-and-drop straight onto the
panel) -- and get the text extracted into the repo without SSH, scp, or
retyping.

Transport, not filing. An upload lands in docs/incoming/ as *staged*
material and nothing more: the extracted markdown carries an explicit
"awaiting evaluation" header, and it does not become a captain's log entry
or canonical doctrine until it has actually been read and filed under
docs/doctrine/012-documentarian-packet-scheme.md. The drop box replaces
copy-paste, not judgment.

No password prompt of its own: Caddy gates /docx-intake-api/* with the
same forward_auth check that already guards the console page, so anyone
who can see the panel is already authorized. Adding a second password
here would be friction without a threat model.

Extraction is stdlib-only (zipfile + ElementTree). A .docx is a zip with
the real content in word/document.xml; there is no pandoc or python-docx
on this host and none is needed. Headings and list items survive as
markdown so a "core doc" arrives readable rather than as one wall of text.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
import xml.etree.ElementTree as ET
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

HOST = "127.0.0.1"
PORT = 4797

REPO_ROOT = Path(__file__).resolve().parents[2]
INCOMING_DIR = REPO_ROOT / "docs" / "incoming"
ORIGINALS_DIR = INCOMING_DIR / "docx"

MAX_UPLOAD_BYTES = 25 * 1024 * 1024
# Decompressed ceiling for the one XML part we read, so a zip bomb can't
# turn a small upload into gigabytes of parsed text.
MAX_DOCUMENT_XML_BYTES = 40 * 1024 * 1024
ZIP_MAGIC = b"PK\x03\x04"
DOCUMENT_PART = "word/document.xml"

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _slugify(name: str) -> str:
    stem = Path(name).stem.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", stem).strip("-")
    return (slug or "packet")[:60]


def _paragraph_to_markdown(para: ET.Element) -> str:
    pieces: list[str] = []
    for node in para.iter():
        if node.tag == W + "t":
            pieces.append(node.text or "")
        elif node.tag == W + "tab":
            pieces.append("\t")
        elif node.tag == W + "br":
            pieces.append("\n")
    text = "".join(pieces).strip()
    if not text:
        return ""

    style_node = para.find(f"./{W}pPr/{W}pStyle")
    style = (style_node.get(W + "val") or "") if style_node is not None else ""
    heading = re.match(r"(?:Heading|heading)(\d)", style)
    if heading:
        level = min(int(heading.group(1)), 6)
        return f"{'#' * level} {text}"
    if style in ("Title",):
        return f"# {text}"

    if para.find(f"./{W}pPr/{W}numPr") is not None:
        return f"- {text}"
    return text


def extract_markdown(docx_bytes: bytes) -> str:
    with zipfile.ZipFile(BytesIO(docx_bytes)) as archive:
        try:
            info = archive.getinfo(DOCUMENT_PART)
        except KeyError:
            raise ValueError("not a Word document (no word/document.xml inside)")
        if info.file_size > MAX_DOCUMENT_XML_BYTES:
            raise ValueError("document content is implausibly large; refusing to expand it")
        xml_bytes = archive.read(DOCUMENT_PART)

    root = ET.fromstring(xml_bytes)
    lines: list[str] = []
    for para in root.iter(W + "p"):
        lines.append(_paragraph_to_markdown(para))

    # Collapse runs of blank lines to a single blank line: Word emits a lot
    # of empty paragraphs that mean nothing once the text is markdown.
    out: list[str] = []
    for line in lines:
        if not line and out and not out[-1]:
            continue
        out.append(line)
    return "\n\n".join(l for l in out if l) + "\n"


def _git(*args: str, timeout: int = 90) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _staged_files() -> list[Path]:
    if not INCOMING_DIR.is_dir():
        return []
    return sorted(p for p in INCOMING_DIR.glob("*.md") if p.name != "README.md")


def commit_and_push() -> dict:
    """Stage, commit, and push docs/incoming only.

    Deliberately scoped with an explicit pathspec rather than `git add -A`:
    the working tree routinely carries unrelated in-progress edits, and a
    button on a web panel must never sweep those into a commit the operator
    didn't look at.
    """
    pending = _staged_files()
    if not pending:
        return {"ok": False, "error": "nothing staged to commit"}

    add = _git("add", "--", str(INCOMING_DIR.relative_to(REPO_ROOT)))
    if add.returncode != 0:
        return {"ok": False, "error": f"git add failed: {add.stderr.strip()}"}

    status = _git("status", "--porcelain", "--", str(INCOMING_DIR.relative_to(REPO_ROOT)))
    if not status.stdout.strip():
        return {"ok": False, "error": "no changes in docs/incoming to commit"}

    names = ", ".join(p.name for p in pending[:5])
    if len(pending) > 5:
        names += f", +{len(pending) - 5} more"
    message = (
        f"Stage {len(pending)} incoming packet(s) from Root Console drop box\n\n"
        f"{names}\n\n"
        "Staged material only -- transported into the repo, not yet evaluated\n"
        "or filed per docs/doctrine/012-documentarian-packet-scheme.md."
    )
    commit = _git("commit", "-m", message)
    if commit.returncode != 0:
        return {"ok": False, "error": f"git commit failed: {commit.stderr.strip() or commit.stdout.strip()}"}

    head = _git("rev-parse", "--short", "HEAD").stdout.strip()
    branch = _git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()

    push = _git("push", "origin", "HEAD")
    if push.returncode != 0:
        return {
            "ok": False,
            "committed": True,
            "commit": head,
            "branch": branch,
            "error": f"committed {head} but push failed: {push.stderr.strip()}",
        }

    return {
        "ok": True,
        "committed": True,
        "pushed": True,
        "commit": head,
        "branch": branch,
        "count": len(pending),
    }


def clear_staged() -> dict:
    """Delete staged extracts and their originals.

    Only touches files this drop box created. Anything already committed
    stays in git history; this clears the staging tray, it does not rewrite
    what was pushed.
    """
    removed = 0
    for path in _staged_files():
        path.unlink()
        removed += 1
    if ORIGINALS_DIR.is_dir():
        for path in ORIGINALS_DIR.glob("*.docx"):
            path.unlink()
    return {"ok": True, "removed": removed}


def _parse_multipart(body: bytes, boundary: bytes) -> dict[str, dict]:
    parts: dict[str, dict] = {}
    delimiter = b"--" + boundary
    for chunk in body.split(delimiter):
        chunk = chunk.strip(b"\r\n")
        if not chunk or chunk == b"--":
            continue
        header_blob, _, content = chunk.partition(b"\r\n\r\n")
        if not content:
            continue
        content = content[:-2] if content.endswith(b"\r\n") else content
        headers = header_blob.decode("utf-8", "replace")
        name = None
        filename = None
        for line in headers.split("\r\n"):
            if line.lower().startswith("content-disposition:"):
                for piece in line.split(";"):
                    piece = piece.strip()
                    if piece.startswith("name="):
                        name = piece.split("=", 1)[1].strip('"')
                    elif piece.startswith("filename="):
                        filename = piece.split("=", 1)[1].strip('"')
        if name:
            parts[name] = {"filename": filename, "content": content}
    return parts


class Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        path = urlparse(self.path).path

        if path == "/api/commit":
            try:
                result = commit_and_push()
            except subprocess.TimeoutExpired:
                result = {"ok": False, "error": "git operation timed out"}
            self._json(200 if result.get("ok") else 400, result)
            return

        if path == "/api/clear":
            self._json(200, clear_staged())
            return

        if path != "/api/upload":
            self._json(404, {"ok": False, "error": "not found"})
            return

        length = int(self.headers.get("Content-Length", 0))
        if length <= 0 or length > MAX_UPLOAD_BYTES:
            self._json(413, {"ok": False, "error": f"file must be under {MAX_UPLOAD_BYTES // (1024*1024)}MB"})
            return

        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type or "boundary=" not in content_type:
            self._json(400, {"ok": False, "error": "expected multipart/form-data"})
            return
        boundary = content_type.split("boundary=", 1)[1].strip().strip('"').encode("utf-8")

        parts = _parse_multipart(self.rfile.read(length), boundary)
        upload = parts.get("file")
        if not upload or not upload["content"]:
            self._json(400, {"ok": False, "error": "no file provided"})
            return

        data = upload["content"]
        original_name = upload.get("filename") or "packet.docx"
        if data[:4] != ZIP_MAGIC:
            self._json(400, {"ok": False, "error": "not a .docx file (expected a Word document)"})
            return

        try:
            markdown = extract_markdown(data)
        except (zipfile.BadZipFile, ET.ParseError):
            self._json(400, {"ok": False, "error": "file is a zip but not readable as a Word document"})
            return
        except ValueError as error:
            self._json(400, {"ok": False, "error": str(error)})
            return

        if not markdown.strip():
            self._json(400, {"ok": False, "error": "document parsed but contained no text"})
            return

        stamp = time.strftime("%Y-%m-%d_%H%M%S")
        slug = _slugify(original_name)
        ORIGINALS_DIR.mkdir(parents=True, exist_ok=True)

        docx_path = ORIGINALS_DIR / f"{stamp}_{slug}.docx"
        md_path = INCOMING_DIR / f"{stamp}_{slug}.md"

        docx_path.write_bytes(data)
        md_path.write_text(
            f"# Incoming packet — {original_name}\n\n"
            f"Dropped: {time.strftime('%Y-%m-%d %H:%M:%S %Z')}\n"
            f"Source: Root Console .docx drop box\n"
            f"Original: `{docx_path.relative_to(REPO_ROOT)}`\n"
            f"Status: **staged, awaiting evaluation** — not yet filed as a\n"
            f"captain's log entry or canonical doctrine.\n\n"
            f"---\n\n"
            f"{markdown}",
            encoding="utf-8",
        )

        words = len(markdown.split())
        self._json(200, {
            "ok": True,
            "original": original_name,
            "markdown_path": str(md_path.relative_to(REPO_ROOT)),
            "docx_path": str(docx_path.relative_to(REPO_ROOT)),
            "words": words,
            "preview": markdown[:400],
            "dropped_at": int(time.time()),
        })

    def do_GET(self) -> None:
        if urlparse(self.path).path != "/api/recent":
            self._json(404, {"ok": False, "error": "not found"})
            return
        entries = []
        if INCOMING_DIR.is_dir():
            for path in sorted(INCOMING_DIR.glob("*.md"), reverse=True)[:10]:
                stat = path.stat()
                entries.append({
                    "name": path.name,
                    "path": str(path.relative_to(REPO_ROOT)),
                    "bytes": stat.st_size,
                    "mtime": int(stat.st_mtime),
                })
        self._json(200, {"ok": True, "entries": entries})

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args) -> None:  # noqa: A002
        pass


class Server(ThreadingHTTPServer):
    daemon_threads = True


def main() -> int:
    INCOMING_DIR.mkdir(parents=True, exist_ok=True)
    server = Server((HOST, PORT), Handler)
    print(f"docx-intake listening on http://{HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
