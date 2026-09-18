#!/usr/bin/env python3
"""Cognitive Watch: a curated, disposable Qdrant index for finding source evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import textwrap
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORPUS = Path(__file__).with_name("corpus.json")
COLLECTION = "monad_retrieval_watch_v1"
API = "http://127.0.0.1:6333"
MODEL = "BAAI/bge-base-en-v1.5"
NAMESPACE = uuid.UUID("cf5c6079-7e22-4da7-895c-4d61db6d54f5")


def request(method: str, path: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(API + path, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.loads(response.read())
    except urllib.error.URLError as error:
        raise RuntimeError(f"Qdrant unavailable at {API}: {error}") from error


def embedder():
    try:
        from fastembed import TextEmbedding
    except ImportError as error:
        raise RuntimeError("Install fastembed in /home/cgl/.cache/monad-cognitive-watch first.") from error
    return TextEmbedding(model_name=MODEL)


def heading_chunks(text: str, limit: int = 1200):
    heading = "Document"
    current = []
    ordinal = 0
    for paragraph in text.splitlines():
        if paragraph.startswith("#"):
            if current:
                yield heading, ordinal, "\n".join(current).strip(); ordinal += 1; current = []
            heading = paragraph.lstrip("#").strip() or "Document"
            continue
        if current and len("\n".join(current)) + len(paragraph) + 1 > limit:
            yield heading, ordinal, "\n".join(current).strip(); ordinal += 1; current = []
        current.append(paragraph)
    if current and "\n".join(current).strip():
        yield heading, ordinal, "\n".join(current).strip()


def git_commit(path: str) -> str:
    result = subprocess.run(["git", "log", "-1", "--format=%H", "--", path], cwd=ROOT, capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else "untracked"


def records():
    for entry in json.loads(CORPUS.read_text()):
        path = entry["path"]
        source = ROOT / path
        text = source.read_text(encoding="utf-8")
        digest = hashlib.sha256(text.encode()).hexdigest()
        commit = git_commit(path)
        for heading, ordinal, chunk in heading_chunks(text):
            if not chunk:
                continue
            key = f"{path}:{digest}:{ordinal}"
            yield str(uuid.uuid5(NAMESPACE, key)), chunk, {
                "projection": "cognitive-watch-v1", "source_path": path, "source_class": entry["class"],
                "source_commit": commit, "source_sha256": digest, "heading": heading,
                "ordinal": ordinal, "title": source.stem, "excerpt": chunk[:600],
                "indexed_at": datetime.now(timezone.utc).isoformat(), "authority": "retrieval-only"
            }


def ensure_collection():
    collections = request("GET", "/collections")["result"]["collections"]
    if not any(item["name"] == COLLECTION for item in collections):
        request("PUT", f"/collections/{COLLECTION}", {"vectors": {"size": 768, "distance": "Cosine"}})


def index():
    ensure_collection()
    # This projection owns only its tagged points; no other Qdrant data is touched.
    request("POST", f"/collections/{COLLECTION}/points/delete", {"filter": {"must": [{"key": "projection", "match": {"value": "cognitive-watch-v1"}}]}, "wait": True})
    rows = list(records())
    model = embedder()
    # Granite is a working host, not a model-serving appliance. Small batches
    # keep the first local embedding pass from monopolizing RAM.
    vectors = model.embed([row[1] for row in rows], batch_size=8)
    points = [{"id": row[0], "vector": list(vector), "payload": row[2]} for row, vector in zip(rows, vectors)]
    for start in range(0, len(points), 32):
        request("PUT", f"/collections/{COLLECTION}/points", {"wait": True, "points": points[start:start + 32]})
    print(json.dumps({"collection": COLLECTION, "documents": len(json.loads(CORPUS.read_text())), "chunks": len(points), "model": MODEL}, indent=2))


def find(query: str, limit: int):
    model = embedder()
    vector = list(next(model.embed([query])))
    result = request("POST", f"/collections/{COLLECTION}/points/query", {"query": vector, "limit": limit, "with_payload": True, "with_vector": False})
    for rank, item in enumerate(result["result"]["points"], 1):
        p = item["payload"]
        print(f"[{rank}] {p['source_path']} :: {p['heading']}  score={item['score']:.3f}")
        print(f"    commit={p['source_commit'][:12]} class={p['source_class']} authority={p['authority']}")
        print(textwrap.fill(p["excerpt"].replace("\n", " "), width=108, subsequent_indent="    "))
        print()


def status():
    data = request("GET", f"/collections/{COLLECTION}")
    print(json.dumps(data["result"], indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("index")
    query = sub.add_parser("find"); query.add_argument("query"); query.add_argument("-k", type=int, default=5)
    sub.add_parser("status")
    args = parser.parse_args()
    if args.command == "index": index()
    elif args.command == "find": find(args.query, args.k)
    else: status()


if __name__ == "__main__": main()
