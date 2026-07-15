#!/usr/bin/env python3
"""Read-only HTTP status view over Living Captain's persisted state.

Serves only what is already on disk in data/living-captain/ -- state.json
and the tail of actions.jsonl. This process never assembles a
LivingCaptain instance, never calls observe(), never spends budget: it is
a window onto the record left by whatever operator-invoked run wrote it
last, not a second way to drive the Captain.
"""

from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))

import action_log
import captain_state

ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = ROOT / "data" / "living-captain"


def build_status(action_tail_limit: int = 20) -> dict:
    state = captain_state.load_state(STATE_DIR / "state.json")
    actions = action_log.read_actions(STATE_DIR / "actions.jsonl")
    return {
        "identity": {
            "captain_id": state["captain_id"],
            "created_at": state["created_at"],
            "restart_count": state["restart_count"],
            "last_assembled_at": state["last_assembled_at"],
        },
        "last_observed": {
            "fleetcore_tick": state.get("last_seen_fleetcore_tick"),
            "fleetcore_event_sequence": state.get("last_seen_fleetcore_event_sequence"),
            "world_intake_pending_count": state.get("last_seen_world_intake_pending_count"),
        },
        "spend": {
            "observe_count": state.get("observe_count", 0),
            "observe_limit": state.get("observe_limit"),
        },
        "custody_manifest": state.get("custody_manifest"),
        "action_log_length": len(actions),
        "recent_actions": actions[-action_tail_limit:],
    }


def serve(host: str = "127.0.0.1", port: int = 4774) -> None:
    class Handler(BaseHTTPRequestHandler):
        def send_json(self, payload, status: int = 200) -> None:
            body = json.dumps(payload, indent=2).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/status":
                limit = int(parse_qs(parsed.query).get("limit", ["20"])[0])
                self.send_json(build_status(action_tail_limit=limit))
                return
            self.send_json({"error": "not found"}, 404)

        def do_OPTIONS(self) -> None:
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET,OPTIONS")
            self.end_headers()

        def log_message(self, format, *args) -> None:  # noqa: A002
            pass

    server = HTTPServer((host, port), Handler)
    print(f"Living Captain status API listening on http://{host}:{port}")
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    serve()
