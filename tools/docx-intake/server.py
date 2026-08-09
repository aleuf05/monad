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


def _cell_text(cell: ET.Element) -> str:
    pieces = [_paragraph_to_markdown(p).lstrip("# ").lstrip("- ") for p in cell.iter(W + "p")]
    # A pipe inside a cell would otherwise split the markdown row.
    return " ".join(piece for piece in pieces if piece).replace("|", "\\|")


def _table_to_markdown(table: ET.Element) -> list[str]:
    """Render a Word table as a markdown table.

    Worth doing rather than flattening: the first real document through this
    box (MSIR-CORE-001) carries its whole token vocabulary as a table, and
    one-cell-per-line destroys exactly the structure that made it a table.
    """
    rows: list[list[str]] = []
    for row in table.findall(W + "tr"):
        cells = [_cell_text(cell) for cell in row.findall(W + "tc")]
        if any(cells):
            rows.append(cells)
    if not rows:
        return []

    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    header, body = rows[0], rows[1:]
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join([" --- "] * width) + "|"]
    lines.extend("| " + " | ".join(r) + " |" for r in body)
    return lines


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
    body = root.find(W + "body")
    if body is None:
        body = root

    # Walk the body in document order rather than iter()-ing every <w:p>:
    # paragraphs inside table cells must be consumed by the table renderer,
    # not emitted a second time as loose lines.
    # Blocks, not lines: blocks are joined with a blank line between them,
    # so a whole table has to be one block or its rows get split apart.
    blocks: list[str] = []
    for node in body:
        if node.tag == W + "p":
            blocks.append(_paragraph_to_markdown(node))
        elif node.tag == W + "tbl":
            table = _table_to_markdown(node)
            if table:
                blocks.append("\n".join(table))

    return "\n\n".join(block for block in blocks if block) + "\n"


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
        # Nothing new to commit, but the tray isn't empty -- these were
        # committed by an earlier run. They are already safe in history, so
        # the honest action is to finish the job and clear, not to report a
        # failure at a tray the operator can plainly see has files in it.
        head = _git("rev-parse", "--short", "HEAD").stdout.strip()
        cleared = _clear_committed(head)
        return {
            "ok": not cleared.get("error"),
            "committed": False,
            "already_committed": True,
            "commit": head,
            "branch": _git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip(),
            "count": len(pending),
            "auto_cleared": cleared,
            "error": cleared.get("error"),
        }

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

    # Push confirmed -- only now is it safe to empty the tray, because the
    # packets exist on the remote and not merely on this disk. The clear is
    # itself committed and pushed rather than left as a working-tree
    # deletion: a tray emptied by `rm` would leave the repo permanently
    # showing pending deletes of files that are still in HEAD.
    cleared = _clear_committed(head)

    return {
        "ok": True,
        "committed": True,
        "pushed": True,
        "commit": head,
        "branch": branch,
        "count": len(pending),
        "auto_cleared": cleared,
    }


def _clear_committed(source_commit: str) -> dict:
    """Remove the staging tray in git, after its contents are safely pushed."""
    paths = [str(p.relative_to(REPO_ROOT)) for p in _staged_files()]
    if ORIGINALS_DIR.is_dir():
        paths += [str(p.relative_to(REPO_ROOT)) for p in sorted(ORIGINALS_DIR.glob("*.docx"))]
    if not paths:
        return {"cleared": 0}

    removed = _git("rm", "--quiet", "--", *paths)
    if removed.returncode != 0:
        return {"cleared": 0, "error": f"git rm failed: {removed.stderr.strip()}"}

    message = (
        f"Clear staging tray ({len(paths)} file(s))\n\n"
        f"Contents committed and pushed in {source_commit}; the tray is a\n"
        "landing zone, not storage. History keeps the packets."
    )
    commit = _git("commit", "-m", message)
    if commit.returncode != 0:
        return {"cleared": 0, "error": f"clear commit failed: {commit.stderr.strip()}"}

    clear_head = _git("rev-parse", "--short", "HEAD").stdout.strip()
    push = _git("push", "origin", "HEAD")
    return {
        "cleared": len(paths),
        "commit": clear_head,
        "pushed": push.returncode == 0,
        "error": None if push.returncode == 0 else f"cleared in {clear_head} but push failed",
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
        for path in sorted(_staged_files(), reverse=True)[:10]:
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
