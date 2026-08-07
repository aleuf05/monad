"""Grounded retrieval for the Captain's Concept Room.

Documents and git are authoritative.  The FTS table is a disposable projection
inside the existing Live Captain SQLite database and is synchronized from the
real corpus before every query.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import subprocess
import threading
import time
from pathlib import Path

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
TOKEN_RE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]{1,}")
MAX_CHUNK_CHARS = 4800

INDEX_SCHEMA = """
CREATE TABLE IF NOT EXISTS concept_documents (
    path TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    status TEXT NOT NULL,
    mtime REAL NOT NULL,
    content_hash TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS concept_chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL,
    title TEXT NOT NULL,
    heading TEXT NOT NULL,
    category TEXT NOT NULL,
    status TEXT NOT NULL,
    ordinal INTEGER NOT NULL,
    content TEXT NOT NULL,
    content_hash TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_concept_chunks_path ON concept_chunks(path);
CREATE VIRTUAL TABLE IF NOT EXISTS concept_chunks_fts USING fts5(
    title, path, heading, content, content='concept_chunks', content_rowid='id'
);
"""


class ConceptRetrievalError(RuntimeError):
    pass


def _split_sections(text: str) -> list[tuple[str, str]]:
    matches = list(HEADING_RE.finditer(text))
    if not matches:
        return [("Document", text)]
    sections: list[tuple[str, str]] = []
    if matches[0].start() > 0 and text[: matches[0].start()].strip():
        sections.append(("Preamble", text[: matches[0].start()].strip()))
    stack: list[tuple[int, str]] = []
    for index, match in enumerate(matches):
        level = len(match.group(1))
        title = match.group(2).strip()
        while stack and stack[-1][0] >= level:
            stack.pop()
        stack.append((level, title))
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[match.end() : end].strip()
        sections.append((" / ".join(item[1] for item in stack), body or title))
    return sections


def _chunk_document(entry: dict) -> list[dict]:
    chunks: list[dict] = []
    ordinal = 0
    for heading, section in _split_sections(entry["content"]):
        paragraphs = re.split(r"\n\s*\n", section)
        current = ""
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            if current and len(current) + len(paragraph) + 2 > MAX_CHUNK_CHARS:
                chunks.append({"heading": heading, "content": current, "ordinal": ordinal})
                ordinal += 1
                current = ""
            if len(paragraph) > MAX_CHUNK_CHARS:
                if current:
                    chunks.append({"heading": heading, "content": current, "ordinal": ordinal})
                    ordinal += 1
                    current = ""
                for start in range(0, len(paragraph), MAX_CHUNK_CHARS):
                    chunks.append({
                        "heading": heading,
                        "content": paragraph[start : start + MAX_CHUNK_CHARS],
                        "ordinal": ordinal,
                    })
                    ordinal += 1
                continue
            current = f"{current}\n\n{paragraph}".strip()
        if current:
            chunks.append({"heading": heading, "content": current, "ordinal": ordinal})
            ordinal += 1
    return chunks


class ConceptEngine:
    def __init__(self, db_path: Path, repo_root: Path, corpus_module):
        self.repo_root = repo_root
        self.corpus = corpus_module
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            try:
                self._conn.executescript(INDEX_SCHEMA)
                self._conn.commit()
            except sqlite3.DatabaseError as exc:
                raise ConceptRetrievalError(f"concept index unavailable: {exc}") from exc

    def sync(self) -> dict:
        entries = self.corpus.collect(self.repo_root)
        incoming = {
            entry["path"]: (
                entry,
                hashlib.sha256(entry["content"].encode("utf-8")).hexdigest(),
            )
            for entry in entries
        }
        changed = 0
        removed = 0
        with self._lock:
            known = {
                row["path"]: row["content_hash"]
                for row in self._conn.execute(
                    "SELECT path, content_hash FROM concept_documents"
                ).fetchall()
            }
            for path in sorted(set(known) - set(incoming)):
                self._delete_document(path)
                removed += 1
            for path, (entry, digest) in incoming.items():
                if known.get(path) == digest:
                    continue
                self._delete_document(path)
                self._conn.execute(
                    "INSERT INTO concept_documents(path,title,category,status,mtime,content_hash) "
                    "VALUES(?,?,?,?,?,?)",
                    (path, entry["title"], entry["category"], entry["status"], entry["mtime"], digest),
                )
                for chunk in _chunk_document(entry):
                    cursor = self._conn.execute(
                        "INSERT INTO concept_chunks(path,title,heading,category,status,ordinal,content,content_hash) "
                        "VALUES(?,?,?,?,?,?,?,?)",
                        (path, entry["title"], chunk["heading"], entry["category"],
                         entry["status"], chunk["ordinal"], chunk["content"], digest),
                    )
                    self._conn.execute(
                        "INSERT INTO concept_chunks_fts(rowid,title,path,heading,content) VALUES(?,?,?,?,?)",
                        (cursor.lastrowid, entry["title"], path, chunk["heading"], chunk["content"]),
                    )
                changed += 1
            self._conn.commit()
            chunk_count = self._conn.execute("SELECT COUNT(*) FROM concept_chunks").fetchone()[0]
        return {"documents": len(incoming), "chunks": chunk_count, "changed": changed, "removed": removed}

    def _delete_document(self, path: str) -> None:
        rows = self._conn.execute("SELECT id FROM concept_chunks WHERE path=?", (path,)).fetchall()
        for row in rows:
            self._conn.execute("DELETE FROM concept_chunks_fts WHERE rowid=?", (row["id"],))
        self._conn.execute("DELETE FROM concept_chunks WHERE path=?", (path,))
        self._conn.execute("DELETE FROM concept_documents WHERE path=?", (path,))

    @staticmethod
    def classify(query: str) -> str:
        lowered = query.lower()
        if any(word in lowered for word in ("history", "evolve", "origin", "changed", "timeline")):
            return "history"
        if any(word in lowered for word in ("compare", "difference", "versus", " vs ")):
            return "comparison"
        if any(word in lowered for word in ("conflict", "disagree", "contradict", "tension")):
            return "conflict"
        if any(word in lowered for word in ("everything", "whole corpus", "overall", "catch me up", "brief me")):
            return "global-brief"
        return "concept"

    def retrieve(self, query: str, limit: int = 8) -> dict:
        metrics = self.sync()
        terms = []
        seen = set()
        for token in TOKEN_RE.findall(query.lower()):
            if token in seen or len(token) < 3:
                continue
            seen.add(token)
            terms.append(token)
        mode = self.classify(query)
        with self._lock:
            if terms:
                match = " OR ".join(f'"{term}"' for term in terms[:16])
                rows = self._conn.execute(
                    "SELECT c.*, bm25(concept_chunks_fts, 5.0, 1.0, 3.0, 1.0) AS score "
                    "FROM concept_chunks_fts JOIN concept_chunks c ON c.id=concept_chunks_fts.rowid "
                    "WHERE concept_chunks_fts MATCH ? ORDER BY score LIMIT ?",
                    (match, limit),
                ).fetchall()
            else:
                rows = self._conn.execute(
                    "SELECT c.*, 0.0 AS score FROM concept_chunks c "
                    "JOIN concept_documents d ON d.path=c.path ORDER BY d.mtime DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        evidence = []
        for index, row in enumerate(rows, 1):
            evidence.append({
                "id": f"S{index}", "path": row["path"], "title": row["title"],
                "heading": row["heading"], "category": row["category"],
                "status": row["status"], "content_hash": row["content_hash"],
                "excerpt": row["content"][:1800], "score": round(float(row["score"]), 4),
            })
        history = self._git_history([item["path"] for item in evidence]) if mode == "history" else []
        return {"mode": mode, "query": query, "evidence": evidence, "history": history, "index": metrics}

    def _git_history(self, paths: list[str], limit: int = 12) -> list[dict]:
        command = ["git", "log", f"-{limit}", "--format=%H%x1f%aI%x1f%s", "--name-only", "--"]
        command.extend(paths[:8] or ["docs"])
        try:
            result = subprocess.run(command, cwd=self.repo_root, check=True, capture_output=True, text=True, timeout=10)
        except (OSError, subprocess.SubprocessError):
            return []
        events = []
        current = None
        for line in result.stdout.splitlines():
            if "\x1f" in line:
                digest, authored, subject = line.split("\x1f", 2)
                current = {"commit": digest, "authored_at": authored, "subject": subject, "paths": []}
                events.append(current)
            elif line.strip() and current is not None:
                current["paths"].append(line.strip())
        return events

    def close(self) -> None:
        with self._lock:
            self._conn.close()


def compile_concept_prompt(
    captain_kernel: str,
    current_bearing: str,
    room: dict,
    turns: list[dict],
    query: str,
    retrieval: dict,
) -> str:
    transcript = "\n\n".join(
        f"{'Admiral' if turn['role'] == 'admiral' else 'Captain'}: {turn['text']}"
        for turn in turns[-12:]
    ) or "(new room)"
    sources = "\n\n".join(
        f"[{item['id']}] {item['title']} | {item['path']} | {item['heading']} | "
        f"status={item['status']} | revision={item['content_hash'][:12]}\n{item['excerpt']}"
        for item in retrieval["evidence"]
    ) or "(no matching evidence found)"
    history = "\n".join(
        f"- {item['authored_at']} {item['commit'][:12]} {item['subject']} ({', '.join(item['paths'])})"
        for item in retrieval["history"]
    ) or "(not requested or no matching git history)"
    return f"""{captain_kernel.strip()}

---

{current_bearing.strip()}

---

# Captain's Concept Room

Room: {room['title']} ({room['id']})
Retrieval mode: {retrieval['mode']}

Answer the Admiral from the supplied evidence. Cite consequential source claims inline as [S1], [S2], etc. Separate observation, inference, disagreement, and uncertainty. Never invent a citation. Git events prove file chronology, not semantic change by themselves. Begin with a concise 1-3 sentence spoken brief under the exact heading `SPOKEN BRIEF`, then provide useful visible depth under `DEEPER CHART`.

## Room conversation

{transcript}

## Grounded evidence

{sources}

## Relevant git events

{history}

## Current Admiral question

{query.strip()}
"""


def spoken_brief(answer: str) -> str:
    match = re.search(r"SPOKEN BRIEF\s*[:\n]+(.+?)(?:\n\s*(?:#+\s*)?DEEPER CHART|\Z)", answer, re.I | re.S)
    if match:
        return match.group(1).strip()[:1200]
    return answer.strip()[:600]


def normalized_concept_title(query: str) -> str:
    title = re.sub(r"\s+", " ", query.strip()).rstrip("?.!")
    title = re.sub(r"^(please\s+)?(explain|describe|trace|compare|find|brief me (?:on|about))\s+", "", title, flags=re.I)
    return (title or "Untitled concept")[:140]

