#!/usr/bin/env python3
"""Small shared contribution API for Centaur Math: All Hands.

State is intentionally server-side and narrow: one SQLite database containing
bounded, attributed candidate/observation records. The browser never becomes
the source of truth.
"""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.environ.get("CENTAUR_MATH_DATA", ROOT / "data" / "centaur-math"))
DB_PATH = DATA_DIR / "centaur.sqlite3"
HOST = os.environ.get("CENTAUR_MATH_HOST", "127.0.0.1")
PORT = int(os.environ.get("CENTAUR_MATH_PORT", "4790"))
MAX_RECORDS = 200
MAX_NOTE = 800
MAX_INT = 1_000_000
ATTRIBUTIONS = {"Cameron", "Mike", "Captain"}
KINDS = {"candidate", "observation"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=5)
    connection.row_factory = sqlite3.Row
    connection.execute(
        """CREATE TABLE IF NOT EXISTS contributions (
            id TEXT PRIMARY KEY,
            attribution TEXT NOT NULL,
            kind TEXT NOT NULL,
            note TEXT NOT NULL,
            start_value INTEGER,
            step INTEGER,
            length INTEGER,
            endpoint INTEGER,
            created_at TEXT NOT NULL
        )"""
    )
    connection.commit()
    return connection


def public_row(row: sqlite3.Row) -> dict:
    return dict(row)


def list_contributions(connection: sqlite3.Connection) -> list[dict]:
    rows = connection.execute(
        "SELECT * FROM contributions ORDER BY created_at DESC LIMIT ?", (MAX_RECORDS,)
    ).fetchall()
    return [public_row(row) for row in rows]


def validate(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("request must be an object")
    attribution = payload.get("attribution")
    kind = payload.get("kind")
    note = str(payload.get("note", "")).strip()
    if attribution not in ATTRIBUTIONS:
        raise ValueError("choose Cameron, Mike, or Captain")
    if kind not in KINDS:
        raise ValueError("choose candidate or observation")
    if not note or len(note) > MAX_NOTE:
        raise ValueError(f"note must contain 1-{MAX_NOTE} characters")

    values: dict[str, int | None] = {
        "start_value": None,
        "step": None,
        "length": None,
        "endpoint": None,
    }
    if kind == "candidate":
        for key in ("start_value", "step", "length", "endpoint"):
            try:
                value = int(payload.get(key))
            except (TypeError, ValueError):
                raise ValueError(f"{key} must be an integer") from None
            values[key] = value
        if not 0 <= values["start_value"] <= MAX_INT:
            raise ValueError("start must be between 0 and 1,000,000")
        if not 1 <= values["step"] <= MAX_INT:
            raise ValueError("step must be positive and at most 1,000,000")
        if not 1 <= values["length"] <= 35:
            raise ValueError("length must be between 1 and 35")
        expected_endpoint = values["start_value"] + (values["length"] - 1) * values["step"]
        if values["endpoint"] != expected_endpoint:
            raise ValueError("endpoint does not match start, step, and length")
        if expected_endpoint > MAX_INT:
            raise ValueError("candidate endpoint exceeds the supported bound")
    return {"attribution": attribution, "kind": kind, "note": note, **values}


class Handler(BaseHTTPRequestHandler):
    server_version = "CentaurMath/1.0"

    def send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_json(204, {})

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path in {"/health", "/api/health"}:
            self.send_json(200, {"ok": True, "service": "centaur-math", "shared": True})
            return
        if path in {"/api/contributions", "/contributions"}:
            with connect() as connection:
                self.send_json(200, {"ok": True, "contributions": list_contributions(connection)})
            return
        self.send_json(404, {"ok": False, "error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path not in {"/api/contributions", "/contributions"}:
            self.send_json(404, {"ok": False, "error": "not found"})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size > 5000:
                raise ValueError("request is too large")
            payload = json.loads(self.rfile.read(size))
            record = validate(payload)
            record = {"id": uuid.uuid4().hex, **record, "created_at": now()}
            with connect() as connection:
                connection.execute(
                    """INSERT INTO contributions
                    (id, attribution, kind, note, start_value, step, length, endpoint, created_at)
                    VALUES (:id, :attribution, :kind, :note, :start_value, :step, :length, :endpoint, :created_at)""",
                    record,
                )
                connection.commit()
            self.send_json(201, {"ok": True, "contribution": record})
        except (ValueError, json.JSONDecodeError) as error:
            self.send_json(400, {"ok": False, "error": str(error)})
        except sqlite3.Error:
            self.send_json(503, {"ok": False, "error": "shared contribution store unavailable"})

    def log_message(self, format: str, *args: object) -> None:
        print(f"[centaur-math] {self.address_string()} {format % args}", flush=True)


if __name__ == "__main__":
    with connect():
        pass
    print(f"Centaur Math API listening on http://{HOST}:{PORT}", flush=True)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
