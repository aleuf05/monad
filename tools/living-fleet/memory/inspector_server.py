#!/usr/bin/env python3
"""Read-only JSON API for the live Captain Memory & Identity inspector.

stdlib http.server, bound 127.0.0.1 only -- reached publicly through Caddy's
handle_path /captain-memory-api/* reverse proxy (see docs/deployment.md and
scripts/Caddyfile), the same loopback+reverse-proxy pattern already used for
fleetcore-serve. No write endpoints, no command authority: same risk class
as the existing unauthenticated fleetcore-ws snapshot read, consistent with
this project's standing "security hardening is not the priority" policy.

Single-threaded on purpose: sqlite3 connections aren't safe to share across
threads without extra care, and this is a low-traffic page polling every
~8 seconds, not a service under real load.
"""

from __future__ import annotations

import argparse
import json
import re
import threading
import time
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from memory import store  # noqa: E402
from memory.seed_import import DEFAULT_CAPTAINS, DEFAULT_DB, _read_captains  # noqa: E402
from memory.service import MemoryService  # noqa: E402

HOST = "127.0.0.1"
PORT = 4772


def _captain_summary(service: MemoryService, captain_id: str) -> dict:
    context = service.request_context(captain_id, purpose="respond-to-lieutenant")
    identity_summary = context["identity_summary"]
    relationship = service.request_relationship_context(captain_id, "lieutenant.cgl")

    reflections = sorted(
        store.fetch_by(service.conn, "reflections", captain_id=captain_id),
        key=lambda row: row["created_at"],
        reverse=True,
    )
    beliefs = store.fetch_by(service.conn, "semantic_beliefs", captain_id=captain_id)
    episodes = sorted(
        store.fetch_by(service.conn, "episodic_memories", captain_id=captain_id),
        key=lambda row: row["salience_score"],
        reverse=True,
    )

    latest_reflection = reflections[0] if reflections else None
    top_episode = episodes[0] if episodes else None
    return {
        "captain_id": captain_id,
        "role": identity_summary.get("role"),
        "communication_style": identity_summary.get("communication_style"),
        "traits": identity_summary.get("current_tendencies"),
        "lieutenant_relationship": {"trust": relationship["trust"], "friction": relationship["friction"]},
        "latest_reflection": (
            {
                "summary": latest_reflection["summary"],
                "created_at": latest_reflection["created_at"],
                "triggered_by": latest_reflection["triggered_by"],
            }
            if latest_reflection
            else None
        ),
        "belief_counts": {
            "active": sum(1 for row in beliefs if row["status"] == "active"),
            "superseded": sum(1 for row in beliefs if row["status"] == "superseded"),
        },
        "top_episode": (
            {"what": top_episode["what"], "salience_score": top_episode["salience_score"]} if top_episode else None
        ),
    }


def _fleet_narrative(service: MemoryService) -> list[dict]:
    seen = set()
    result = []
    for captain_id in service.captains:
        for row in store.fetch_by(service.conn, "narrative_memories", captain_id=captain_id):
            key = (row["title"], row["fact_summary"])
            if key in seen:
                continue
            seen.add(key)
            result.append({"title": row["title"], "fact_summary": row["fact_summary"], "mythology": row["mythology"]})
    return result


def _summary_payload(service: MemoryService) -> dict:
    return {
        "captains": [_captain_summary(service, captain_id) for captain_id in service.captains],
        "fleet_narrative": _fleet_narrative(service),
    }


class SummaryCache:
    """Keep the hot read endpoint independent of retrieval rebuild latency.

    SQLite remains authoritative.  A dedicated read connection notices WAL
    data-version changes and atomically publishes a newly computed payload;
    request handlers never wait on a database lock or a TF-IDF corpus rebuild.
    At the 250 ms poll interval, inspector data is still much fresher than its
    human-facing UI needs while API latency stays deterministic.
    """

    def __init__(self, db_path: str, captains: list[dict], initial_payload: dict):
        self.db_path = db_path
        self.captains = captains
        self.payload = initial_payload
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._refresh_loop, name="memory-summary-refresh", daemon=True)

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        self.thread.join(timeout=2)

    def _refresh_loop(self) -> None:
        service = MemoryService(self.db_path, self.captains)
        try:
            data_version = service.conn.execute("PRAGMA data_version").fetchone()[0]
            while not self.stop_event.wait(0.25):
                try:
                    current_version = service.conn.execute("PRAGMA data_version").fetchone()[0]
                    if current_version != data_version:
                        refreshed = _summary_payload(service)
                        self.payload = refreshed
                        data_version = current_version
                except Exception:
                    # The inspector is observational and fail-open: retain the
                    # last good payload if a concurrent write briefly wins.
                    continue
        finally:
            service.close()


def make_handler(service: MemoryService, summary_cache: SummaryCache):
    class Handler(BaseHTTPRequestHandler):
        def _json(self, payload: dict, status: int = 200) -> None:
            body = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802 (stdlib method name)
            if self.path == "/captains/summary":
                self._json(summary_cache.payload)
                return
            match = re.match(r"^/captains/([^/]+)/detail$", self.path)
            if match:
                captain_id = match.group(1)
                if captain_id not in service.captains:
                    self._json({"error": "unknown captain"}, status=404)
                    return
                self._json({"captain_id": captain_id, "records": service.inspect_memory(captain_id, limit=100)})
                return
            self._json({"error": "not found"}, status=404)

        def log_message(self, format: str, *args) -> None:  # noqa: A002
            pass  # keep the systemd journal quiet; response status already carries errors

    return Handler


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve the read-only Captain Memory & Identity API.")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--captains", default=str(DEFAULT_CAPTAINS))
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=PORT)
    args = parser.parse_args()

    captains = _read_captains(Path(args.captains))
    service = MemoryService(args.db, captains)
    summary_cache = SummaryCache(args.db, captains, _summary_payload(service))
    summary_cache.start()
    server = HTTPServer((args.host, args.port), make_handler(service, summary_cache))
    print(f"living-fleet-memory inspector serving on {args.host}:{args.port}")
    try:
        server.serve_forever()
    finally:
        summary_cache.stop()
        service.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
