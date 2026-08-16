#!/usr/bin/env python3
"""Monad CardMaker v0.1 - Web Server & API.

Runs locally in one command:
    python3 tools/cardmaker/server.py --port 4780

Serves:
- Single-page application UI at /
- Card generation API at POST /api/generate
- Health check at GET /api/status
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# Add cardmaker directory to import path
CARDMAKER_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CARDMAKER_DIR))

from generator import CardGeneratorEngine, CardInput

# Unified static directory: single source of truth at web/toys/cardmaker
WEB_ROOT = CARDMAKER_DIR.parent.parent / "web"
STATIC_DIR = WEB_ROOT / "toys" / "cardmaker"
ENGINE = CardGeneratorEngine()


class CardMakerRequestHandler(BaseHTTPRequestHandler):
    """HTTP Request Handler for CardMaker."""

    def log_message(self, format: str, *args: tuple) -> None:
        # Keep stdout clean during operational use
        pass

    def _send_json(self, status: int, data: dict) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, file_path: Path, content_type: str) -> None:
        if not file_path.exists():
            self.send_error(404, f"File Not Found: {file_path.name}")
            return

        with open(file_path, "rb") as f:
            content = f.read()

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_OPTIONS(self) -> None:
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        path = self.path.split("?")[0].rstrip("/")

        if path in ("/status", "/api/status"):
            self._send_json(200, {
                "status": "ok",
                "service": "monad-cardmaker",
                "version": "0.1",
                "has_llm_key": bool(ENGINE.llm_generator.api_key)
            })
            return

        # Serve static files directly from canonical location web/toys/cardmaker
        if path == "" or path == "/index.html":
            self._send_file(STATIC_DIR / "index.html", "text/html; charset=utf-8")
        elif path == "/style.css":
            self._send_file(STATIC_DIR / "style.css", "text/css; charset=utf-8")
        elif path == "/app.js":
            self._send_file(STATIC_DIR / "app.js", "application/javascript; charset=utf-8")
        else:
            self.send_error(404, "Not Found")

    def do_POST(self) -> None:
        path = self.path.split("?")[0].rstrip("/")

        if path.endswith("/generate") or path in ("/generate", "/api/generate", "/cardmaker-api/generate"):
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)

            try:
                data = json.loads(body.decode("utf-8")) if body else {}
                card_input = CardInput(
                    recipient=str(data.get("recipient", "Ken")),
                    occasion=str(data.get("occasion", "Birthday")),
                    relationship=str(data.get("relationship", "Family")),
                    details=str(data.get("details", "")),
                    tone=str(data.get("tone", "Warm"))
                )

                card = ENGINE.create_card(card_input)
                self._send_json(200, card.to_dict())
            except Exception as e:
                self._send_json(400, {"error": str(e)})
            return

        self.send_error(404, f"Not Found: {self.path}")


def run_server(host: str = "127.0.0.1", port: int = 4785) -> None:
    ThreadingHTTPServer.allow_reuse_address = True
    server = ThreadingHTTPServer((host, port), CardMakerRequestHandler)
    print(f"🎴 MONAD CARDMAKER v0.1 running at http://{host}:{port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down CardMaker server.")
        server.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Monad CardMaker v0.1 Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host address to bind")
    parser.add_argument("--port", type=int, default=4785, help="Port to bind")
    args = parser.parse_args()

    run_server(host=args.host, port=args.port)
